# Despliegue de Capricornio Plus

## Requisitos
- Python 3.10 o superior.
- Un sistema Linux/macOS o Windows con Python.
- Disco persistente para la base de datos.
- HTTPS cuando el servicio sea accesible por internet.

## Instalación local

    git clone https://github.com/tm9880380-code/capricornio-plus.git
    cd capricornio-plus
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn backend.main:app --reload

Abre http://127.0.0.1:8000.

En Windows PowerShell, activa el entorno con:

    .venv\Scripts\Activate.ps1

## Servidor Linux

1. Descarga el repositorio y crea un entorno virtual.
2. Instala requirements.txt.
3. Ejecuta el servicio con un usuario del sistema sin privilegios administrativos.
4. Configura un proxy inverso con HTTPS (por ejemplo, Caddy o Nginx).
5. Define CAPRICORNIO_HTTPS=1 para que la cookie de sesión use Secure.
6. Conserva data/ en un volumen persistente con permisos restrictivos.
7. Configura copias de seguridad, actualizaciones y supervisión del servicio.

Comando de ejecución básico:

    uvicorn backend.main:app --host 127.0.0.1 --port 8000

En un proveedor que defina PORT:

    uvicorn backend.main:app --host 0.0.0.0 --port $PORT

No expongas SQLite, archivos .env, copias ni el puerto interno de la aplicación directamente a internet.

## Persistencia (importante en Render)

La base está en `data/capricornio.db`. En el plan gratuito de Render el sistema de archivos es efímero: cada despliegue o reinicio puede borrar todas las cuentas y el progreso. Para conservarlos hace falta un disco persistente (plan de pago) y apuntar la base a él con la variable `CAPRICORNIO_DATA_DIR` (por ejemplo `/var/data`). En `render.yaml` hay un bloque comentado listo para activar. Sin eso, usa la instancia solo para pruebas y no prometas conservar datos de estudiantes.

Si hay un proxy delante, ejecuta uvicorn con `--proxy-headers` para que los límites de intentos usen la IP real del visitante.

## Persistencia y escalabilidad

SQLite es adecuado para desarrollo, demostración y una instancia pequeña. No compartas el mismo archivo SQLite entre varias instancias de aplicación ni lo ubiques en un sistema de archivos de red sin comprobar sus garantías de bloqueo.

Para una universidad con múltiples grupos y concurrencia, planifica migración a PostgreSQL, migraciones de esquema, roles institucionales, copias probadas y monitoreo.

## Privacidad y preparación legal\n\nAntes de habilitar registros con personas reales:\n- Completa nombre legal, domicilio y correo de contacto del responsable en `aviso-privacidad.html` y `privacidad.html`.\n- Revisa con asesoría jurídica `terminos.html`, `cookies.html`, `politica-comercial.html` y las políticas de accesibilidad, seguridad y uso responsable según el país y el público.\n- Comprueba que el aviso y los enlaces legales estén visibles desde el formulario de registro.\n- Verifica que el registro exija ambas casillas sin premarcarlas y que `privacy_consents` almacene versiones y fecha.\n- Define procedimiento de consultas, reclamos, revocación, eliminación y plazos de conservación, incluidos respaldos.\n- No uses datos reales de menores sin evaluación jurídica e institucional y salvaguardas específicas.\n\nLos documentos incluidos son plantillas técnicas de partida, no una certificación legal ni sustituyen la identificación del responsable de cada instalación.\n\n## Actualizaciones

Antes de actualizar:
- Haz copia de seguridad de data/.
- Lee cambios de esquema y dependencias.
- Ejecuta compileall y pytest.
- Prueba restauración de la copia en un entorno separado.

## Costos

El software no requiere una API de IA de pago ni alojamiento de los cursos externos. Sin embargo, un servidor público, dominio, almacenamiento, copias y soporte pueden generar costos. Ningún plan gratuito de proveedor debe considerarse permanente o ilimitado.
