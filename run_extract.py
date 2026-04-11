import sys
import os
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

from db import get_mysql_conn, get_pg_conn
from extract import extract_table, TABLES

BATCH_SIZE = 1000

mysql_conn = get_mysql_conn()
pg_conn = get_pg_conn()
print("Connections established.")
try:
    with mysql_conn.cursor() as mysql_cur, pg_conn.cursor() as pg_cur:
        for table, columns in TABLES.items():
            print(f"  Fetching {table} from MySQL...", flush=True)
            count = extract_table(mysql_cur, pg_cur, table, columns)
            print(f"  stg_{table}: {count:,} rows loaded", flush=True)
    pg_conn.commit()
    print("Extract complete.")
except Exception as e:
    pg_conn.rollback()
    print(f"Extract failed: {e}")
    raise
finally:
    mysql_conn.close()
    pg_conn.close()
