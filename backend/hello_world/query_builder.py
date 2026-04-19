def build_athena_query(metric, depth=None, start_date=None, end_date=None):
    """
    Constructs a SQL query for Athena to fetch CalCOFI data.
    """
    database = "calcofi_db"
    table = "bottle_data"

    metric_column = metric
    if metric == "temperature":
        metric_column = "t_degc"
    elif metric == "salinity":
        metric_column = "sal_psu"

    query = f"SELECT {metric_column}, depth, obs_date FROM {database}.{table} WHERE 1=1"

    if depth is not None:
        query += f" AND depth = {depth}"

    if start_date:
        query += f" AND obs_date >= '{start_date}'"

    if end_date:
        query += f" AND obs_date <= '{end_date}'"

    query += " ORDER BY obs_date ASC LIMIT 1000"

    return query
