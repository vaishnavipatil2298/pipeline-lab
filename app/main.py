"""
pipeline-lab: a tiny FastAPI service used to practice Docker + CI/CD + testing.

Week 1 goal: two endpoints, tested with pytest, containerized, running in GitHub Actions.
"""
from fastapi import FastAPI, HTTPException

app = FastAPI(title="pipeline-lab", version="0.1.0")

# In-memory state for Week 1. We'll replace this with a real DB in Week 2.
_todos = [
    {"id": 1, "title": "Learn Docker", "done": False},
    {"id": 2, "title": "Ship CI/CD pipeline", "done": False},
    {"id": 3, "title": "Connect Claude Code to workflow", "done": False},
]


@app.get("/health")
def health():
    """Liveness check for container orchestrators."""
    return {"status": "ok"}


@app.get("/todos")
def list_todos():
    """Return all todos."""
    return {"todos": _todos, "count": len(_todos)}


@app.get("/todos/{todo_id}")
def get_todo(todo_id: int):
    """Return a single todo by id, or 404 if it doesn't exist."""
    for todo in _todos:
        if todo["id"] == todo_id:
            return todo
    raise HTTPException(status_code=404, detail="Todo not found")
