import pymssql
import pandas as pd
from config import db_server, db_user, db_password, db_name
def execute_query(query: str):
    """Execute a SQL query and return the result as a DataFrame."""
    conn = pymssql.connect(server=db_server, user=db_user, password=db_password, database=db_name)
    result = pd.read_sql_query(query, conn)
    conn.close()
    return result
