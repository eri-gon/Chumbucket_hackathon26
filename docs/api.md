# API

The HTTP API is created by AWS SAM (`infrastructure/template.yaml`). After deploy, CloudFormation output **`ApiEndpoint`** is the base URL. It looks like:

`https://{rest-api-id}.execute-api.{region}.amazonaws.com/Prod`

The frontend sets `VITE_API_URL` to that base (no trailing slash required). The client calls **`POST {base}/query`**.

All paths below use JSON bodies and return JSON unless noted.

---

## `POST /query`

Implemented by `backend/hello_world/app.py` (`lambda_handler`). It runs **`SELECT * FROM …bottle_table LIMIT 10`** against the Glue database in **`ATHENA_DATABASE`** (SAM **`AthenaDatabase`**, default **`default`**) using **boto3**, and returns those rows as JSON. Request fields `metric` / `depth` / dates are accepted but not used for this preview.

Stack parameter **`AthenaOutputLocation`** defaults to **`s3://your-calcofi-bucket/athena-results/`** (see `docs/setup.md`); override at deploy if needed.

### Request body

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `metric` | string | No | Ignored for the current **`LIMIT 10`** preview (defaults to `temperature` in clients). |
| `depth` | number | No | Ignored for the preview. |
| `startDate` | string | No | Ignored for the preview. |
| `endDate` | string | No | Ignored for the preview. |

Example:

```json
{
  "metric": "temperature",
  "depth": 10,
  "startDate": "2019-01-01",
  "endDate": "2019-12-31"
}
```

### Success response (`200`)

```json
{
  "success": true,
  "data": [
    { "cst_cnt": 1, "btl_cnt": 1, "depthm": 10.0, "t_degc": 12.3 }
  ],
  "query": "SELECT * FROM default.bottle_table LIMIT 10"
}
```

`data` columns match Athena output (names depend on the `SELECT`). Errors return `4xx`/`5xx` with `success: false` and an `error` string; missing Athena output location returns `500` with a configuration hint.

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

- **SAM local:** from the repo root, use `infrastructure/events/api_events.json` with `sam local invoke` for the query function (see `docs/setup.md`).
- **curl:**

```bash
curl -sS -X POST "${VITE_API_URL}/query" \
  -H "Content-Type: application/json" \
  -d '{"metric":"temperature","depth":10}'
```

Replace `VITE_API_URL` with your deployed `ApiEndpoint` value.
