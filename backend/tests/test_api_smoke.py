"""Smoke tests for core API routes; run with: pytest -q."""
import os
import tempfile
import sys
import shutil
import subprocess
from html.parser import HTMLParser
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
    assert "Encuentra tu camino para aprender tecnología" in response.text
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"


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

@pytest.mark.parametrize("area", [
    "Ciberseguridad",
    "Desarrollo frontend",
    "Desarrollo backend",
    "Análisis de datos",
    "Inteligencia artificial y modelos de lenguaje",
    "Bases de datos",
    "Redes y sistemas",
    "Programación y lenguajes",
    "Python",
    "JavaScript",
    "Go",
    "Java",
    "C++",
])
def test_learning_routes_have_area_specific_diagnostic_bank(client, area):
    response = client.post("/api/register", json={
        "name": "Estudiante Ruta",
        "email": f"{area.lower().replace(' ', '').replace('/', '')}@example.com",
        "password": "ClaveSegura123",
        "learning_goal": area,
    })
    assert response.status_code == 201

    diagnostic = client.get("/api/diagnostic/questions")
    assert diagnostic.status_code == 200
    data = diagnostic.json()
    assert data["mode"] == "assessment"
    assert data["area"] == area
    assert len(data["questions"]) >= 6
    assert all(question["options"] for question in data["questions"])


def test_resource_library_page_is_served(client):
    page = client.get("/recursos.html")
    assert page.status_code == 200
    assert "Biblioteca de recursos gratuitos" in page.text

def test_orientation_recommends_new_area_and_starts_its_diagnostic(client):
    registered = client.post("/api/register", json={
        "name": "Estudiante Orientación",
        "email": "orientacion@example.com",
        "password": "ClaveSegura123",
        "learning_goal": "Aún no lo sé; necesito orientación",
    })
    assert registered.status_code == 201

    orientation = client.get("/api/diagnostic/questions").json()
    assert orientation["mode"] == "orientation"
    answers = {question["id"]: "Desarrollo frontend" for question in orientation["questions"]}
    result = client.post("/api/diagnostic/submit", json={
        "area": orientation["area"],
        "answers": answers,
    })
    assert result.status_code == 200
    assert result.json()["recommended_area"] == "Desarrollo frontend"

    assessment = client.get("/api/diagnostic/questions").json()
    assert assessment["mode"] == "assessment"
    assert assessment["area"] == "Desarrollo frontend"
    assert len(assessment["questions"]) == 6

def test_curriculum_contains_eight_areas_and_real_lesson_content(client):
    response = client.get("/api/curriculum")
    assert response.status_code == 200
    data = response.json()
    assert len(data["areas"]) == 8
    assert {area["id"] for area in data["areas"]} == {
        "ciberseguridad", "frontend", "backend", "datos",
        "ia", "bases-datos", "redes-sistemas", "programacion",
    }
    assert all(area["modules"] and area["description"] for area in data["areas"])


def test_curriculum_lesson_and_resources_are_available_after_login(client):
    registered = client.post("/api/register", json={
        "name": "Estudiante Currículo",
        "email": "curriculum@example.com",
        "password": "ClaveSegura123",
        "learning_goal": "Desarrollo frontend",
    })
    assert registered.status_code == 201

    lesson = client.get("/api/lessons/frontend-html")
    assert lesson.status_code == 200
    assert lesson.json()["lesson"]["title"] == "HTML semántico"

    resources = client.get("/api/resources/frontend")
    assert resources.status_code == 200
    assert any(item["title"] == "MDN HTML" for item in resources.json()["resources"])


def test_curriculum_diagnostic_records_area_specific_competencies(client):
    registered = client.post("/api/register", json={
        "name": "Estudiante Datos",
        "email": "datos@example.com",
        "password": "ClaveSegura123",
        "learning_goal": "Análisis de datos",
    })
    assert registered.status_code == 201
    diagnostic = client.get("/api/diagnostic/questions").json()
    assert diagnostic["area"] == "Análisis de datos"
    assert len(diagnostic["questions"]) == 6
    answers = {q["id"]: "a" for q in diagnostic["questions"]}
    submitted = client.post("/api/diagnostic/submit", json={
        "area": diagnostic["area"], "answers": answers
    })
    assert submitted.status_code == 200
    assert submitted.json()["total_questions"] == 6
    progress = client.get("/api/progress").json()
    assert progress["total_lessons"] == 6

class InlineScriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_script = False
        self.external = False
        self.current = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.in_script = True
            self.external = any(key == "src" for key, _ in attrs)
            self.current = []

    def handle_data(self, data):
        if self.in_script and not self.external:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.in_script:
            if not self.external:
                source = "".join(self.current).strip()
                if source:
                    self.scripts.append(source)
            self.in_script = False
            self.external = False


def test_inline_javascript_and_python_worker_have_valid_syntax(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is not installed in this test environment.")
    script_files = list((ROOT / "js").glob("*.js"))
    for index, path in enumerate(script_files):
        result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True)
        assert result.returncode == 0, f"{path}: {result.stderr}"

    for page in ROOT.glob("*.html"):
        parser = InlineScriptParser()
        parser.feed(page.read_text(encoding="utf-8"))
        for index, source in enumerate(parser.scripts):
            temp = tmp_path / f"{page.stem}-{index}.js"
            temp.write_text(source, encoding="utf-8")
            result = subprocess.run([node, "--check", str(temp)], capture_output=True, text=True)
            assert result.returncode == 0, f"{page.name} script {index}: {result.stderr}"


def test_python_code_attempt_updates_competency_and_saves_lesson(client):
    registered = client.post("/api/register", json={
        "name": "Estudiante Python",
        "email": "python@example.com",
        "password": "ClaveSegura123",
        "learning_goal": "Python",
    })
    assert registered.status_code == 201

    attempt = client.post("/api/lessons/attempt", json={
        "lesson_id": "fundamentos-variables",
        "correct": False,
    })
    assert attempt.status_code == 200
    assert attempt.json()["correct"] is False
    assert attempt.json()["competency_update"]["observations"] == 1

    completed = client.post("/api/lessons/complete", json={
        "lesson_id": "fundamentos-variables",
    })
    assert completed.status_code == 200
    assert completed.json()["progress_percent"] > 0

def test_mutating_requests_reject_foreign_origins(client):
    response = client.post("/api/logout", headers={"Origin": "https://malicious.example"})
    assert response.status_code == 403

