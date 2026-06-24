"""
pipeline-lab: a tiny FastAPI service used to practice Docker + CI/CD + testing.

Week 2 goal: persist todos in SQLite instead of an in-memory list.

This module is the API layer only — it contains NO SQL. All storage access
goes through app.database.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app import database

app = FastAPI(title="pipeline-lab", version="0.2.0")

# Ensure the table exists before we serve any requests. Idempotent.
database.init_db()


class TodoCreate(BaseModel):
    title: str
    done: bool = False


class TodoUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


@app.get("/health")
def health():
    """Liveness check for container orchestrators."""
    return {"status": "ok"}


@app.get("/todos")
def list_todos():
    """Return all todos."""
    todos = database.get_all_todos()
    return {"todos": todos, "count": len(todos)}


@app.get("/todos/{todo_id}")
def get_todo(todo_id: int):
    """Return a single todo by id, or 404 if it doesn't exist."""
    todo = database.get_todo(todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@app.post("/todos", status_code=201)
def create_todo(payload: TodoCreate):
    """Create a new todo and return it with an auto-assigned id."""
    return database.create_todo(payload.title, payload.done)


@app.put("/todos/{todo_id}")
def update_todo(todo_id: int, payload: TodoUpdate):
    """Update an existing todo's title and/or done flag, or 404 if missing.

    Partial update: fields omitted from the payload keep their current value.
    """
    existing = database.get_todo(todo_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    new_title = payload.title if payload.title is not None else existing["title"]
    new_done = payload.done if payload.done is not None else existing["done"]
    return database.update_todo(todo_id, new_title, new_done)


@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    """Delete a todo by id. Return 204 on success, or 404 if it doesn't exist."""
    if not database.delete_todo(todo_id):
        raise HTTPException(status_code=404, detail="Todo not found")
