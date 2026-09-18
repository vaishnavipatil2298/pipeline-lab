"""
Shared pytest fixtures for pipeline-lab.

Every test runs against its own isolated, freshly-seeded database:

* By default that's a per-test SQLite file (fast, no external services).
* Set ``TEST_DATABASE_URL`` to a Postgres URL to run the exact same suite
  against Postgres. The table is truncated and its identity reset before each
  test, so auto-assigned ids line up with the SQLite run.
"""
import os

import pytest

from app import database

# The starting todos several tests rely on (e.g. GET/PUT /todos/1, count >= 1).
_SEED_TODOS = [
    ("Learn Docker", False),
    ("Ship CI/CD pipeline", False),
    ("Connect Claude Code to workflow", False),
]


def _reset_postgres_table() -> None:
    """Empty the todos table and restart ids at 1 (Postgres-only)."""
    with database._connection() as conn:
        conn.execute("TRUNCATE todos RESTART IDENTITY")


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Give each test an isolated, freshly-seeded database.

    When ``TEST_DATABASE_URL`` is set we point the app at Postgres and reset the
    table before every test. Otherwise we use a unique per-test SQLite file so
    no state leaks between tests. ``monkeypatch`` restores the environment after.
    """
    test_url = os.environ.get("TEST_DATABASE_URL")
    if test_url:
        monkeypatch.setenv("DATABASE_URL", test_url)
        database.init_db()
        _reset_postgres_table()
    else:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("DB_PATH", str(tmp_path / "todos.db"))
        database.init_db()

    for title, done in _SEED_TODOS:
        database.create_todo(title, done)

    yield
