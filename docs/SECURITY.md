# Seguridad: modelo y lista de verificación

## Controles implementados en el prototipo

- Contraseñas con hash diseñado para contraseñas mediante pwdlib/Argon2.
- Token de sesión aleatorio; en SQLite se conserva su SHA-256, no el token original.
- Cookie HttpOnly y SameSite=Lax. La opción Secure se activa con `CAPRICORNIO_HTTPS=1`.
- Caducidad de sesión en el servidor.
- Consultas SQL parametrizadas.
- Protección de claves foráneas en SQLite.
- Comprobación de origen en solicitudes mutables cuando el navegador envía Origin.
- Cabeceras X-Content-Type-Options, X-Frame-Options, Referrer-Policy y Permissions-Policy.
- Código Python educativo ejecutado en Web Worker del navegador, nunca mediante `exec` en el servidor.

## Antes de desplegar públicamente

- Configurar HTTPS y `CAPRICORNIO_HTTPS=1`.
- Restringir acceso al servidor, sistema operativo, copias y archivo SQLite.
- Definir copias cifradas y probar restauración.
- Añadir límites de intentos de inicio de sesión y protección contra abuso.
- Añadir flujo seguro de recuperación de cuenta, cierre global de sesiones y eliminación de cuenta.
- Revisar CSRF, XSS, CSP, cookies, dependencias y configuración del proxy.
- Ejecutar análisis SAST, escaneo de dependencias, pruebas de penetración y revisión independiente.
- Definir registros sin contraseñas, tokens ni datos personales innecesarios.
- Revisar la ejecución de Pyodide, límites de recursos y versiones CDN; el Web Worker no sustituye una auditoría de seguridad del navegador.
- Para una institución, definir responsables, gestión de incidentes, retención, accesos administrativos y plan de continuidad.

## Uso con menores

No desplegar para estudiantes menores de edad sin evaluación de impacto, revisión jurídica y de privacidad, aprobación institucional, controles de protección y protocolos de atención de incidentes. Esta versión no incluye aún controles de administración escolar.
