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
- Código Python educativo ejecutado en Web Worker del navegador, nunca mediante `exec` en el servidor. Se bloquea el acceso de red del worker y se limita el tiempo de ejecución y la salida capturada.

**Límite importante:** un Web Worker y Pyodide no constituyen una caja de arena de seguridad para ejecutar código hostil. La plataforma está pensada para ejercicios educativos de estudiantes de confianza. No ejecutes código de terceros ni la presentes como entorno aislado multiusuario. Para un servicio público con código no confiable se necesita aislamiento real en servidor (contenedores/VM efímeros, límites de CPU/memoria, red denegada, sistema de archivos temporal y revisión de seguridad).

## Antes de desplegar públicamente

- Configurar HTTPS y `CAPRICORNIO_HTTPS=1`.
- Restringir acceso al servidor, sistema operativo, copias y archivo SQLite.
- Definir copias cifradas y probar restauración.
- Añadir límites de intentos de inicio de sesión y protección contra abuso.
- Añadir flujo seguro de recuperación de cuenta, cierre global de sesiones y eliminación de cuenta.
- Revisar CSRF, XSS, CSP, cookies, dependencias y configuración del proxy.
- Ejecutar análisis SAST, escaneo de dependencias, pruebas de penetración y revisión independiente.
- Definir registros sin contraseñas, tokens ni datos personales innecesarios.
- Revisar la ejecución de Pyodide, límites de recursos y versiones CDN; el Web Worker no sustituye una auditoría de seguridad del navegador ni una sandbox de código no confiable.
- Para una institución, definir responsables, gestión de incidentes, retención, accesos administrativos y plan de continuidad.

## Uso con menores

No desplegar para estudiantes menores de edad sin evaluación de impacto, revisión jurídica y de privacidad, aprobación institucional, controles de protección y protocolos de atención de incidentes. Esta versión no incluye aún controles de administración escolar.
