# Capricornio Plus — instalación local

## Requisitos
- Python 3.11 o superior.
- pip.

## Instalar
Desde la carpeta raíz del repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Abre http://127.0.0.1:8000/ . La raíz muestra el inicio de sesión.

La base SQLite se crea automáticamente en `data/capricornio.db` al iniciar la aplicación. No borres esa carpeta si necesitas conservar cuentas y progreso.

## API
- `GET /api/health`: estado del servicio.
- `POST /api/register`: crea cuenta y sesión.
- `POST /api/login`: inicia sesión.
- `POST /api/logout`: cierra sesión.
- `GET /api/me`: usuario autenticado.
- `GET /api/diagnostic/questions`: preguntas del diagnóstico.
- `POST /api/diagnostic/submit`: guarda diagnóstico y actualiza BKT/IRT.
- `GET /api/diagnostic/latest`: último diagnóstico.
- `GET /api/progress`: progreso persistido del estudiante.
- `POST /api/lessons/complete`: marca una lección como completada.

## Notas
Las estimaciones BKT/IRT actuales son experimentales; el banco es pequeño y sus parámetros no están calibrados psicométricamente. No deben presentarse como certificación de competencias.
