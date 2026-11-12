# Configuracion de cuentas y autenticacion

## Uso local

Copiar `.env.example` a `.env`, configurar una clave JWT propia y mantener
`AUTENTICACION_SIMULADA=false` para usar el login real. No versionar `.env`.
El backend consulta PostgreSQL en `localhost:5433/clinica_san_rafael`.
Desde la raiz, con Python y las dependencias del backend instaladas:

```powershell
python -m uvicorn aplicacion.principal:aplicacion --app-dir backend --host 127.0.0.1 --port 8000
```

`GET /salud` comprueba la API; `GET /salud/base-datos` devuelve
`{"base_datos":"ok"}` al conectar. El contrato esta en `/openapi.json`.
`POST /auth/login` recibe correo y contrasena y devuelve un JWT Bearer.
No registrar contrasenas ni tokens. La configuracion se carga al iniciar el proceso.

## Configurar las siete cuentas academicas C2

La herramienta es exclusiva del entorno local C2. No carga datos clinicos ni
crea medicos. Requiere los cinco medicos existentes y las cuatro cuentas originales:

| ID usuario | Correo | Rol | ID medico |
|---|---|---|---|
| 800001 | admision.c2@sanrafael.invalid | ADMISION | — |
| 800002 | medico1.c2@sanrafael.invalid | MEDICO | 800001 |
| 800003 | medico2.c2@sanrafael.invalid | MEDICO | 800002 |
| 800004 | admin.c2@sanrafael.invalid | ADMINISTRADOR | — |
| 800005 | medico3.c2@sanrafael.invalid | MEDICO | 800003 |
| 800006 | medico4.c2@sanrafael.invalid | MEDICO | 800004 |
| 800007 | medico5.c2@sanrafael.invalid | MEDICO | 800005 |

Antes de aplicar, obtener autorizacion del responsable, comprobar el destino y
crear un respaldo completo con `pg_dump -Fc`. Conservarlo fuera de Git, registrar
su SHA-256 y verificarlo con `pg_restore --list`. Ensayar su restauracion en un
servidor aislado vacio con `pg_restore --exit-on-error`, manteniendo propietarios
y ACL. `pg_dump` no incluye roles globales: preparar antes los roles requeridos
con atributos y membresias cotejados contra el origen, sin copiar contrasenas.
Los roles tecnicos `clinica_auditoria_writer` y `clinica_auditoria_reader` se
crean originalmente en `db/01_esquema.sql`; sus permisos se restringen en
`db/02_permisos.sql`. No omitir ACL ni desactivar triggers para restaurar.
Comparar tablas, conteos, restricciones, relaciones y permisos efectivos.
No restaurar sobre desarrollo como ensayo ni eliminar volumenes.

Desde `backend`, con `ENTORNO=local`:

```powershell
python -m administracion.configurar_usuarios --aplicar-local
```

Introducir las siete claves mediante los prompts ocultos y confirmarlas. No hay
contrasenas predeterminadas en Git. Para automatizacion privada pueden inyectarse
`CLAVE_C2_ADMISION`, `CLAVE_C2_ADMIN` y `CLAVE_C2_MEDICO1` a `CLAVE_C2_MEDICO5`
como variables de entorno; la herramienta no las lee automaticamente de `.env`.

Se conservan las cuatro identidades originales y se crean solo las tres cuentas
faltantes. Cada clave recibe un hash Argon2id independiente. La transaccion
bloquea escrituras concurrentes, verifica claves y comprueba que las otras nueve
tablas permanezcan iguales antes de confirmar. Una discrepancia revierte la
operacion. Repetir no duplica cuentas, pero restablece las claves suministradas
y renueva los hashes. La herramienta rechaza destinos ajenos al escenario C2.
No usarla como provisionamiento de produccion.

El seed C2 no sobrescribe credenciales: aborta ante diferencias. No volver a
cargarlo despues de personalizar las claves. Tampoco ejecutar el script de modo
simulado sobre estas cuentas: agregaria otros registros ficticios.

## Simulacion y permisos

La simulacion esta disponible para pruebas explicitas, pero requiere
`AUTENTICACION_SIMULADA=true`. Sin Bearer usa usuario 1 y, para MEDICO, medico 1.
Con `ENTORNO=produccion` la configuracion rechaza el modo simulado. Declarar el
entorno de despliegue explicitamente. El frontend debe desactivar su panel
`VITE_AUTENTICACION_SIMULADA` cuando se use autenticacion real.

El JWT exige expiracion e identidad coherente; las rutas controlan roles y las
operaciones de recetas/anulacion exigen al medico responsable. Administrador
no tiene acceso general a historias clinicas. Los JWT ya emitidos no se revocan
al desactivar una cuenta: siguen vigentes hasta expirar.

Consultar [validacion y pendientes](verificacion_autenticacion_real.md) antes
de ampliar permisos o preparar un despliegue.

## Pruebas reproducibles

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File db/probar_usuarios.ps1
```

Requiere Docker. Crea PostgreSQL 16 y Python temporales, sin puertos publicados
ni volumen de desarrollo. Instala las dependencias declaradas y Ruff en QA.
Ejecuta las suites de cuentas, C3, concurrencia y flujo autenticado con bases
separadas y datos ficticios; los contenedores propios se retiran al terminar.
Los reportes se guardan en `reportes_qa/`, excluido de Git. Nunca apunta a la
base local para las pruebas con escrituras. Sin Docker, Pytest puede ejecutarse
desde backend; las suites PostgreSQL requieren sus destinos QA explicitos.
