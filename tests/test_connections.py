def test_pg_connection_is_reachable(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute("SELECT 1")
        result = cur.fetchone()
    assert result == (1,)
