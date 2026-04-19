import json
import os
import time
from typing import Any, Dict, List

import boto3

from query_builder import build_athena_query

athena = boto3.client("athena")

_CORS_HEADERS: Dict[str, str] = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}


def _http_method(event: Dict[str, Any]) -> str:
    m = event.get("httpMethod")
    if isinstance(m, str) and m:
        return m.upper()
    rc = event.get("requestContext") or {}
    inner = (rc.get("http") or {}).get("method")
    if isinstance(inner, str) and inner:
        return inner.upper()
    return ""


def _response(status: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": dict(_CORS_HEADERS),
        "body": json.dumps(payload),
    }


def _options_response() -> Dict[str, Any]:
    h = {k: v for k, v in _CORS_HEADERS.items() if k != "Content-Type"}
    return {"statusCode": 200, "headers": h, "body": ""}


def _coerce_cell(value: str | None) -> Any:
    if value is None or value == "":
        return None
    try:
        if "." in value or "e" in value.lower():
            return float(value)
        return int(value)
    except ValueError:
        return value


def _rows_to_objects(athena_client, execution_id: str) -> List[Dict[str, Any]]:
    column_names: List[str] = []
    out: List[Dict[str, Any]] = []
    next_token = None
    first_page = True

    while True:
        kwargs: Dict[str, Any] = {"QueryExecutionId": execution_id}
        if next_token:
            kwargs["NextToken"] = next_token

        page = athena_client.get_query_results(**kwargs)
        meta = page["ResultSet"]["ResultSetMetadata"]["ColumnInfo"]
        if not column_names:
            column_names = [c.get("Label") or c["Name"] for c in meta]

        rows = page["ResultSet"]["Rows"]
        if first_page and rows:
            rows = rows[1:]
            first_page = False

        for row in rows:
            cells = [d.get("VarCharValue") for d in row["Data"]]
            item = {
                column_names[i]: _coerce_cell(cells[i]) if i < len(cells) else None
                for i in range(len(column_names))
            }
            out.append(item)

        next_token = page.get("NextToken")
        if not next_token:
            break

    return out


def _normalize_athena_output_location(raw: str) -> str:
    """Match scripts/athena_minimal_query.py: require s3:// and ensure trailing slash."""
    loc = raw.strip()
    if not loc:
        raise ValueError(
            "ATHENA_OUTPUT_LOCATION is not set (e.g. s3://your-calcofi-bucket/athena-results/). "
            "Pass it as a stack parameter when deploying."
        )
    if not loc.startswith("s3://"):
        raise ValueError("ATHENA_OUTPUT_LOCATION must be an s3:// URI.")
    return loc.rstrip("/") + "/"


def _run_athena(sql: str) -> List[Dict[str, Any]]:
    database = os.environ.get("ATHENA_DATABASE", "default")
    workgroup = os.environ.get("ATHENA_WORKGROUP", "primary")
    output = _normalize_athena_output_location(os.environ.get("ATHENA_OUTPUT_LOCATION", ""))

    start = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={"OutputLocation": output},
        WorkGroup=workgroup,
    )
    qid = start["QueryExecutionId"]

    deadline = time.time() + float(os.environ.get("ATHENA_POLL_TIMEOUT_SEC", "55"))
    poll = float(os.environ.get("ATHENA_POLL_INTERVAL_SEC", "0.25"))

    while time.time() < deadline:
        status = athena.get_query_execution(QueryExecutionId=qid)
        state = status["QueryExecution"]["Status"]["State"]
        if state == "SUCCEEDED":
            return _rows_to_objects(athena, qid)
        if state in ("FAILED", "CANCELLED"):
            reason = status["QueryExecution"]["Status"].get("StateChangeReason", state)
            raise RuntimeError(reason or state)
        time.sleep(poll)

    raise TimeoutError("Athena query did not finish before Lambda timeout")


def lambda_handler(event, context):
    if _http_method(event) == "OPTIONS":
        return _options_response()

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"success": False, "error": "Invalid JSON body"})

    metric = body.get("metric", "temperature")
    depth = body["depth"] if "depth" in body else None
    start_date = body.get("startDate")
    end_date = body.get("endDate")
    columns = body.get("columns")
    filters = body.get("filters")
    limit = body.get("limit")
    order_by = body.get("orderBy")

    try:
        sql = build_athena_query(
            metric,
            depth,
            start_date,
            end_date,
            columns=columns,
            filters=filters,
            limit=limit,
            order_by=order_by,
        )
    except ValueError as e:
        return _response(400, {"success": False, "error": str(e)})

    try:
        rows = _run_athena(sql)
    except ValueError as e:
        return _response(500, {"success": False, "error": str(e), "query": sql})
    except TimeoutError as e:
        return _response(504, {"success": False, "error": str(e), "query": sql})
    except Exception as e:
        return _response(
            500,
            {"success": False, "error": str(e), "query": sql},
        )

    return _response(
        200,
        {
            "success": True,
            "data": rows,
            "query": sql,
        },
    )
