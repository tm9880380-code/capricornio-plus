# Capricornio Plus

**Capricornio es una plataforma educativa de conectividad y práctica.** Ayuda a descubrir rutas de aprendizaje, encontrar recursos gratuitos que ya existen en internet, practicar conceptos y conservar el progreso. No pretende reemplazar docentes ni alojar o copiar cursos de terceros.

## Principios
- Acceso abierto y autoalojable.
- Prioridad a recursos gratuitos y fuentes originales.
- Una ruta adecuada al objetivo y nivel inicial de cada estudiante.
- Aprender, practicar, recibir retroalimentación y volver a intentarlo.
- Privacidad, accesibilidad y costos operativos transparentes.
- Mantener la identidad visual y la paleta del proyecto.

## Ocho áreas
1. Ciberseguridad.
2. Desarrollo frontend.
3. Desarrollo backend.
4. Análisis de datos.
5. Inteligencia artificial y modelos de lenguaje.
6. Bases de datos.
7. Redes y sistemas.
8. Programación y lenguajes.

El estudiante puede elegir una de estas áreas, seleccionar un lenguaje (Python, JavaScript, Go, Java o C++) o solicitar orientación. Las rutas de lenguajes conducen al itinerario general de programación en esta versión.

## Qué incluye el prototipo actual
- Registro, inicio de sesión y sesiones con cookies HttpOnly.
- Orientación inicial para quien no sabe qué área elegir.
- Diagnóstico específico por ruta: seis preguntas por área y siete en programación.
- Niveles internos provisionales A1–C2, sin valor de certificación.
- Currículo declarativo con ocho áreas, dos módulos por área y aproximadamente 50 lecciones de muestra.
- Explicaciones, ejemplos, preguntas de comprensión y retroalimentación.
- Cuatro ejercicios iniciales de Python que se ejecutan en un Web Worker del navegador mediante Pyodide. El código no se envía al backend.
- Seguimiento de lecciones y estimaciones experimentales de competencias.
- Biblioteca filtrable de documentación, cursos, repositorios GitHub y canales educativos de YouTube.
- Pruebas automatizadas de API y comprobación sintáctica de JavaScript.

## Alcance y límites conocidos
Esta versión es un prototipo funcional para revisión y pruebas, no una plataforma certificada ni lista para desplegar a gran escala en colegios.
- Los diagnósticos son breves y sus niveles son orientativos. No han sido validados psicométricamente ni equivalen a certificaciones.
- El motor BKT/IRT es experimental y requiere calibración con datos de aprendizaje y revisión pedagógica.
- Los cuatro ejercicios ejecutables son de Python. Las demás lecciones utilizan preguntas de comprensión; todavía no hay sandbox de ejecución para JavaScript, Go, Java o C++.
- La evaluación de Python compara la salida esperada y muestra errores del intérprete; no es un depurador profesional ni un corrector general de código.
- La gestión de progreso se realiza por cuenta y ruta; faltan funciones institucionales como panel docente, cohortes, roles, SSO, exportación académica y multi-tenancy.
- El catálogo de recursos se mantiene manualmente. Los enlaces y condiciones de terceros pueden cambiar.
- La plataforma no incorpora todavía un proceso completo de recuperación/eliminación de cuenta, limitación de intentos de acceso ni auditoría de seguridad independiente.
- Para uso con menores se requiere revisión jurídica, de privacidad, seguridad y protección institucional antes de cualquier piloto real.

## Instalación local
Requiere Python 3.10 o superior.

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn backend.main:app --reload

Abre http://127.0.0.1:8000. La página pública de bienvenida es la raíz; desde allí puedes crear una cuenta.

Para pruebas:

    pip install -r requirements-dev.txt
    python -m compileall -q backend
    pytest -q

## Datos y despliegue
SQLite se crea en data/capricornio.db. Conserva la carpeta data/ en un volumen persistente. Consulta DEPLOY.md, PRIVACY.md y docs/SECURITY.md.

No se garantiza que un proveedor externo mantenga un plan gratuito permanente. Para una instalación sin pagos de hosting, se puede ejecutar en un equipo o servidor propio; el equipo debe permanecer disponible y administrado.

## Documentación para revisión
- Arquitectura: docs/ARCHITECTURE.md
- Seguridad: docs/SECURITY.md
- Accesibilidad: docs/ACCESSIBILITY.md
- Privacidad: PRIVACY.md
- Plan de piloto institucional: docs/INSTITUTIONAL-PILOT.md
- Cómo contribuir: CONTRIBUTING.md
- Código de conducta: CODE_OF_CONDUCT.md

## Licencia
El código propio de Capricornio Plus se distribuye bajo MIT. Los componentes adaptativos y materiales de terceros conservan sus licencias y avisos. Los recursos enlazados pertenecen a sus autores y plataformas; consulta sus condiciones antes de reutilizarlos.
