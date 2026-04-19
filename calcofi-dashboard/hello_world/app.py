import json


def lambda_handler(event, context):
    """Sample pure Lambda function"""

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({"message": "hello"}),
    }
