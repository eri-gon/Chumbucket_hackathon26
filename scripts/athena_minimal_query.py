#!/usr/bin/env python3
"""
Minimal Athena query → print rows (local script; uses default AWS credential chain).

  pip install boto3
  set ATHENA_OUTPUT_LOCATION=s3://your-calcofi-bucket/athena-results/
  python scripts/athena_minimal_query.py

Optional env: ATHENA_DATABASE (default default), ATHENA_TABLE (default bottle_table).
"""
import os
import time

import boto3

athena = boto3.client("athena")

DATABASE = os.environ.get("ATHENA_DATABASE", "default")
TABLE = os.environ.get("ATHENA_TABLE", "bottle_table")
OUTPUT_S3 = os.environ.get(
    "ATHENA_OUTPUT_LOCATION",
    "s3://your-calcofi-bucket/athena-results/",
).rstrip("/") + "/"

if not OUTPUT_S3.startswith("s3://"):
    raise SystemExit("ATHENA_OUTPUT_LOCATION must be an s3:// URI.")

query = f"SELECT * FROM {TABLE} LIMIT 10"

# Start query
response = athena.start_query_execution(
    QueryString=query,
    QueryExecutionContext={"Database": DATABASE},
    ResultConfiguration={"OutputLocation": OUTPUT_S3},
)

query_execution_id = response["QueryExecutionId"]

# Wait for query to finish
while True:
    result = athena.get_query_execution(QueryExecutionId=query_execution_id)
    state = result["QueryExecution"]["Status"]["State"]

    if state in ["SUCCEEDED", "FAILED", "CANCELLED"]:
        break
    time.sleep(1)

if state != "SUCCEEDED":
    reason = result["QueryExecution"]["Status"].get("StateChangeReason", state)
    raise RuntimeError(f"Athena query failed: {state} — {reason}")

# Fetch results
results = athena.get_query_results(QueryExecutionId=query_execution_id)

# Print rows
for row in results["ResultSet"]["Rows"]:
    print([col.get("VarCharValue", "") for col in row["Data"]])
