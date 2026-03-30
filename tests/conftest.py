import os
import pytest
import psycopg2
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="session")
def pg_conn():
    conn = psycopg2.connect(
        host=os.environ.get("PG_HOST", "localhost"),
        port=int(os.environ.get("PG_PORT", "5432")),
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
        dbname=os.environ["PG_DATABASE"],
    )
    yield conn
    conn.close()
