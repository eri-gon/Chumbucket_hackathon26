# API

The HTTP API is created by AWS SAM (`infrastructure/template.yaml`). After deploy, CloudFormation output **`ApiEndpoint`** is the base URL. It looks like:

`https://{rest-api-id}.execute-api.{region}.amazonaws.com/Prod`

The frontend sets `VITE_API_URL` to that base (no trailing slash required). The client calls **`POST {base}/query`**.

All paths below use JSON bodies and return JSON unless noted.

---

## `POST /query`

Implemented by `backend/hello_world/app.py` (`lambda_handler`). It builds SQL for `calcofi_db.bottle_data`, runs it in **Amazon Athena** with **boto3**, and returns result rows as JSON.

Deploy must set stack parameter **`AthenaOutputLocation`** (see `docs/setup.md`) so Athena can write results to S3.

### Request body

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `metric` | string | No | Defaults to `temperature` (`t_degc`); `salinity` maps to `sal_psu`. |
| `depth` | number | No | Defaults to `10`; adds `AND depth = …` to the SQL. |
| `startDate` | string | No | Lower bound on `obs_date` (`YYYY-MM-DD`). |
| `endDate` | string | No | Upper bound on `obs_date`. |

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
    { "t_degc": 15.5, "depth": 10, "obs_date": "2019-04-15" }
  ],
  "query": "SELECT t_degc, depth, obs_date FROM calcofi_db.bottle_data WHERE 1=1 ..."
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
