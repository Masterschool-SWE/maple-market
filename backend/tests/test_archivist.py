"""Tests for the Archivist's read-only SQL tool (no LLM needed)."""
from app.agent.archivist import execute_sql


def test_guard_blocks_writes():
    assert "Rejected" in execute_sql.invoke({"query": "DELETE FROM shop_order"})
    assert "Rejected" in execute_sql.invoke({"query": "DROP TABLE shop_order"})
    assert "Rejected" in execute_sql.invoke({"query": "UPDATE shop_order SET status = 'cancelled'"})


def test_guard_blocks_multiple_statements():
    assert "Rejected" in execute_sql.invoke({"query": "SELECT 1; DROP TABLE shop_order"})


def test_select_runs_against_seeded_db(client):
    out = execute_sql.invoke({"query": "SELECT COUNT(*) AS n FROM product"})
    assert out.startswith("n"), out


def test_created_at_column_not_falsely_blocked(client):
    out = execute_sql.invoke({"query": "SELECT username, created_at FROM user"})
    assert "Rejected" not in out
