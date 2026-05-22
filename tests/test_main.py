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
