# Capricornio Plus

Capricornio es una plataforma educativa de conectividad: ayuda a encontrar recursos gratuitos que ya existen en internet y ofrece un espacio para organizar el aprendizaje, practicar y consultar el avance.

No pretende alojar cursos, copiar documentación ni reemplazar a los autores de los recursos enlazados.

## Qué incluye esta versión

- Registro e inicio de sesión con contraseñas almacenadas mediante hash.
- Ocho rutas iniciales: ciberseguridad, desarrollo frontend, desarrollo backend, análisis de datos, inteligencia artificial y modelos de lenguaje, bases de datos, redes y sistemas, y programación/lenguajes.
- Opción de elegir directamente Python, JavaScript, Go, Java o C++, o pedir orientación si todavía no se sabe qué estudiar.
- Diagnóstico inicial y seguimiento experimental de respuestas.
- Panel de inicio con ruta seleccionada y avance guardado.
- Biblioteca de enlaces a documentación, tutoriales, prácticas, proyectos GitHub y canales educativos de YouTube.
- Cuatro lecciones de muestra de fundamentos de Python y ejercicios básicos.

## Importante: alcance y límites

Esta versión es un prototipo funcional y abierto a revisión, no una plataforma educativa terminada ni una certificación.

- Los bancos de diagnóstico actuales son pequeños (tres preguntas por banco heredado). Las rutas frontend y backend reutilizan preguntas generales de desarrollo web/programación; todavía no existe un banco amplio y validado de 10–27 preguntas por especialidad.
- Las estimaciones adaptativas BKT/IRT son experimentales y no están calibradas psicométricamente.
- Las cuatro lecciones prácticas incluidas son ejemplos de Python. La comprobación actual usa reglas sobre el texto enviado; todavía no es un entorno general que ejecute y depure código con análisis de errores por línea.
- La biblioteca enlaza a recursos de terceros. Su disponibilidad, idioma, licencias y condiciones pueden cambiar.
- El progreso guardado actualmente corresponde al catálogo de lecciones de muestra, no a un currículo completo de las ocho áreas.

## Instalación local

Requiere Python 3.10 o superior.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Abre `http://127.0.0.1:8000` y crea una cuenta.

Para ejecutar las pruebas:

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Datos y privacidad

La base SQLite se crea en `data/capricornio.db`. Cada instalación administra sus propios datos. No se envían respuestas a un servicio de IA externo en esta versión.

## Despliegue

Consulta [DEPLOY.md](DEPLOY.md). En un servidor, configura almacenamiento persistente para la carpeta `data/`; si el proveedor elimina el disco local al reiniciar, las cuentas y el progreso pueden perderse.

No se garantiza que un proveedor externo mantenga un plan gratuito permanente. La opción más predecible para uso autónomo es instalar Capricornio en un equipo o servidor propio.

## Licencias

Los recursos externos pertenecen a sus respectivos autores y plataformas. Los componentes adaptativos incluidos conservan los avisos de licencia que los acompañan. Revisa las licencias de cada componente antes de redistribuir o modificarlo.
