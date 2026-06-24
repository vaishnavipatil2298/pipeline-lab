"""
Shared pytest fixtures for pipeline-lab.

Goal: every test runs against its own fresh SQLite database so tests stay
isolated and don't pollute each other. We do this by pointing DB_PATH at a
per-test temp file, creating the schema, and seeding the same starting todos
the app shipped with.
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


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Give each test an isolated, freshly-seeded database.

    `tmp_path` is unique per test, so pointing DB_PATH there guarantees no
    state leaks between tests. We then create the schema and seed the default
    todos. `monkeypatch` restores the original DB_PATH after the test.
    """
    db_file = tmp_path / "todos.db"
    monkeypatch.setenv("DB_PATH", str(db_file))

    database.init_db()
    for title, done in _SEED_TODOS:
        database.create_todo(title, done)

    yield
