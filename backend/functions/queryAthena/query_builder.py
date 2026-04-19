def build_athena_query(metric, depth=None, start_date=None, end_date=None):
    """
    Constructs a SQL query for Athena to fetch CalCOFI data.
    """
    # Assuming standard table name structure
    database = "calcofi_db"
    table = "bottle_data"
    
    # Map friendly metric names to column names if necessary
    metric_column = metric # e.g., 'temperature' -> 't_degc'
    if metric == 'temperature':
        metric_column = 't_degc'
    elif metric == 'salinity':
        metric_column = 'sal_psu'

    query = f"SELECT {metric_column}, depth, obs_date FROM {database}.{table} WHERE 1=1"

    if depth:
        query += f" AND depth = {depth}"

    if start_date:
        query += f" AND obs_date >= '{start_date}'"

    if end_date:
        query += f" AND obs_date <= '{end_date}'"

    query += " ORDER BY obs_date ASC LIMIT 1000"
    
    return query
