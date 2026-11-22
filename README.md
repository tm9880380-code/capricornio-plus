# Capricornio Plus

Plataforma educativa adaptativa en español. Incluye registro e inicio de sesión, diagnóstico inicial, rutas por área, lecciones con evaluación, registro de progreso y actualización experimental de dominio mediante Bayesian Knowledge Tracing (BKT).

## Requisitos
- Python 3.10 o superior.
- pip.
- No requiere API de pago ni servicios externos.

## Instalación local (Linux, macOS o Windows)
```bash
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Abre http://127.0.0.1:8000. La página de entrada es el inicio de sesión; desde allí puedes crear una cuenta. La base SQLite se crea automáticamente en `data/capricornio.db`.

## Funcionalidades
- Registro e inicio de sesión con contraseñas hasheadas y cookie de sesión HTTP-only.
- Diagnóstico de orientación y conocimientos por área.
- Catálogo de 27 lecciones iniciales distribuidas en nueve áreas.
- Evaluaciones breves por lección.
- Progreso guardado por usuario y consultado desde el plan.
- Actualización BKT experimental a partir de respuestas del diagnóstico y las lecciones.

## Áreas incluidas
Ciberseguridad, desarrollo de software y programación, desarrollo web, análisis de datos, bases de datos, inteligencia artificial, redes y sistemas, fundamentos de programación y programación orientada a objetos.

## Alcance y honestidad académica
Este es un prototipo educativo. El banco de preguntas y los parámetros BKT/IRT no están calibrados ni validados psicométricamente. El progreso mostrado refleja actividades registradas en la plataforma; no equivale a una certificación profesional ni demuestra por sí solo dominio real. El motor adaptativo de selección CAT/IRT está incluido como biblioteca, pero la selección de contenidos del flujo de lecciones aún se organiza por rutas curriculares.

## Seguridad y despliegue
Para producción se requiere HTTPS, configuración segura de cookies, gestión de secretos, protección CSRF apropiada al esquema de autenticación, limitación de intentos, copias de seguridad, migraciones y pruebas automatizadas. No expongas el servidor de desarrollo directamente a Internet.

## Licencias y atribución
El motor adaptativo incluido conserva su licencia MIT en `backend/adaptive/LICENSE-adaptive-engine`. El módulo BKT adaptado de OATutor conserva la atribución y licencia MIT en `backend/adaptive/LICENSE-OATutor`. El currículo inicial de `backend/curriculum.py` fue redactado para este proyecto.
