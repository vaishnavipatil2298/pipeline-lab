"""
Database access layer for pipeline-lab.

ALL SQL lives here. The rest of the app (main.py) talks to todos only through
the functions in this module, so we could swap SQLite for another store without
touching the API layer.

Week 2 goal: replace the in-memory list with real, persistent storage.
"""
import os
import sqlite3


def _db_path() -> str:
    """Resolve the SQLite file path at call time.

    Read the env var on every call (not at import) so tests can repoint
    DB_PATH at a temp file and have it take effect even after re-importing
    this module.
    """
    return os.environ.get("DB_PATH", "todos.db")


def _connect() -> sqlite3.Connection:
    """Open a connection with row access by column name."""
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a DB row into the dict shape the API returns.

    Notably: SQLite has no native bool, so `done` is stored as 0/1 and
    converted back to a real Python bool here.
    """
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


def init_db() -> None:
    """Create the todos table if it does not already exist.

    Idempotent: safe to call on every startup and after module reload.
    """
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT    NOT NULL,
                done  INTEGER NOT NULL DEFAULT 0
            )
            """
        )


def get_all_todos() -> list[dict]:
    """Return every todo, ordered by id."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, title, done FROM todos ORDER BY id"
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_todo(todo_id: int) -> dict | None:
    """Return a single todo by id, or None if it doesn't exist."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, title, done FROM todos WHERE id = ?", (todo_id,)
        ).fetchone()
    return _row_to_dict(row) if row is not None else None


def create_todo(title: str, done: bool) -> dict:
    """Insert a new todo and return it, including the auto-assigned id."""
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO todos (title, done) VALUES (?, ?)",
            (title, int(done)),
        )
        new_id = cursor.lastrowid
    return {"id": new_id, "title": title, "done": bool(done)}


def update_todo(todo_id: int, title: str, done: bool) -> dict | None:
    """Update an existing todo's title and done flag.

    Returns the updated todo, or None if no row with that id exists.
    """
    with _connect() as conn:
        cursor = conn.execute(
            "UPDATE todos SET title = ?, done = ? WHERE id = ?",
            (title, int(done), todo_id),
        )
        if cursor.rowcount == 0:
            return None
    return {"id": todo_id, "title": title, "done": bool(done)}


def delete_todo(todo_id: int) -> bool:
    """Delete a todo by id. Return True if a row was deleted, else False."""
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        return cursor.rowcount > 0
