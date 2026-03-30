import os
import pytest
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def _require_env(key):
    value = os.environ.get(key)
    if value is None:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            "Is your .env file configured?"
        )
    return value


@pytest.fixture(scope="session")
def pg_conn():
    # Connection logic is intentionally duplicated from db.py to keep conftest importable without pymysql.
    conn = psycopg2.connect(
        host=os.environ.get("PG_HOST", "localhost"),
        port=int(os.environ.get("PG_PORT", "5432")),
        user=_require_env("PG_USER"),
        password=_require_env("PG_PASSWORD"),
        dbname=_require_env("PG_DATABASE"),
    )
    yield conn
    conn.close()
