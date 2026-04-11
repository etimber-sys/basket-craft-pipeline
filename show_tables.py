import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
import psycopg2

conn = psycopg2.connect(
    host=os.getenv('PG_HOST'),
    port=int(os.getenv('PG_PORT', 5432)),
    user=os.getenv('PG_USER'),
    password=os.getenv('PG_PASSWORD'),
    dbname=os.getenv('PG_DATABASE'),
)
cur = conn.cursor()
cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name
""")
tables = [row[0] for row in cur.fetchall()]

print(f"{'Table':<25} {'Row Count':>10}")
print('-' * 37)
for t in tables:
    cur.execute(f'SELECT COUNT(*) FROM {t}')
    count = cur.fetchone()[0]
    print(f'{t:<25} {count:>10,}')

conn.close()
