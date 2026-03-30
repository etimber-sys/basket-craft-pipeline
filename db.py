import os
import pymysql
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def _require_env(key):
    """Raise EnvironmentError if key is not set in environment."""
    value = os.environ.get(key)
    if value is None:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            "Is your .env file configured?"
        )
    return value


def get_mysql_conn():
    """Return a new pymysql connection. Rows are returned as dicts (DictCursor). Caller must close."""
    return pymysql.connect(
        host=_require_env("MYSQL_HOST"),
        port=int(_require_env("MYSQL_PORT")),
        user=_require_env("MYSQL_USER"),
        password=_require_env("MYSQL_PASSWORD"),
        database=_require_env("MYSQL_DATABASE"),
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_pg_conn():
    """Return a new psycopg2 connection. Caller must close."""
    return psycopg2.connect(
        host=os.environ.get("PG_HOST", "localhost"),
        port=int(os.environ.get("PG_PORT", "5432")),
        user=_require_env("PG_USER"),
        password=_require_env("PG_PASSWORD"),
        dbname=_require_env("PG_DATABASE"),
    )
