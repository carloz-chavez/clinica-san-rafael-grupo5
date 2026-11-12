# Validacion de autenticacion e integracion

## Alcance y ejecucion

La autenticacion real se verifico con siete identidades C2 y PostgreSQL local.
Las pruebas con escrituras se ejecutan exclusivamente en bases QA aisladas.
El frontend fue probado manualmente por el equipo con una cuenta de Admision;
esto no sustituye una prueba automatizada de interfaz.

Ejecutar desde la raiz:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File db/probar_usuarios.ps1
```

El ejecutor prepara `clinica_usuarios_qa`, `clinica_c3_qa` y `clinica_flujo_qa`.
Las variables USUARIOS_BASE_DATOS_QA, C3_BASE_DATOS_QA y FLUJO_BASE_DATOS_QA solo
apuntan a ese servidor temporal. Las claves QA son aleatorias y no corresponden
a cuentas locales. Los reportes generados quedan fuera del repositorio.

## Cobertura permanente

- Siete logins y validacion de firma, identidad, rol, medico y expiracion JWT.
- Rechazo de clave incorrecta, cuenta inactiva, token invalido, vencido o ausente.
- Conservacion de identidades, unicidad e idempotencia del administrador de cuentas.
- Rollback ante errores y conservacion de tablas ajenas a usuarios.
- Login real con pool ASGI y PostgreSQL, sin sustituir autenticacion por mocks.
- Registro de paciente, reserva de cita, consulta, recetas, indicaciones y anulacion.
- Lectura de commits desde conexiones independientes y eventos de auditoria.
- Restricciones FK, inmutabilidad de auditoria y carreras de anulacion/recetas.

## Permisos implementados

| Operacion | ADMISION | MEDICO | ADMINISTRADOR |
|---|---|---|---|
| Registrar/actualizar paciente | Si | No | Si |
| Leer paciente | Si | Con vinculo asistencial | Si |
| Consultar/reservar citas | Si | No | Si |
| Registrar consulta | No | Identidad tomada del JWT | No |
| Leer consulta/historia | No | Por rol; ver pendientes | No |
| Recetas/indicaciones/anulacion | No | Solo responsable | No |

La cita de otro medico se rechaza al registrar una consulta. Enviar un campo
id_medico extra no suplanta al profesional: el servicio usa la identidad JWT.
El medico ajeno no puede recetar ni anular la consulta de otro.

## Validacion registrada el 12/11/2026

Las siete cuentas locales iniciaron sesion y sus JWT se comprobaron sin
registrar secretos. Salud, salud/base-datos y OpenAPI respondieron correctamente.
Uvicorn temporal se detuvo tras las pruebas. Las diez tablas locales, sus
restricciones, permisos y secuencias conservaron su estado; ninguna prueba
clinica con escrituras se dirigio a desarrollo.

La suite QA completa aprobo 218 pruebas sin omisiones. Ruff E/F/I, excepto E501,
paso en los archivos de esta tarea. El analisis completo del backend detecto
52 hallazgos heredados, presentes tambien en HEAD: 15 I001, 7 F401 y 30 F811.
Existe una advertencia de deprecacion Starlette/httpx. Los resultados historicos
no sustituyen ejecutar las pruebas sobre cambios posteriores.

## Pendientes antes de produccion

1. Las rutas de agenda no admiten MEDICO: acordar su contrato antes de ampliar acceso.
2. Historia y consulta individual admiten MEDICO sin exigir vinculo asistencial,
   a diferencia de pacientes. La prueba caracteriza esta inconsistencia actual;
   no demuestra aislamiento clinico completo. Requiere decision de negocio.
3. La lectura individual de consultas y las reservas no registran auditoria;
   la historia y las operaciones clinicas de escritura si la registran.
4. Configurar una clave JWT robusta antes de desplegar y decidir politica de
   revocacion. Las claves academicas nunca son credenciales de produccion.
5. Resolver lint heredado y fijar versiones de dependencias para mayor reproducibilidad.
6. Ampliar las pruebas de interfaz a los tres roles.

No se ampliaron permisos ni se cambiaron reglas de negocio para obtener pruebas
aprobadas. Ver [configuracion y mantenimiento](configuracion_usuarios.md).
