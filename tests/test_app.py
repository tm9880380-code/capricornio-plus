from fastapi.testclient import TestClient
from backend import main


def test_registration_login_and_learning_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "test.db")
    main.initialize_database()

    with TestClient(main.app) as client:
        created = client.post("/api/register", json={
            "name": "Estudiante Demo",
            "email": "demo@example.com",
            "password": "ClaveSegura123",
            "learning_goal": "Fundamentos de programación",
        })
        assert created.status_code == 201
        assert created.json()["user"]["email"] == "demo@example.com"

        me = client.get("/api/me")
        assert me.status_code == 200

        catalog = client.get("/api/learning/catalog")
        assert catalog.status_code == 200
        assert catalog.json()["total_lessons"] == 27

        lesson = client.get("/api/learning/lesson/prog-01")
        assert lesson.status_code == 200
        assert lesson.json()["id"] == "prog-01"

        answer = client.post(
            "/api/learning/lesson/prog-01/answer",
            json={"answer": "a"},
        )
        assert answer.status_code == 200
        assert answer.json()["correct"] is True

        updated = client.get("/api/learning/catalog").json()
        assert updated["completed_lessons"] == 1
        assert updated["progress_percent"] > 0

        logout = client.post("/api/logout")
        assert logout.status_code == 200
        assert client.get("/api/me").status_code == 401
