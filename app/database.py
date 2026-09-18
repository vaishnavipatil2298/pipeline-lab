"""
Database access layer for pipeline-lab.

ALL SQL lives here. The rest of the app (main.py) talks to todos only through
the functions in this module, so we could swap storage engines without touching
the API layer.

Storage backend is chosen at call time from the environment:

* ``DATABASE_URL`` set to a ``postgres://``/``postgresql://`` URL -> Postgres
  (this is what the Render deployment and the local docker-compose stack use).
* otherwise -> a local SQLite file at ``DB_PATH`` (handy for quick local runs
  and the default in the pytest suite).

Both backends expose the exact same five functions, so callers never care which
one is active.
"""
import os
from contextlib import contextmanager

# Placeholder used by SQLite. We swap it for "%s" on Postgres via _adapt().
_PLACEHOLDER = "?"


def _database_url() -> str | None:
    """Return the configured Postgres URL, if any."""
    return os.environ.get("DATABASE_URL") or None


def _db_path() -> str:
    """Resolve the SQLite file path at call time.

    Read the env var on every call (not at import) so tests can repoint
    DB_PATH at a temp file and have it take effect even after re-importing
    this module.
    """
    return os.environ.get("DB_PATH", "todos.db")


def _is_postgres() -> bool:
    """True when a Postgres URL is configured, else False (SQLite)."""
    url = _database_url()
    return bool(url) and url.startswith(("postgres://", "postgresql://"))


def _adapt(query: str) -> str:
    """Translate `?` placeholders to the active backend's syntax.

    Queries are written once with `?` and rewritten to `%s` for Postgres.
    Parameter values are always bound separately, never interpolated.
    """
    return query.replace(_PLACEHOLDER, "%s") if _is_postgres() else query


@contextmanager
def _connection():
    """Open a connection, committing on success and always closing it.

    Used as ``with _connection() as conn:``. The inner ``with conn`` is what
    commits (or rolls back on exception) for both sqlite3 and psycopg3.
    """
    if _is_postgres():
        import psycopg
        from psycopg.rows import dict_row

        conn = psycopg.connect(_database_url())
        conn.row_factory = dict_row
    else:
        import sqlite3

        conn = sqlite3.connect(_db_path())
        conn.row_factory = sqlite3.Row

    try:
        with conn:
            yield conn
    finally:
        conn.close()


def _row_to_dict(row) -> dict:
    """Convert a DB row into the dict shape the API returns.

    Postgres stores `done` as a real BOOLEAN; SQLite stores 0/1. Normalising
    through ``bool()`` gives callers a real Python bool either way.
    """
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


def init_db() -> None:
    """Create the todos table if it does not already exist.

    Idempotent: safe to call on every startup and after module reload.
    """
    if _is_postgres():
        ddl = """
            CREATE TABLE IF NOT EXISTS todos (
                id    SERIAL PRIMARY KEY,
                title TEXT    NOT NULL,
                done  BOOLEAN NOT NULL DEFAULT FALSE
            )
        """
    else:
        ddl = """
            CREATE TABLE IF NOT EXISTS todos (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT    NOT NULL,
                done  INTEGER NOT NULL DEFAULT 0
            )
        """
    with _connection() as conn:
        conn.execute(ddl)


def get_all_todos() -> list[dict]:
    """Return every todo, ordered by id."""
    with _connection() as conn:
        rows = conn.execute(
            _adapt("SELECT id, title, done FROM todos ORDER BY id")
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_todo(todo_id: int) -> dict | None:
    """Return a single todo by id, or None if it doesn't exist."""
    with _connection() as conn:
        row = conn.execute(
            _adapt("SELECT id, title, done FROM todos WHERE id = ?"), (todo_id,)
        ).fetchone()
    return _row_to_dict(row) if row is not None else None


def create_todo(title: str, done: bool) -> dict:
    """Insert a new todo and return it, including the auto-assigned id."""
    with _connection() as conn:
        if _is_postgres():
            # RETURNING is the reliable way to get the generated key on Postgres.
            row = conn.execute(
                _adapt("INSERT INTO todos (title, done) VALUES (?, ?) RETURNING id"),
                (title, done),
            ).fetchone()
            new_id = row["id"]
        else:
            cursor = conn.execute(
                _adapt("INSERT INTO todos (title, done) VALUES (?, ?)"),
                (title, int(done)),
            )
            new_id = cursor.lastrowid
    return {"id": new_id, "title": title, "done": bool(done)}


def update_todo(todo_id: int, title: str, done: bool) -> dict | None:
    """Update an existing todo's title and done flag.

    Returns the updated todo, or None if no row with that id exists.
    """
    with _connection() as conn:
        cursor = conn.execute(
            _adapt("UPDATE todos SET title = ?, done = ? WHERE id = ?"),
            (title, done if _is_postgres() else int(done), todo_id),
        )
        if cursor.rowcount == 0:
            return None
    return {"id": todo_id, "title": title, "done": bool(done)}


def delete_todo(todo_id: int) -> bool:
    """Delete a todo by id. Return True if a row was deleted, else False."""
    with _connection() as conn:
        cursor = conn.execute(
            _adapt("DELETE FROM todos WHERE id = ?"), (todo_id,)
        )
        return cursor.rowcount > 0
