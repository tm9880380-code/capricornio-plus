# Publicación de Capricornio Plus

## Despliegue en un servidor Python
1. Sube el contenido completo del repositorio.
2. Instala dependencias: `pip install -r requirements.txt`.
3. Configura el comando de inicio: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` (si el proveedor define `PORT`).
4. Usa un volumen persistente para la carpeta `data/`; allí vive la base SQLite.
5. En HTTPS configura `CAPRICORNIO_HTTPS=1` para que la cookie de sesión use Secure.

## Prueba local
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
uvicorn backend.main:app --reload
```

La raíz `/` sirve `login.html`. El servidor debe ejecutar FastAPI; abrir los HTML como archivos estáticos no conecta la autenticación ni la base de datos.
