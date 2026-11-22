"""Smoke tests for core API routes; run with: pytest -q."""
import os
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient

from backend import main


@pytest.fixture()
def client(monkeypatch):
    handle, db_path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(handle)
    monkeypatch.setattr(main, "DB_PATH", Path(db_path))
    main.initialize_database()
    with TestClient(main.app) as test_client:
        yield test_client
    Path(db_path).unlink(missing_ok=True)


def test_health_and_root(client):
    assert client.get("/api/health").json()["status"] == "ok"
    response = client.get("/")
    assert response.status_code == 200
    assert "Iniciar sesión" in response.text


def test_register_login_and_lesson_progress(client):
    registered = client.post("/api/register", json={
        "name": "Estudiante Demo",
        "email": "demo@example.com",
        "password": "ClaveSegura123",
        "learning_goal": "Fundamentos de programación",
    })
    assert registered.status_code == 201
    assert "capricornio_session" in registered.cookies

    progress = client.get("/api/progress")
    assert progress.status_code == 200
    assert progress.json()["completed_count"] == 0

    adaptive = client.get("/api/learning/next", params={"area": "Fundamentos de programación"})
    assert adaptive.status_code == 200
    exercise = adaptive.json()
    assert exercise["item_id"] in {"fund_1", "fund_2", "fund_3"}
    answer_key = {"fund_1": "a", "fund_2": "b", "fund_3": "c"}
    submitted = client.post("/api/learning/answer", json={
        "area": "Fundamentos de programación",
        "item_id": exercise["item_id"],
        "answer": answer_key[exercise["item_id"]],
    })
    assert submitted.status_code == 200
    assert submitted.json()["correct"] is True
    next_exercise = client.get("/api/learning/next", params={"area": "Fundamentos de programación"})
    assert next_exercise.status_code == 200
    assert next_exercise.json()["item_id"] != exercise["item_id"]

    first = client.post("/api/lessons/complete", json={"lesson_id": "estructuras-for"})
    assert first.status_code == 200
    assert first.json()["completed_lessons"] == 1

    # Repeating the same completion is idempotent.
    second = client.post("/api/lessons/complete", json={"lesson_id": "estructuras-for"})
    assert second.status_code == 200
    assert second.json()["completed_lessons"] == 1

    client.post("/api/logout")
    assert client.get("/api/me").status_code == 401

    logged_in = client.post("/api/login", json={
        "email": "demo@example.com",
        "password": "ClaveSegura123",
    })
    assert logged_in.status_code == 200
    assert client.get("/api/me").status_code == 200


def test_lesson_requires_authentication(client):
    response = client.post("/api/lessons/complete", json={"lesson_id": "estructuras-for"})
    assert response.status_code == 401
