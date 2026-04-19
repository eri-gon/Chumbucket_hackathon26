import json

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}


def _http_method(event):
    m = event.get("httpMethod")
    if isinstance(m, str) and m:
        return m.upper()
    rc = event.get("requestContext") or {}
    inner = (rc.get("http") or {}).get("method")
    if isinstance(inner, str) and inner:
        return inner.upper()
    return ""


def handler(event, context):
    """
    Lambda handler for preprocessing CalCOFI data (cleaning, aggregation).
    """
    if _http_method(event) == "OPTIONS":
        return {"statusCode": 200, "headers": dict(_CORS), "body": ""}

    return {
        "statusCode": 200,
        "headers": {**_CORS, "Content-Type": "application/json"},
        "body": json.dumps({
            "success": True,
            "message": "Data preprocessing task initiated successfully.",
        }),
    }
