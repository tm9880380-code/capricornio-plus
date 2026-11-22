import os
import json
import re
import sqlite3
import hashlib
import secrets
import time
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response as FastAPIResponse, Cookie, Depends
from pydantic import BaseModel, Field
from pwdlib import PasswordHash

from backend.adaptive.adaptive_engine import (
    AdaptiveEngine,
    Item,
    ItemBank,
    LearnerState,
    Response as AdaptiveResponse,
)
from backend.adaptive.bkt import BKTParameters, update_mastery

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "capricornio.db"

SESSION_DAYS = 30
COOKIE_NAME = "capricornio_session"
password_hash = PasswordHash.recommended()

app = FastAPI(title="Capricornio API", version="1.0.0")


def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize_database():
    with closing(connect()) as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                learning_goal TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at REAL NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS student_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                completed_lessons INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS lesson_completions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lesson_id TEXT NOT NULL,
                completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, lesson_id),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        db.executescript("""
            CREATE TABLE IF NOT EXISTS diagnostic_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                learning_area TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'in_progress',
                detected_level TEXT,
                score REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS diagnostic_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                question_id TEXT NOT NULL,
                answer_value TEXT NOT NULL,
                is_correct INTEGER,
                answered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(attempt_id) REFERENCES diagnostic_attempts(id) ON DELETE CASCADE,
                UNIQUE(attempt_id, question_id)
            );

            CREATE TABLE IF NOT EXISTS learning_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                item_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                is_correct INTEGER NOT NULL CHECK(is_correct IN (0, 1)),
                created_at REAL NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS student_skill_mastery (
                user_id INTEGER NOT NULL,
                skill_id TEXT NOT NULL,
                prob_mastery REAL NOT NULL DEFAULT 0.10,
                prob_slip REAL NOT NULL DEFAULT 0.10,
                prob_guess REAL NOT NULL DEFAULT 0.20,
                prob_transit REAL NOT NULL DEFAULT 0.10,
                observations INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(user_id, skill_id),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS student_irt_state (
                user_id INTEGER NOT NULL,
                learning_area TEXT NOT NULL,
                state_json TEXT NOT NULL,
                ability REAL NOT NULL DEFAULT 0.0,
                ability_se REAL NOT NULL DEFAULT 1.0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(user_id, learning_area),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_learning_events_user
            ON learning_events(user_id, created_at);

            CREATE INDEX IF NOT EXISTS idx_learning_events_skill
            ON learning_events(user_id, skill_id, created_at);
        """)

        db.commit()


@app.on_event("startup")
def startup():
    initialize_database()


class RegisterData(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    learning_goal: str = Field(default="Fundamentos de programación", max_length=100)


class LoginData(BaseModel):
    email: str
    password: str


def normalize_email(email):
    email = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=422, detail="Correo electrónico no válido.")
    return email


def create_session(db, user_id, response: FastAPIResponse):
    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires = time.time() + SESSION_DAYS * 86400

    db.execute(
        "INSERT INTO sessions (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
        (user_id, token_hash, expires)
    )
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_DAYS * 86400,
        httponly=True,
        secure=os.getenv("CAPRICORNIO_HTTPS") == "1",
        samesite="lax",
        path="/"
    )


def current_user(
    capricornio_session: str | None = Cookie(default=None)
):
    if not capricornio_session:
        raise HTTPException(status_code=401, detail="Inicia sesión para continuar.")

    token_hash = hashlib.sha256(capricornio_session.encode()).hexdigest()

    with closing(connect()) as db:
        row = db.execute("""
            SELECT users.id, users.name, users.email, users.learning_goal
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > ?
        """, (token_hash, time.time())).fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="Sesión inválida o vencida.")

    return dict(row)



AREAS = [
    "Ciberseguridad",
    "Desarrollo de software y programación",
    "Desarrollo web",
    "Análisis de datos",
    "Bases de datos",
    "Inteligencia artificial",
    "Redes y sistemas",
    "Fundamentos de programación",
    "Programación orientada a objetos",
]

ORIENTATION_ID = "Aún no lo sé; necesito orientación"

QUESTION_BANK = {
    "Ciberseguridad": [
        ("cyber_1", "¿Qué busca principalmente la ciberseguridad?",
         [("a", "Proteger sistemas, redes y datos"), ("b", "Diseñar páginas web"), ("c", "Aumentar la velocidad del computador"), ("d", "No lo sé todavía")], "a"),
        ("cyber_2", "¿Qué característica hace más segura una contraseña?",
         [("a", "Usar solo el nombre propio"), ("b", "Ser larga y difícil de adivinar"), ("c", "Repetir números sencillos"), ("d", "No lo sé todavía")], "b"),
        ("cyber_3", "Si recibes un correo que pide tu contraseña mediante un enlace extraño, ¿qué haces?",
         [("a", "Abrirlo y escribir la contraseña"), ("b", "Reenviarlo a todos"), ("c", "No abrir el enlace y verificar el remitente"), ("d", "No lo sé todavía")], "c"),
    ],
    "Desarrollo de software y programación": [
        ("software_1", "¿Qué es un algoritmo?",
         [("a", "Una secuencia de pasos para resolver un problema"), ("b", "Una pieza física del computador"), ("c", "Un tipo de pantalla"), ("d", "No lo sé todavía")], "a"),
        ("software_2", "¿Para qué sirve una variable en un programa?",
         [("a", "Para apagar el computador"), ("b", "Para guardar un valor que puede utilizarse"), ("c", "Para conectar cables"), ("d", "No lo sé todavía")], "b"),
        ("software_3", "¿Qué hace una condición en un programa?",
         [("a", "Repite siempre todas las instrucciones"), ("b", "Borra los archivos"), ("c", "Permite tomar decisiones según una situación"), ("d", "No lo sé todavía")], "c"),
    ],
    "Desarrollo web": [
        ("web_1", "¿Qué lenguaje define principalmente la estructura de una página web?",
         [("a", "HTML"), ("b", "SQL"), ("c", "Python exclusivamente"), ("d", "No lo sé todavía")], "a"),
        ("web_2", "¿Para qué se utiliza CSS?",
         [("a", "Guardar contraseñas"), ("b", "Dar estilos y presentación a una página"), ("c", "Administrar redes"), ("d", "No lo sé todavía")], "b"),
        ("web_3", "¿Qué permite JavaScript en una página web?",
         [("a", "Reemplazar el sistema operativo"), ("b", "Crear bases de datos físicas"), ("c", "Agregar interacción y comportamiento"), ("d", "No lo sé todavía")], "c"),
    ],
    "Análisis de datos": [
        ("data_1", "¿Qué significa analizar datos?",
         [("a", "Examinar información para encontrar patrones o conclusiones"), ("b", "Cambiar el color de una pantalla"), ("c", "Instalar programas sin revisarlos"), ("d", "No lo sé todavía")], "a"),
        ("data_2", "¿Para qué sirve una tabla de datos?",
         [("a", "Reproducir videos"), ("b", "Organizar información en filas y columnas"), ("c", "Proteger físicamente un computador"), ("d", "No lo sé todavía")], "b"),
        ("data_3", "Si quieres conocer el promedio de varias notas, ¿qué necesitas?",
         [("a", "Ordenarlas alfabéticamente"), ("b", "Contar solo la nota más alta"), ("c", "Sumarlas y dividir entre la cantidad"), ("d", "No lo sé todavía")], "c"),
    ],
    "Bases de datos": [
        ("db_1", "¿Para qué sirve una base de datos?",
         [("a", "Almacenar y organizar información"), ("b", "Diseñar componentes electrónicos"), ("c", "Aumentar el brillo del monitor"), ("d", "No lo sé todavía")], "a"),
        ("db_2", "En una tabla, ¿qué representa normalmente una fila?",
         [("a", "El nombre del programa"), ("b", "Un registro"), ("c", "Una conexión a internet"), ("d", "No lo sé todavía")], "b"),
        ("db_3", "¿Qué permite hacer SQL?",
         [("a", "Editar fotografías"), ("b", "Crear animaciones"), ("c", "Consultar y gestionar datos en bases de datos"), ("d", "No lo sé todavía")], "c"),
    ],
    "Inteligencia artificial": [
        ("ai_1", "¿Qué busca hacer un sistema de inteligencia artificial?",
         [("a", "Realizar tareas que requieren capacidades como reconocer patrones"), ("b", "Reemplazar todos los cables"), ("c", "Aumentar físicamente la memoria"), ("d", "No lo sé todavía")], "a"),
        ("ai_2", "¿Qué necesita aprender un modelo supervisado?",
         [("a", "Solo el color de la pantalla"), ("b", "Ejemplos de datos acompañados de respuestas o etiquetas"), ("c", "La contraseña del usuario"), ("d", "No lo sé todavía")], "b"),
        ("ai_3", "¿Qué es un conjunto de entrenamiento?",
         [("a", "Una lista de contraseñas"), ("b", "Un grupo de cables"), ("c", "Datos utilizados para ajustar un modelo"), ("d", "No lo sé todavía")], "c"),
    ],
    "Redes y sistemas": [
        ("net_1", "¿Qué permite una red informática?",
         [("a", "Conectar dispositivos para intercambiar información"), ("b", "Cambiar el idioma de un teclado"), ("c", "Editar documentos sin software"), ("d", "No lo sé todavía")], "a"),
        ("net_2", "¿Qué identifica normalmente una dirección IP?",
         [("a", "El modelo del monitor"), ("b", "Un dispositivo o interfaz dentro de una red"), ("c", "La contraseña del correo"), ("d", "No lo sé todavía")], "b"),
        ("net_3", "¿Cuál es una función de un sistema operativo?",
         [("a", "Diseñar páginas web automáticamente"), ("b", "Crear señales de televisión"), ("c", "Administrar recursos del equipo y permitir ejecutar programas"), ("d", "No lo sé todavía")], "c"),
    ],
    "Fundamentos de programación": [
        ("fund_1", "¿Qué es una instrucción en programación?",
         [("a", "Una orden que el programa puede ejecutar"), ("b", "Una pieza del teclado"), ("c", "Un archivo de música"), ("d", "No lo sé todavía")], "a"),
        ("fund_2", "¿Qué representa el valor 10 en una operación como 4 + 10?",
         [("a", "Una condición"), ("b", "Un dato numérico"), ("c", "Un ciclo"), ("d", "No lo sé todavía")], "b"),
        ("fund_3", "¿Qué es un ciclo o bucle?",
         [("a", "Una variable que nunca cambia"), ("b", "Un tipo de error"), ("c", "Una estructura que repite instrucciones"), ("d", "No lo sé todavía")], "c"),
    ],
    "Programación orientada a objetos": [
        ("oop_1", "¿Qué es una clase en programación orientada a objetos?",
         [("a", "Un molde que define características y comportamientos"), ("b", "Una carpeta del sistema operativo"), ("c", "Una conexión de red"), ("d", "No lo sé todavía")], "a"),
        ("oop_2", "¿Qué es un objeto?",
         [("a", "Una instrucción para repetir código"), ("b", "Una instancia creada a partir de una clase"), ("c", "Un tipo de base de datos"), ("d", "No lo sé todavía")], "b"),
        ("oop_3", "¿Qué permite la encapsulación?",
         [("a", "Repetir instrucciones sin límite"), ("b", "Convertir código en imágenes"), ("c", "Agrupar datos y controlar el acceso a ellos"), ("d", "No lo sé todavía")], "c"),
    ],
}


SKILL_BY_QUESTION = {
    "cyber_1": "ciberseguridad.proteccion",
    "cyber_2": "ciberseguridad.contrasenas",
    "cyber_3": "ciberseguridad.phishing",
    "software_1": "software.algoritmos",
    "software_2": "software.variables",
    "software_3": "software.condiciones",
    "web_1": "web.html",
    "web_2": "web.css",
    "web_3": "web.javascript",
    "data_1": "datos.analisis",
    "data_2": "datos.organizacion",
    "data_3": "datos.estadistica",
    "db_1": "bases_datos.almacenamiento",
    "db_2": "bases_datos.registros",
    "db_3": "bases_datos.sql",
    "ai_1": "ia.conceptos",
    "ai_2": "ia.aprendizaje_supervisado",
    "ai_3": "ia.entrenamiento",
    "net_1": "redes.conectividad",
    "net_2": "redes.direccionamiento_ip",
    "net_3": "sistemas.sistema_operativo",
    "fund_1": "programacion.instrucciones",
    "fund_2": "programacion.datos",
    "fund_3": "programacion.ciclos",
    "oop_1": "poo.clases",
    "oop_2": "poo.objetos",
    "oop_3": "poo.encapsulacion",
}


def record_learning_response(
    db, user_id, source, item_id, skill_id, learning_area, correct
):
    """Registra una respuesta y actualiza BKT e IRT para el estudiante."""
    timestamp = time.time()

    mastery_row = db.execute(
        """
        SELECT prob_mastery, prob_slip, prob_guess, prob_transit, observations
        FROM student_skill_mastery
        WHERE user_id = ? AND skill_id = ?
        """,
        (user_id, skill_id),
    ).fetchone()

    if mastery_row:
        mastery = mastery_row["prob_mastery"]
        observations = mastery_row["observations"]
        params = BKTParameters(
            initial_mastery=mastery,
            learning_transition=mastery_row["prob_transit"],
            guess=mastery_row["prob_guess"],
            slip=mastery_row["prob_slip"],
        )
    else:
        params = BKTParameters()
        mastery = params.initial_mastery
        observations = 0

    updated_mastery = update_mastery(mastery, bool(correct), params)

    db.execute(
        """
        INSERT INTO student_skill_mastery
            (user_id, skill_id, prob_mastery, prob_slip, prob_guess,
             prob_transit, observations, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, skill_id) DO UPDATE SET
            prob_mastery = excluded.prob_mastery,
            observations = excluded.observations,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            user_id, skill_id, updated_mastery, params.slip,
            params.guess, params.learning_transition, observations + 1,
        ),
    )

    db.execute(
        """
        INSERT INTO learning_events
            (user_id, source, item_id, skill_id, is_correct, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, source, item_id, skill_id, int(bool(correct)), timestamp),
    )

    questions = QUESTION_BANK[learning_area]
    bank = ItemBank([
        Item(
            id=q[0],
            difficulty=0.0,
            discrimination=1.0,
            tags=(learning_area, SKILL_BY_QUESTION[q[0]]),
        )
        for q in questions
    ])
    engine = AdaptiveEngine(bank)

    saved = db.execute(
        """
        SELECT state_json
        FROM student_irt_state
        WHERE user_id = ? AND learning_area = ?
        """,
        (user_id, learning_area),
    ).fetchone()

    state = LearnerState.from_dict(json.loads(saved["state_json"])) if saved else LearnerState()
    state = engine.record_response(
        state, AdaptiveResponse(item_id=item_id, correct=bool(correct), timestamp=timestamp)
    )

    db.execute(
        """
        INSERT INTO student_irt_state
            (user_id, learning_area, state_json, ability, ability_se, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, learning_area) DO UPDATE SET
            state_json = excluded.state_json,
            ability = excluded.ability,
            ability_se = excluded.ability_se,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            user_id, learning_area, json.dumps(state.to_dict()),
            state.ability, state.ability_se,
        ),
    )

    return {
        "skill_id": skill_id,
        "mastery": round(updated_mastery, 4),
        "observations": observations + 1,
        "ability": round(state.ability, 4),
        "ability_se": round(state.ability_se, 4),
    }


ORIENTATION_QUESTIONS = [
    {
        "id": "orient_1",
        "prompt": "¿Qué actividad te llama más la atención?",
        "options": [
            {"value": "Ciberseguridad", "label": "Investigar cómo proteger información y sistemas"},
            {"value": "Desarrollo de software y programación", "label": "Crear programas que resuelvan problemas"},
            {"value": "Desarrollo web", "label": "Construir páginas y aplicaciones web"},
            {"value": "Análisis de datos", "label": "Encontrar respuestas a partir de datos"},
            {"value": "Bases de datos", "label": "Organizar información para consultarla"},
            {"value": "Inteligencia artificial", "label": "Crear sistemas que aprendan de datos"},
            {"value": "Redes y sistemas", "label": "Entender cómo se conectan y funcionan los equipos"},
            {"value": "Fundamentos de programación", "label": "Aprender desde cero a dar instrucciones a un computador"},
            {"value": "Programación orientada a objetos", "label": "Diseñar programas con componentes organizados"},
        ],
    },
    {
        "id": "orient_2",
        "prompt": "¿Qué tipo de reto preferirías explorar?",
        "options": [
            {"value": "Ciberseguridad", "label": "Detectar riesgos y proteger cuentas"},
            {"value": "Desarrollo de software y programación", "label": "Resolver un problema paso a paso con código"},
            {"value": "Desarrollo web", "label": "Diseñar una página interactiva"},
            {"value": "Análisis de datos", "label": "Descubrir tendencias en una tabla"},
            {"value": "Bases de datos", "label": "Guardar y encontrar información rápidamente"},
            {"value": "Inteligencia artificial", "label": "Enseñar a un sistema a reconocer patrones"},
            {"value": "Redes y sistemas", "label": "Comprender por qué dos equipos no se conectan"},
            {"value": "Fundamentos de programación", "label": "Aprender la lógica básica de los programas"},
            {"value": "Programación orientada a objetos", "label": "Organizar un programa en objetos y responsabilidades"},
        ],
    },
    {
        "id": "orient_3",
        "prompt": "¿Cuál de estas metas te gustaría alcanzar?",
        "options": [
            {"value": "Ciberseguridad", "label": "Ayudar a mantener seguros los sistemas"},
            {"value": "Desarrollo de software y programación", "label": "Crear herramientas y aplicaciones"},
            {"value": "Desarrollo web", "label": "Publicar sitios web propios"},
            {"value": "Análisis de datos", "label": "Convertir datos en decisiones útiles"},
            {"value": "Bases de datos", "label": "Diseñar sistemas para manejar información"},
            {"value": "Inteligencia artificial", "label": "Desarrollar soluciones inteligentes"},
            {"value": "Redes y sistemas", "label": "Administrar equipos, servidores y redes"},
            {"value": "Fundamentos de programación", "label": "Comprender cómo se construye el software"},
            {"value": "Programación orientada a objetos", "label": "Crear programas grandes y bien organizados"},
        ],
    },
]


class DiagnosticSubmitData(BaseModel):
    area: str = Field(min_length=2, max_length=100)
    answers: dict[str, str]


@app.get("/api/diagnostic/questions")
def diagnostic_questions(area: str | None = None, user=Depends(current_user)):
    with closing(connect()) as db:
        attempt = db.execute(
            """
            SELECT learning_area
            FROM diagnostic_attempts
            WHERE user_id = ? AND status = 'in_progress'
            ORDER BY id DESC
            LIMIT 1
            """,
            (user["id"],),
        ).fetchone()

    selected = attempt["learning_area"] if attempt else (area or user["learning_goal"])

    if selected == ORIENTATION_ID or selected not in AREAS:
        return {
            "mode": "orientation",
            "area": ORIENTATION_ID,
            "questions": ORIENTATION_QUESTIONS,
        }

    questions = QUESTION_BANK[selected]
    return {
        "mode": "assessment",
        "area": selected,
        "questions": [
            {
                "id": qid,
                "prompt": prompt,
                "options": [{"value": value, "label": label} for value, label in options],
            }
            for qid, prompt, options, correct in questions
        ],
    }


@app.post("/api/diagnostic/submit")
def submit_diagnostic(data: DiagnosticSubmitData, user=Depends(current_user)):
    if data.area == ORIENTATION_ID:
        questions = ORIENTATION_QUESTIONS
        expected = {q["id"]: {o["value"] for o in q["options"]} for q in questions}

        if set(data.answers) != set(expected):
            raise HTTPException(status_code=422, detail="Responde las tres preguntas de orientación.")

        for qid, allowed in expected.items():
            if data.answers[qid] not in allowed:
                raise HTTPException(status_code=422, detail="Una respuesta de orientación no es válida.")

        counts = {}
        for answer in data.answers.values():
            counts[answer] = counts.get(answer, 0) + 1
        recommended = sorted(counts, key=lambda area: (-counts[area], AREAS.index(area)))[0]

        with closing(connect()) as db:
            cursor = db.execute(
                "INSERT INTO diagnostic_attempts (user_id, learning_area, status, detected_level) VALUES (?, ?, 'in_progress', NULL)",
                (user["id"], recommended),
            )
            attempt_id = cursor.lastrowid
            for qid, answer in data.answers.items():
                db.execute(
                    "INSERT INTO diagnostic_answers (attempt_id, question_id, answer_value, is_correct) VALUES (?, ?, ?, NULL)",
                    (attempt_id, qid, answer),
                )
            db.commit()

        return {
            "message": "Orientación completada.",
            "attempt_id": attempt_id,
            "recommended_area": recommended,
            "next_step": "Realizar el diagnóstico de conocimientos del área recomendada.",
        }

    if data.area not in AREAS:
        raise HTTPException(status_code=422, detail="Área de aprendizaje no válida.")

    questions = QUESTION_BANK[data.area]
    expected = {q[0]: q[3] for q in questions}

    if set(data.answers) != set(expected):
        raise HTTPException(status_code=422, detail="Responde todas las preguntas del diagnóstico.")

    for qid, answer in data.answers.items():
        if answer not in {option[0] for option in next(q[2] for q in questions if q[0] == qid)}:
            raise HTTPException(status_code=422, detail="Una respuesta no es válida.")

    correct_count = sum(data.answers[qid] == correct for qid, correct in expected.items())
    score = round(correct_count / len(expected) * 100, 2)

    if score <= 33.34:
        level = "Principiante"
    elif score <= 66.67:
        level = "Básico en desarrollo"
    else:
        level = "Intermedio inicial"

    with closing(connect()) as db:
        attempt = db.execute(
            """
            SELECT id
            FROM diagnostic_attempts
            WHERE user_id = ? AND learning_area = ? AND status = 'in_progress'
            ORDER BY id DESC
            LIMIT 1
            """,
            (user["id"], data.area),
        ).fetchone()

        if attempt:
            attempt_id = attempt["id"]
            db.execute(
                """
                UPDATE diagnostic_attempts
                SET status = 'completed',
                    detected_level = ?,
                    score = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
                """,
                (level, score, attempt_id, user["id"]),
            )
        else:
            cursor = db.execute(
                """
                INSERT INTO diagnostic_attempts
                (user_id, learning_area, status, detected_level, score, completed_at)
                VALUES (?, ?, 'completed', ?, ?, CURRENT_TIMESTAMP)
                """,
                (user["id"], data.area, level, score),
            )
            attempt_id = cursor.lastrowid

        learning_updates = []

        for qid, answer in data.answers.items():
            is_correct = answer == expected[qid]

            db.execute(
                "INSERT INTO diagnostic_answers (attempt_id, question_id, answer_value, is_correct) VALUES (?, ?, ?, ?)",
                (attempt_id, qid, answer, int(is_correct)),
            )

            learning_updates.append(
                record_learning_response(
                    db=db,
                    user_id=user["id"],
                    source="diagnostic",
                    item_id=qid,
                    skill_id=SKILL_BY_QUESTION[qid],
                    learning_area=data.area,
                    correct=is_correct,
                )
            )

        db.commit()

    return {
        "message": "Diagnóstico completado.",
        "attempt_id": attempt_id,
        "area": data.area,
        "score": score,
        "detected_level": level,
        "correct_answers": correct_count,
        "total_questions": len(expected),
        "competency_updates": learning_updates,
    }


@app.get("/api/diagnostic/latest")
def latest_diagnostic(user=Depends(current_user)):
    with closing(connect()) as db:
        row = db.execute(
            """
            SELECT id, learning_area, status, detected_level, score, created_at, completed_at
            FROM diagnostic_attempts
            WHERE user_id = ? AND status = 'completed' AND learning_area != 'Orientación'
            ORDER BY id DESC
            LIMIT 1
            """,
            (user["id"],),
        ).fetchone()

    return {"diagnostic": dict(row) if row else None}


LESSON_CATALOG = {
    "fundamentos-variables": {"title": "Variables y tipos de datos", "module": "Fundamentos de programación"},
    "fundamentos-condiciones": {"title": "Condiciones if y else", "module": "Fundamentos de programación"},
    "estructuras-for": {"title": "Ciclo for", "module": "Estructuras de control"},
    "estructuras-while": {"title": "Ciclo while", "module": "Estructuras de control"},
}

@app.get("/api/progress")
def get_progress(user=Depends(current_user)):
    with closing(connect()) as db:
        completed = db.execute(
            "SELECT lesson_id, completed_at FROM lesson_completions WHERE user_id = ? ORDER BY completed_at",
            (user["id"],),
        ).fetchall()
        diagnostic = db.execute(
            "SELECT learning_area, detected_level, score FROM diagnostic_attempts WHERE user_id = ? AND status = 'completed' AND learning_area != ? ORDER BY id DESC LIMIT 1",
            (user["id"], ORIENTATION_ID),
        ).fetchone()
        mastery = db.execute(
            "SELECT skill_id, prob_mastery, observations FROM student_skill_mastery WHERE user_id = ? ORDER BY skill_id",
            (user["id"],),
        ).fetchall()
    completed_ids = [row["lesson_id"] for row in completed]
    total = len(LESSON_CATALOG)
    return {
        "completed_lessons": completed_ids,
        "completed_count": len(completed_ids),
        "total_lessons": total,
        "progress_percent": round(len(completed_ids) / total * 100) if total else 0,
        "diagnostic": dict(diagnostic) if diagnostic else None,
        "mastery": [dict(row) for row in mastery],
        "catalog": LESSON_CATALOG,
    }


class LessonCompletionData(BaseModel):
    lesson_id: str = Field(min_length=1, max_length=100)


@app.post("/api/lessons/complete")
def complete_lesson(data: LessonCompletionData, user=Depends(current_user)):
    if data.lesson_id not in LESSON_CATALOG:
        raise HTTPException(status_code=404, detail="La lección no existe.")
    with closing(connect()) as db:
        db.execute(
            "INSERT OR IGNORE INTO lesson_completions (user_id, lesson_id) VALUES (?, ?)",
            (user["id"], data.lesson_id),
        )
        count = db.execute(
            "SELECT COUNT(*) AS total FROM lesson_completions WHERE user_id = ?",
            (user["id"],),
        ).fetchone()["total"]
        db.execute(
            "INSERT INTO student_progress (user_id, completed_lessons) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET completed_lessons = excluded.completed_lessons, updated_at = CURRENT_TIMESTAMP",
            (user["id"], count),
        )
        db.commit()
    return {"message": "Progreso guardado.", "completed_lessons": count, "progress_percent": round(count / len(LESSON_CATALOG) * 100)}


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Capricornio API"}


@app.post("/api/register", status_code=201)
def register(data: RegisterData, response: FastAPIResponse):
    name = data.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Escribe tu nombre completo.")

    email = normalize_email(data.email)
    hashed_password = password_hash.hash(data.password)

    with closing(connect()) as db:
        try:
            cursor = db.execute("""
                INSERT INTO users (name, email, password_hash, learning_goal)
                VALUES (?, ?, ?, ?)
            """, (name, email, hashed_password, data.learning_goal.strip()))
            user_id = cursor.lastrowid

            db.execute(
                "INSERT INTO student_progress (user_id) VALUES (?)",
                (user_id,)
            )
            create_session(db, user_id, response)
            db.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=409,
                detail="Ya existe una cuenta con ese correo."
            )

    return {
        "message": "Cuenta creada correctamente.",
        "user": {
            "id": user_id,
            "name": name,
            "email": email,
            "learning_goal": data.learning_goal
        }
    }


@app.post("/api/login")
def login(data: LoginData, response: FastAPIResponse):
    email = normalize_email(data.email)

    with closing(connect()) as db:
        user = db.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Todavía no tienes una cuenta. Regístrate para comenzar en Capricornio."
            )

        if not password_hash.verify(data.password, user["password_hash"]):
            raise HTTPException(
                status_code=401,
                detail="La contraseña es incorrecta. Inténtalo de nuevo."
            )

        create_session(db, user["id"], response)
        db.commit()

    return {
        "message": "Sesión iniciada correctamente.",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "learning_goal": user["learning_goal"]
        }
    }


@app.get("/api/me")
def me(user=Depends(current_user)):
    return {"user": user}


@app.post("/api/logout")
def logout(
    response: FastAPIResponse,
    capricornio_session: str | None = Cookie(default=None)
):
    if capricornio_session:
        token_hash = hashlib.sha256(
            capricornio_session.encode()
        ).hexdigest()

        with closing(connect()) as db:
            db.execute(
                "DELETE FROM sessions WHERE token_hash = ?",
                (token_hash,)
            )
            db.commit()

    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax"
    )
    return {"message": "Sesión cerrada."}

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(BASE_DIR / "login.html")


@app.get("/{page}.html", include_in_schema=False)
def serve_page(page: str):
    allowed = {
        "index", "registro", "login", "diagnostico",
        "plan", "modulo", "leccion", "suscripciones"
    }
    if page not in allowed:
        raise HTTPException(status_code=404, detail="Página no encontrada.")
    return FileResponse(BASE_DIR / f"{page}.html")


app.mount("/css", StaticFiles(directory=BASE_DIR / "css"), name="css")
app.mount("/img", StaticFiles(directory=BASE_DIR / "img"), name="img")
app.mount("/js", StaticFiles(directory=BASE_DIR / "js"), name="js")
