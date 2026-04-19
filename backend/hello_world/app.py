import json
import os
import time
from typing import Any, Dict, List

import boto3

from query_builder import build_athena_query

athena = boto3.client("athena")


def _response(status: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(payload),
    }


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


def _run_athena(sql: str) -> List[Dict[str, Any]]:
    database = os.environ.get("ATHENA_DATABASE", "calcofi_db")
    workgroup = os.environ.get("ATHENA_WORKGROUP", "primary")
    output = os.environ.get("ATHENA_OUTPUT_LOCATION", "").strip()

    if not output:
        raise ValueError(
            "ATHENA_OUTPUT_LOCATION is not set (e.g. s3://your-calcofi-bucket/athena-results/). "
            "Pass it as a stack parameter when deploying."
        )

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
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"success": False, "error": "Invalid JSON body"})

    metric = body.get("metric", "temperature")
    depth = body.get("depth", 10)
    start_date = body.get("startDate")
    end_date = body.get("endDate")

    sql = build_athena_query(metric, depth, start_date, end_date)

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
