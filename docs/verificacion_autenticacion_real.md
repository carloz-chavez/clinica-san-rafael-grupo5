# Validación de autenticación

La autenticación real se comprobó con las siete cuentas C2 y PostgreSQL local.
Las pruebas que crean o modifican registros se ejecutaron en bases aisladas.
El equipo también probó el frontend con una cuenta de Admisión.

## Ejecutar las pruebas

Desde la raíz del proyecto:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File db/probar_usuarios.ps1
```

El comando prepara tres bases QA: `clinica_usuarios_qa`, `clinica_c3_qa` y
`clinica_flujo_qa`. Sus conexiones se pasan mediante `USUARIOS_BASE_DATOS_QA`,
`C3_BASE_DATOS_QA` y `FLUJO_BASE_DATOS_QA`. Usa claves aleatorias para las cuentas
de prueba y guarda los resultados en `reportes_qa/`.

Las pruebas cubren el login, la firma y expiración del JWT, los permisos por rol
y el rechazo de credenciales incorrectas o cuentas inactivas. También comprueban
la configuración de usuarios, el recorrido de paciente a consulta, la persistencia,
el rollback y la auditoría, incluidas operaciones concurrentes.

## Permisos actuales

| Operación | ADMISION | MEDICO | ADMINISTRADOR |
|---|---|---|---|
| Registrar o actualizar paciente | Sí | No | Sí |
| Leer paciente | Sí | Con vínculo asistencial | Sí |
| Consultar o reservar citas | Sí | No | Sí |
| Registrar consulta | No | Con su identidad JWT | No |
| Leer consulta o historia | No | Por rol; ver pendientes | No |
| Recetar, indicar o anular | No | Solo el responsable | No |

El backend rechaza una consulta asociada a la cita de otro médico. Enviar un
`id_medico` distinto no cambia la identidad tomada del JWT. Tampoco permite
recetar ni anular una consulta de otro profesional.

## Resultados del 12/11/2026

Las siete cuentas iniciaron sesión y sus tokens contenían la identidad, el rol
y la relación médica esperados. `/salud`, `/salud/base-datos` y `/openapi.json`
respondieron correctamente. Uvicorn se detuvo al terminar y las diez tablas
locales conservaron sus datos, restricciones, permisos y secuencias.

Pytest aprobó **218 pruebas sin omisiones**. Ruff pasó en los archivos de esta
tarea con las reglas E/F/I, excepto E501. En el backend completo quedaron 52
hallazgos anteriores: 15 I001, 7 F401 y 30 F811. También se detectó una advertencia
de deprecación de Starlette/httpx. Ejecuta las pruebas nuevamente después de
cada cambio; estas cifras corresponden a esa validación.

## Preparación compartida del equipo

El inicializador del equipo reutiliza el seed C2 y el administrador de cuentas.
Se probó en PostgreSQL 16 aislado, con los mismos scripts de inicio que monta
Compose: diez tablas, roles y permisos técnicos. La carga desde vacío dejó siete
cuentas con claves académicas válidas; repetirla conservó todos los hashes.
También se comprobaron cuatro cuentas existentes, confirmación y respaldo
obligatorios, conservación clínica y rollback completo ante un fallo final.

La ejecución QA para este cambio aprobó 227 pruebas y excluyó un caso que envía
TRUNCATE, porque esta tarea prohíbe usar esa sentencia. No se cuenta como aprobado.
Las bases auxiliares de concurrencia se conservan hasta retirar el servidor QA;
la suite ya no ejecuta DROP DATABASE. Ruff pasó en los archivos modificados.

La descarga inicial de dependencias se bloqueó. Se repitió la validación con una
imagen QA que contiene únicamente dependencias ya instaladas, sin código ni
credenciales del proyecto:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File db/probar_usuarios.ps1 -ExcluirTruncate -ImagenPython clinica-python-qa:equipo
```

La sintaxis y la validación de destinos del script PowerShell se comprobaron
por separado. No se ejecutó el asistente completo sobre la base de Carlos:
esa base y su `.env` se verificaron solo mediante lecturas de conservación.
La comparación final confirmó que filas, hashes, relaciones, restricciones,
permisos y secuencias locales no cambiaron. También se comprobó con un build
aislado que Docker rechaza copiar la configuración ficticia excluida del contexto.
Las claves compartidas se conservan en un archivo local ignorado; Git contiene
solo la plantilla vacía. El asistente puede solicitar las siete claves por
entrada oculta si el integrante aún no tiene la configuración privada.

## Pendientes

- La agenda no admite el rol MEDICO. Hay que acordar su acceso antes de cambiar permisos.
- La lectura de historias y consultas no exige vínculo asistencial, aunque la
  lectura de pacientes sí. La prueba documenta esta diferencia; falta resolverla.
- Las reservas y la lectura individual de consultas no generan auditoría.
- Antes de producción, configura una clave JWT robusta y define cómo revocar
  sesiones. Desactivar una cuenta impide nuevos logins, pero no invalida los
  tokens ya emitidos hasta su vencimiento.
- Queda por resolver el lint anterior, fijar versiones de dependencias y ampliar
  las pruebas de interfaz a los tres roles.

Las credenciales académicas son solo para desarrollo. Consulta la
[guía de configuración](configuracion_usuarios.md) para preparar las cuentas.
