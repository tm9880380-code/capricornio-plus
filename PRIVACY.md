# Privacidad y datos de estudiantes

Capricornio Plus es software autoalojable. Cada instalación administra su propia base SQLite; no existe una cuenta central de Capricornio ni telemetría central obligatoria en esta versión.

## Datos que almacena

- Nombre, correo y hash de contraseña.
- Objetivo de aprendizaje seleccionado.
- Hash de token de sesión y fecha de expiración.
- Respuestas de diagnósticos y ejercicios, estimaciones de competencias y lecciones completadas.

Las contraseñas no se almacenan en texto plano. Los tokens de sesión se guardan como hash. El código Python de los ejercicios se ejecuta en un Web Worker del navegador y no se envía al servidor de Capricornio.

## Responsabilidades de quien instala

La institución o persona que despliega el servicio actúa como responsable de los datos que recoge. Debe definir una política de privacidad, base jurídica, retención, atención de solicitudes, seguridad, copias y eliminación.

Para uso con menores se requiere revisión jurídica y de protección de datos aplicable al país, autorización institucional y familiar cuando corresponda, minimización estricta de datos y salvaguardas específicas. Esta versión no debe ponerse en producción escolar con datos reales de menores sin esa evaluación.

## Retención y eliminación

La base SQLite está en `data/capricornio.db`. Quien administra la instalación debe establecer periodos de retención, respaldos y procedimientos seguros para eliminar cuentas y sus datos. La interfaz todavía no ofrece autoservicio completo de eliminación de cuenta.

## Servicios externos

La biblioteca enlaza a sitios de terceros. Al abrirlos, se aplican sus propias políticas y condiciones. El motor Python se descarga desde jsDelivr al utilizar por primera vez la práctica de Python; revisa la política del proveedor y fija/actualiza versiones de manera controlada en despliegues institucionales.

## No incluir

No solicites ni almacenes contraseñas de otras plataformas, documentos de identidad, datos sensibles ni información que no sea necesaria para enseñar y dar seguimiento al progreso.
