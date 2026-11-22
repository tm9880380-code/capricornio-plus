# Seguridad: modelo y lista de verificación

## Controles implementados en el prototipo

- Contraseñas con hash diseñado para contraseñas mediante pwdlib/Argon2.
- Token de sesión aleatorio; en SQLite se conserva su SHA-256, no el token original.
- Cookie HttpOnly y SameSite=Lax. La opción Secure se activa con `CAPRICORNIO_HTTPS=1`.
- Caducidad de sesión en el servidor.
- Consultas SQL parametrizadas.
- Protección de claves foráneas en SQLite.
- Comprobación de origen en solicitudes mutables cuando el navegador envía Origin.
- Cabeceras X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, Content-Security-Policy (el Worker de Python tiene una política propia) y, con `CAPRICORNIO_HTTPS=1`, Strict-Transport-Security. Las respuestas de `/api/` no se almacenan en caché. Si la CSP bloquea algo en un navegador, `CAPRICORNIO_DISABLE_CSP=1` la desactiva mientras se ajusta.
- Límite de intentos: 5 fallos de login por correo y 30 por IP cada 15 minutos, y 10 registros por IP por hora. Tras un login exitoso se borran los fallos de ese correo. En un proveedor con proxy, ejecuta uvicorn con `--proxy-headers` para que la IP sea la real.
- El login verifica siempre una contraseña (también si el correo no existe) para no filtrar por tiempo qué correos tienen cuenta.
- La corrección ocurre en el servidor: las respuestas correctas, la retroalimentación y la salida esperada de los ejercicios no salen en `/api/curriculum` ni `/api/lessons`. Una lección solo se marca completada si el servidor registró una respuesta correcta a su actividad.
- Los ejercicios de Python se califican en el servidor comparando la salida que reporta el navegador. Es una mitigación, no una garantía: un estudiante determinado puede fabricar esa salida. Para valor probatorio hace falta ejecutar el código en un entorno aislado del servidor con pruebas ocultas.
- Eliminación de cuenta (`POST /api/account/delete`, pide la contraseña) con borrado en cascada de todos sus datos.
- Limpieza de sesiones vencidas e intentos antiguos; SQLite en modo WAL con espera de bloqueo.
- Código Python educativo ejecutado en Web Worker del navegador, nunca mediante `exec` en el servidor. Se bloquea el acceso de red del worker y se limita el tiempo de ejecución y la salida capturada.

**Límite importante:** un Web Worker y Pyodide no constituyen una caja de arena de seguridad para ejecutar código hostil. La plataforma está pensada para ejercicios educativos de estudiantes de confianza. No ejecutes código de terceros ni la presentes como entorno aislado multiusuario. Para un servicio público con código no confiable se necesita aislamiento real en servidor (contenedores/VM efímeros, límites de CPU/memoria, red denegada, sistema de archivos temporal y revisión de seguridad).

## Antes de desplegar públicamente

- Configurar HTTPS y `CAPRICORNIO_HTTPS=1`.
- Restringir acceso al servidor, sistema operativo, copias y archivo SQLite.
- Definir copias cifradas y probar restauración.
- Añadir un flujo seguro de recuperación de contraseña y cierre global de sesiones (requiere envío de correo verificado; el registro sigue respondiendo que el correo ya existe, lo que permite saber qué correos tienen cuenta hasta que se verifique el correo).
- Verificar la CSP en navegadores reales, sobre todo el ejercicio de Python, y revisar CSRF, XSS, cookies, dependencias y configuración del proxy.
- Ejecutar análisis SAST, escaneo de dependencias, pruebas de penetración y revisión independiente.
- Definir registros sin contraseñas, tokens ni datos personales innecesarios.
- Revisar la ejecución de Pyodide, límites de recursos y versiones CDN; el Web Worker no sustituye una auditoría de seguridad del navegador ni una sandbox de código no confiable.
- Para una institución, definir responsables, gestión de incidentes, retención, accesos administrativos y plan de continuidad.

## Uso con menores

No desplegar para estudiantes menores de edad sin evaluación de impacto, revisión jurídica y de privacidad, aprobación institucional, controles de protección y protocolos de atención de incidentes. Esta versión no incluye aún controles de administración escolar.
