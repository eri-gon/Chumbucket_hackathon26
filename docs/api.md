# API

The HTTP API is created by AWS SAM (`calcofi-dashboard/template.yaml`). After deploy, CloudFormation output **`ApiEndpoint`** is the base URL. It looks like:

`https://{rest-api-id}.execute-api.{region}.amazonaws.com/Prod`

The frontend sets `VITE_API_URL` to that base (no trailing slash required). The client calls **`POST {base}/query`**.

All paths below use JSON bodies and return JSON unless noted.

---

## `POST /query`

Implemented by `backend/hello_world/app.py` (`lambda_handler`). The Lambda builds **SQL on the server** from structured JSON (clients never send raw SQL). Athena runs against **`ATHENA_TABLE`** (default **`bottle_table`**) with **`QueryExecutionContext`** database **`ATHENA_DATABASE`** (SAM **`AthenaDatabase`**, default **`default`**).

### Identifier safety

- **Column names** must match `^[a-zA-Z_][a-zA-Z0-9_]*$` and appear in the server allowlist defined in `backend/hello_world/query_builder.py` (duplicate list in `frontend/src/config/athenaAllowlist.ts` — keep in sync with `data/schemas/calcofi_schema.sql` **`bottle_table`** columns when that is `ATHENA_TABLE`).
- **Operators** are a closed set: `=`, `!=`, `<`, `<=`, `>`, `>=`, `BETWEEN`.
- **Values** are formatted as SQL literals: numbers unquoted; strings single-quoted with `'` escaped; ISO dates **`YYYY-MM-DD`** allowed; other strings must match a short safe character class or the request is rejected with **`400`**.
- **`LIMIT`**: optional integer in the body, default **10**, maximum **500**.

### Request body

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `metric` | string | No | Ignored for SQL generation (kept for client compatibility). |
| `depth` | number | No | If present, adds `depthm = <depth>` to the `WHERE` clause. Omit the field to skip this shortcut. |
| `startDate` | string | No | If allowlisted column **`date`** exists for the configured table, adds date predicates (`BETWEEN`, `>=`, or `<=`). Must be **`YYYY-MM-DD`**. The default **`bottle_table`** in `data/schemas/calcofi_schema.sql` has no `date` column, so these fields are ignored until you extend the schema or allowlist (e.g. for **`cast_table`**). |
| `endDate` | string | No | Same as `startDate`. |
| `columns` | string[] | No | If non-empty, `SELECT` lists only these columns (each must be allowlisted). Omitted or `[]` means `SELECT *`. |
| `filters` | array | No | List of `{ "column", "op", "value" }`. For **`BETWEEN`**, `value` must be a two-element array `[low, high]`. |
| `limit` | integer | No | Row cap (1–500, default 10). |
| `orderBy` | object | No | `{ "column": "<allowlisted>", "direction": "ASC" \| "DESC" }` (`direction` defaults to **`ASC`**). |

### Example (columns + filters + order)

```json
{
  "limit": 50,
  "columns": ["cst_cnt", "btl_cnt", "depthm", "t_degc", "salnty"],
  "filters": [
    { "column": "depthm", "op": "<=", "value": 100 },
    { "column": "t_degc", "op": ">", "value": 0 }
  ],
  "orderBy": { "column": "depthm", "direction": "ASC" }
}
```

Malformed filters, unknown columns, bad operators, or invalid values produce **`400`** with `{ "success": false, "error": "<message>" }` and no Athena call.

### Success response (`200`)

```json
{
  "success": true,
  "data": [
    { "cst_cnt": 1, "btl_cnt": 1, "depthm": 10.0, "t_degc": 12.3 }
  ],
  "query": "SELECT cst_cnt, btl_cnt, depthm, t_degc, salnty FROM bottle_table WHERE depthm <= 100 AND t_degc > 0 ORDER BY depthm ASC LIMIT 50"
}
```

`data` columns match the `SELECT`. Errors return `4xx`/`5xx` with `success: false` and an `error` string; missing Athena output location returns `500` with a configuration hint.

CORS response headers include `Access-Control-Allow-Origin: *` for browser calls.

---

## `POST /preprocess`

Placeholder endpoint for kicking off preprocessing or ETL.

### Request body

No required fields; body may be empty JSON `{}`.

### Success response (`200`)

```json
{
  "success": true,
  "message": "Data preprocessing task initiated successfully."
}
```

---

## Local testing

- **SAM local:** from `calcofi-dashboard/`, use `events/query_event.json` with `sam local invoke QueryFunction` (see `docs/setup.md`).
- **curl:**

```bash
curl -sS -X POST "${VITE_API_URL}/query" \
  -H "Content-Type: application/json" \
  -d '{"limit":25,"columns":["depthm","t_degc"],"filters":[{"column":"depthm","op":"<","value":500}]}'
```

Replace `VITE_API_URL` with your deployed `ApiEndpoint` value.
