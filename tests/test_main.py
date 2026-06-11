"""
Tests for pipeline-lab.

Run locally with:  pytest -v
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_todos_returns_list():
    response = client.get("/todos")
    assert response.status_code == 200
    body = response.json()
    assert "todos" in body
    assert "count" in body
    assert body["count"] == len(body["todos"])
    assert body["count"] >= 1


def test_todos_have_expected_shape():
    response = client.get("/todos")
    todo = response.json()["todos"][0]
    assert set(todo.keys()) == {"id", "title", "done"}
    assert isinstance(todo["id"], int)
    assert isinstance(todo["title"], str)
    assert isinstance(todo["done"], bool)


def test_get_existing_todo_returns_it():
    response = client.get("/todos/1")
    assert response.status_code == 200
    todo = response.json()
    assert todo["id"] == 1
    assert set(todo.keys()) == {"id", "title", "done"}


def test_get_nonexistent_todo_returns_404():
    response = client.get("/todos/9999")
    assert response.status_code == 404
    assert "detail" in response.json()


def test_get_todo_with_non_integer_id_returns_422():
    response = client.get("/todos/abc")
    assert response.status_code == 422

def test_create_todo_returns_created_todo():
    new_todo ={"title": "Buy groceries", "done":False}
    response = client.post("/todos", json =new_todo)
    assert response.status_code ==201
    created = response.json()
    assert created["title"]== "Buy groceries"
    assert created ["done"] is False
    assert "id" in created


def test_create_todo_missing_title_returns_422():
    response = client.post("/todos", json={})
    assert response.status_code == 422


def test_create_todo_appears_in_list():
    response = client.post("/todos", json={"title": "Should show up"})
    assert response.status_code == 201
    created_id = response.json()["id"]

    list_response = client.get("/todos")
    todos = list_response.json()["todos"]
    assert any(t["id"] == created_id and t["title"] == "Should show up" for t in todos)

def test_update_existing_todo():
    update_data = {"title": "updated title", "done": True}

    response = client.put("/todos/1", json=update_data)
    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "updated title"
    assert updated["done"] is True
    assert updated["id"] == 1


def test_update_non_existent_todo_returns_404():
    response = client.put("/todos/9999", json={"title": "ghost"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Todo not found"


def test_update_todo_persists_changes():
    # Create a fresh todo so we control its id and starting state.
    created = client.post("/todos", json={"title": "before", "done": False}).json()
    todo_id = created["id"]

    # Update it.
    put_response = client.put(f"/todos/{todo_id}", json={"title": "after", "done": True})
    assert put_response.status_code == 200

    # Read it back independently and confirm the change stuck.
    fetched = client.get(f"/todos/{todo_id}").json()
    assert fetched["title"] == "after"
    assert fetched["done"] is True

