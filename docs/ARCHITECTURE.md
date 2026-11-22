# Arquitectura de Capricornio Plus

## Propósito

Capricornio es una plataforma de conectividad educativa. Orienta al estudiante, organiza una ruta, enlaza recursos externos y ofrece práctica con seguimiento. No replica ni aloja cursos de terceros.

## Componentes actuales

- **Frontend:** HTML, CSS y JavaScript sin framework obligatorio. Mantiene la identidad visual existente.
- **API:** FastAPI y Pydantic.
- **Persistencia:** SQLite local en `data/capricornio.db`.
- **Autenticación:** hash de contraseñas con pwdlib/Argon2 y sesiones opacas cuyo token se almacena como hash.
- **Currículo:** `curriculum.json`, catálogo declarativo de ocho áreas, módulos, lecciones, comprobaciones y enlaces externos.
- **Aprendizaje adaptativo:** módulos BKT/IRT heredados. Las estimaciones actuales son experimentales y no tienen calibración psicométrica.
- **Práctica Python:** Pyodide en un Web Worker del navegador. No ejecuta el código del estudiante en el servidor de la API.

## Flujo

1. Registro y selección de área/lenguaje, o solicitud de orientación.
2. Cuestionario de intereses si no conoce su ruta.
3. Diagnóstico de conocimientos específico de la ruta.
4. Panel con progreso y acceso a la siguiente lección.
5. Lección con explicación, ejemplo, recurso externo y evaluación.
6. Registro de resultado y competencias; el progreso se guarda en la cuenta.

## Catálogo de rutas

Las ocho rutas se definen en `curriculum.json`: ciberseguridad, frontend, backend, análisis de datos, inteligencia artificial/modelos de lenguaje, bases de datos, redes/sistemas y programación/lenguajes.

Cada área contiene dos módulos de muestra y tres o cuatro lecciones por módulo. Las rutas de lenguaje específicas reutilizan la ruta de programación y deben ampliarse antes de considerarse currículos completos.

## Despliegue

FastAPI sirve páginas y API desde un mismo origen. SQLite requiere un volumen persistente. Para varias instancias o concurrencia institucional, se recomienda migrar a PostgreSQL y diseñar una estrategia de copias, migraciones y observabilidad.

## Límites

- Los diagnósticos actuales son breves (seis preguntas por área, siete en programación), no pruebas psicométricas validadas.
- Los niveles A1–C2 son etiquetas internas provisionales, no equivalentes a una certificación académica o de idiomas.
- Las lecciones de teoría usan preguntas de selección múltiple; cuatro prácticas iniciales de Python se ejecutan en el navegador. No existe todavía un sandbox general para ejecutar cualquier lenguaje.
- No hay panel docente, gestión institucional multi-tenant, importación de estudiantes, SSO ni analítica institucional.
- El catálogo de recursos se mantiene manualmente; todavía no tiene verificación automática de enlaces ni control editorial colaborativo.
