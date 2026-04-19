import os


def build_athena_query(metric=None, depth=None, start_date=None, end_date=None):
    """
    First 10 rows from bottle_table in Glue database ATHENA_DATABASE (default `default`).
    metric/depth/start_date/end_date are ignored for this preview query (kept for API compatibility).
    """
    database = os.environ.get("ATHENA_DATABASE", "default")
    return f"SELECT * FROM {database}.bottle_table LIMIT 10"
