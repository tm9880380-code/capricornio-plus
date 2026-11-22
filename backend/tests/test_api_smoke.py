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
    assert "Trabajar, persistir y avanzar." in response.text
    assert "Aprender tecnología, con dirección." in response.text
    assert "Ya tengo una cuenta" in response.text
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_private_plan_page_redirects_anonymous_users_and_has_one_progress_target(client):
    anonymous = client.get("/plan.html", follow_redirects=False)
    assert anonymous.status_code == 303
    client.post("/api/register", json={
        "name": "Estudiante Plan", "email": "plan@example.com",
        "password": "ClaveSegura123", "learning_goal": "Ciberseguridad", "privacy_consent": True, "terms_accepted": True,
    })
    page = client.get("/plan.html")
    assert page.status_code == 200
    assert page.text.count('id="avance"') == 1
    assert 'id="resumen-avance"' in page.text
    assert 'id="siguiente-leccion"' in page.text


def test_register_login_and_lesson_progress(client):
    registered = client.post("/api/register", json={
        "name": "Estudiante Demo",
        "email": "demo@example.com",
        "password": "ClaveSegura123",
        "learning_goal": "Fundamentos de programación", "privacy_consent": True, "terms_accepted": True,
    })
    assert registered.status_code == 201
    assert "capricornio_session" in registered.cookies

    progress = client.get("/api/progress")
    assert progress.status_code == 200
    assert progress.json()["completed_count"] == 0

    adaptive = client.get("/api/learning/next", params={"area": "Fundamentos de programación"})
    assert adaptive.status_code == 200
    exercise = adaptive.json()
    assert exercise["item_id"].startswith("cur_")
    assert exercise["prompt"] == main.CURRICULUM_LESSON_BY_QUESTION[exercise["item_id"]]["question"]
    lesson = main.CURRICULUM_LESSON_BY_QUESTION[exercise["item_id"]]
    answer_value = chr(97 + lesson["options"].index(lesson["answer"]))
    submitted = client.post("/api/learning/answer", json={
        "area": "Fundamentos de programación",
        "item_id": exercise["item_id"],
        "answer": answer_value,
    })
    assert submitted.status_code == 200
    assert submitted.json()["correct"] is True
    assert submitted.json()["correct_answer"] == lesson["answer"]
    assert submitted.json()["explanation"] == lesson["feedback"]
    assert submitted.json()["reinforcement"]
    solved_lesson_id = lesson["id"]
    next_exercise = client.get("/api/learning/next", params={"area": "Fundamentos de programación"})
    assert next_exercise.status_code == 200
    assert next_exercise.json()["item_id"] != exercise["item_id"]

    first = client.post("/api/lessons/complete", json={"lesson_id": solved_lesson_id})
    assert first.status_code == 200
    assert first.json()["completed_lessons"] == 1

    # Repeating the same completion is idempotent.
    second = client.post("/api/lessons/complete", json={"lesson_id": solved_lesson_id})
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
        "learning_goal": area, "privacy_consent": True, "terms_accepted": True,
    })
    assert response.status_code == 201

    diagnostic = client.get("/api/diagnostic/questions")
    assert diagnostic.status_code == 200
    data = diagnostic.json()
    assert data["mode"] == "assessment"
    assert data["area"] == area
    assert len(data["questions"]) >= 6
    assert all(question["options"] for question in data["questions"])


def test_resource_library_page_requires_login(client):
    anonymous = client.get("/recursos.html", follow_redirects=False)
    assert anonymous.status_code == 303
    assert anonymous.headers["location"] == "/login.html?motivo=sesion"
    registered = client.post("/api/register", json={
        "name": "Estudiante Recursos", "email": "recursos@example.com",
        "password": "ClaveSegura123", "learning_goal": "Ciberseguridad", "privacy_consent": True, "terms_accepted": True,
    })
    assert registered.status_code == 201
    page = client.get("/recursos.html")
    assert page.status_code == 200
    assert "Biblioteca de recursos gratuitos" in page.text

def test_orientation_recommends_new_area_and_starts_its_diagnostic(client):
    registered = client.post("/api/register", json={
        "name": "Estudiante Orientación",
        "email": "orientacion@example.com",
        "password": "ClaveSegura123",
        "learning_goal": "Aún no lo sé; necesito orientación", "privacy_consent": True, "terms_accepted": True,
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
        "learning_goal": "Desarrollo frontend", "privacy_consent": True, "terms_accepted": True,
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
        "learning_goal": "Análisis de datos", "privacy_consent": True, "terms_accepted": True,
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


def test_python_code_attempt_is_graded_by_the_server(client):
    registered = client.post("/api/register", json={
        "name": "Estudiante Python",
        "email": "python@example.com",
        "password": "ClaveSegura123",
        "learning_goal": "Python", "privacy_consent": True, "terms_accepted": True,
    })
    assert registered.status_code == 201
    expected = main.CURRICULUM_LESSON_BY_QUESTION["cur_fundamentos_variables"]["expected_output"]

    failed = client.post("/api/lessons/attempt", json={"lesson_id": "fundamentos-variables", "error": True})
    assert failed.status_code == 200
    assert failed.json()["correct"] is False
    assert failed.json()["competency_update"]["observations"] == 1

    wrong = client.post("/api/lessons/attempt", json={"lesson_id": "fundamentos-variables", "output": "nada"})
    assert wrong.json()["correct"] is False
    assert client.post("/api/lessons/complete", json={"lesson_id": "fundamentos-variables"}).status_code == 403

    right = client.post("/api/lessons/attempt", json={"lesson_id": "fundamentos-variables", "output": expected + "\n"})
    assert right.json()["correct"] is True
    completed = client.post("/api/lessons/complete", json={"lesson_id": "fundamentos-variables"})
    assert completed.status_code == 200
    assert completed.json()["progress_percent"] > 0


def register_user(client, email="seguro@example.com", goal="Python"):
    response = client.post("/api/register", json={
        "name": "Estudiante Seguro", "email": email,
        "password": "ClaveSegura123", "learning_goal": goal, "privacy_consent": True, "terms_accepted": True,
    })
    assert response.status_code == 201
    return response


def test_client_cannot_forge_a_correct_attempt(client):
    register_user(client)
    forged = client.post("/api/lessons/attempt", json={"lesson_id": "fundamentos-variables", "correct": True})
    assert forged.status_code == 200
    assert forged.json()["correct"] is False


def test_lesson_cannot_be_completed_without_solving_it(client):
    register_user(client)
    response = client.post("/api/lessons/complete", json={"lesson_id": "estructuras-for"})
    assert response.status_code == 403
    assert client.get("/api/progress").json()["completed_count"] == 0


def test_public_endpoints_do_not_expose_answer_keys(client):
    secret_keys = ("answer", "feedback", "expected_output")
    public = client.get("/api/curriculum")
    assert public.status_code == 200
    for area_id in ("ciberseguridad", "programacion"):
        area = client.get(f"/api/curriculum/{area_id}")
        assert area.status_code == 200
        for text in (public.text, area.text):
            for key in secret_keys:
                assert f'"{key}"' not in text
    register_user(client)
    lesson = client.get("/api/lessons/fundamentos-variables")
    assert lesson.status_code == 200
    for key in secret_keys:
        assert key not in lesson.json()["lesson"]


def test_lesson_mode_hides_answer_but_practice_mode_explains_it(client):
    register_user(client, goal="Ciberseguridad")
    lesson = main.CURRICULUM_LESSON_BY_QUESTION["cur_cyber_fundamentos"]
    wrong_index = next(i for i, option in enumerate(lesson["options"]) if option != lesson["answer"])
    payload = {"area": "Ciberseguridad", "item_id": "cur_cyber_fundamentos", "answer": chr(97 + wrong_index)}
    in_lesson = client.post("/api/learning/answer", json={**payload, "mode": "lesson"}).json()
    assert in_lesson["correct"] is False
    assert in_lesson["correct_answer"] is None and in_lesson["explanation"] is None
    assert lesson["answer"] not in in_lesson["feedback"]
    in_practice = client.post("/api/learning/answer", json={**payload, "mode": "practice"}).json()
    assert in_practice["correct_answer"] == lesson["answer"]


def test_correct_answers_are_spread_across_positions():
    positions = [
        lesson["options"].index(lesson["answer"])
        for area in main.CURRICULUM["areas"]
        for module in area["modules"]
        for lesson in module["lessons"]
    ]
    assert len(positions) == 50
    for position in range(4):
        assert positions.count(position) >= 8


def test_login_is_rate_limited_per_email(client):
    register_user(client, email="limite@example.com")
    client.post("/api/logout")
    for _ in range(main.MAX_LOGIN_FAILURES_PER_EMAIL):
        failed = client.post("/api/login", json={"email": "limite@example.com", "password": "incorrecta123"})
        assert failed.status_code == 401
    blocked = client.post("/api/login", json={"email": "limite@example.com", "password": "ClaveSegura123"})
    assert blocked.status_code == 429


def test_successful_login_clears_earlier_failures(client):
    register_user(client, email="reinicio@example.com")
    client.post("/api/logout")
    for _ in range(main.MAX_LOGIN_FAILURES_PER_EMAIL - 1):
        client.post("/api/login", json={"email": "reinicio@example.com", "password": "incorrecta123"})
    assert client.post("/api/login", json={"email": "reinicio@example.com", "password": "ClaveSegura123"}).status_code == 200
    client.post("/api/logout")
    assert client.post("/api/login", json={"email": "reinicio@example.com", "password": "incorrecta123"}).status_code == 401


def test_registration_is_rate_limited_per_ip(client):
    for index in range(main.MAX_REGISTRATIONS_PER_IP):
        assert client.post("/api/register", json={
            "name": "Usuario Masivo", "email": f"masivo{index}@example.com",
            "password": "ClaveSegura123", "learning_goal": "Python", "privacy_consent": True, "terms_accepted": True,
        }).status_code == 201
    extra = client.post("/api/register", json={
        "name": "Usuario Masivo", "email": "masivo-extra@example.com",
        "password": "ClaveSegura123", "learning_goal": "Python", "privacy_consent": True, "terms_accepted": True,
    })
    assert extra.status_code == 429


def test_account_can_be_deleted_with_password(client):
    register_user(client, email="borrar@example.com")
    wrong = client.post("/api/account/delete", json={"password": "incorrecta123"})
    assert wrong.status_code == 401
    assert client.get("/api/me").status_code == 200
    deleted = client.post("/api/account/delete", json={"password": "ClaveSegura123"})
    assert deleted.status_code == 200
    assert client.get("/api/me").status_code == 401
    relogin = client.post("/api/login", json={"email": "borrar@example.com", "password": "ClaveSegura123"})
    assert relogin.status_code == 401
    with main.closing(main.connect()) as db:
        assert db.execute("SELECT COUNT(*) FROM users WHERE email = ?", ("borrar@example.com",)).fetchone()[0] == 0


def test_security_headers_include_csp_and_no_store_for_api(client):
    page = client.get("/")
    csp = page.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in csp and "'unsafe-eval'" not in csp
    worker = client.get("/js/python-runner.js")
    assert "'unsafe-eval'" in worker.headers["content-security-policy"]
    assert client.get("/api/health").headers["cache-control"] == "no-store"


def test_mutating_requests_reject_foreign_origins(client):
    response = client.post("/api/logout", headers={"Origin": "https://malicious.example"})
    assert response.status_code == 403

def test_login_does_not_disclose_whether_email_exists(client):
    unknown = client.post("/api/login", json={
        "email": "missing@example.com", "password": "ClaveSegura123"
    })
    assert unknown.status_code == 401
    assert unknown.json()["detail"] == "Correo electrónico o contraseña incorrectos."



def test_curriculum_resources_competencies_and_projects_are_consistent():
    assert len(main.CURRICULUM["areas"]) == 8
    for area in main.CURRICULUM["areas"]:
        resource_titles = {resource["title"] for resource in area["resources"]}
        assert 4 <= len(resource_titles) <= 8
        assert area["competencies"]
        assert area["capstone_project"]["deliverables"]
        assert area["capstone_project"]["rubric"]
        for module in area["modules"]:
            for lesson in module["lessons"]:
                assert set(lesson.get("resource_ids", [])) <= resource_titles
                assert lesson.get("reinforcement")


def test_learning_environment_page_requires_login(client):
    anonymous = client.get("/entorno.html", follow_redirects=False)
    assert anonymous.status_code == 303
    client.post("/api/register", json={
        "name": "Estudiante Entorno", "email": "entorno@example.com",
        "password": "ClaveSegura123", "learning_goal": "Ciberseguridad", "privacy_consent": True, "terms_accepted": True,
    })
    response = client.get("/entorno.html")
    assert response.status_code == 200
    assert "Mi entorno de aprendizaje" in response.text
    assert "JavaScript" in response.text

 
def test_lesson_page_has_guided_resource_and_return_flow(client):
    anonymous = client.get("/leccion.html", follow_redirects=False)
    assert anonymous.status_code == 303
    client.post("/api/register", json={
        "name": "Estudiante Lección", "email": "leccion@example.com",
        "password": "ClaveSegura123", "learning_goal": "Ciberseguridad", "privacy_consent": True, "terms_accepted": True,
    })
    page = client.get("/leccion.html")
    assert page.status_code == 200
    assert "Prepárate para aprender en la fuente" in page.text
    assert "Vuelve y comprobemos qué encontraste" in page.text
    assert "No lo entendí; explícame de otra forma" in page.text
    assert "Ya entendí · Ir a la práctica" in page.text
    assert "Errores que conviene evitar" in page.text
    assert "Practica el razonamiento paso a paso" in page.text
    assert 'id="practica" hidden' in page.text

 
def test_curriculum_lessons_include_learning_and_reading_guides(client):
    response = client.get("/api/curriculum")
    assert response.status_code == 200
    lessons = [
        lesson
        for area in response.json()["areas"]
        for module in area["modules"]
        for lesson in module["lessons"]
    ]
    assert len(lessons) == 50
    assert all(lesson.get("learning_objective") for lesson in lessons)
    assert all(lesson.get("why_it_matters") for lesson in lessons)
    assert all(len(lesson.get("reading_guide", [])) >= 4 for lesson in lessons)
    assert all(lesson.get("reflection_prompt") for lesson in lessons)


def test_all_curriculum_lessons_have_explanations_examples_and_practice_steps(client):
    response = client.get("/api/curriculum")
    assert response.status_code == 200
    lessons = [lesson for area in response.json()["areas"] for module in area["modules"] for lesson in module["lessons"]]
    assert all(len(lesson.get("explanation", "").split()) >= 35 for lesson in lessons)
    assert all(len(lesson.get("example", "").split()) >= 20 for lesson in lessons)
    assert all(lesson.get("common_mistake") for lesson in lessons)
    assert all(len(lesson.get("guided_steps", [])) >= 4 for lesson in lessons)

def test_login_rejects_oversized_credentials(client):
    response = client.post("/api/login", json={
        "email": "student@example.com",
        "password": "x" * 129,
    })
    assert response.status_code == 422


def test_adaptive_practice_passes_current_time_to_spaced_review_engine(client, monkeypatch):
    register_user(client, email="repaso@example.com", goal="Programación y lenguajes")
    observed = {}

    class ReviewEngineProbe:
        def __init__(self, bank, seed=None):
            self.bank = bank

        def next_item(self, state, now=None):
            observed["now"] = now
            return main.Item(id=self.bank.ids[0], difficulty=0.0)

    monkeypatch.setattr(main, "AdaptiveEngine", ReviewEngineProbe)
    response = client.get("/api/learning/next", params={"area": "Programación y lenguajes"})
    assert response.status_code == 200
    assert observed["now"] is not None
    assert observed["now"] > 0


def test_registration_requires_explicit_privacy_consent_and_terms(client):
    payload = {
        "name": "Estudiante Sin Consentimiento",
        "email": "sin-consentimiento@example.com",
        "password": "ClaveSegura123",
        "learning_goal": "Python",
        "terms_accepted": True,
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422
    assert "autorizar expresamente" in response.json()["detail"]

    payload["privacy_consent"] = True
    payload["terms_accepted"] = False
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422
    assert "aceptar los términos" in response.json()["detail"]

    payload["terms_accepted"] = True
    response = client.post("/api/register", json=payload)
    assert response.status_code == 201
    from backend import main as app_main
    with app_main.closing(app_main.connect()) as db:
        consent = db.execute(
            "SELECT privacy_policy_version, terms_version, consented_at FROM privacy_consents"
        ).fetchone()
    assert consent["privacy_policy_version"] == app_main.PRIVACY_POLICY_VERSION
    assert consent["terms_version"] == app_main.TERMS_VERSION
    assert consent["consented_at"].endswith("Z")


def test_legal_pages_are_public_without_an_account(client):
    for page in (
        "privacidad", "aviso-privacidad", "terminos", "cookies", "accesibilidad",
        "uso-responsable", "seguridad", "mapa-sitio", "creditos", "politica-comercial",
    ):
        response = client.get(f"/{page}.html")
        assert response.status_code == 200
        assert "<title>" in response.text
