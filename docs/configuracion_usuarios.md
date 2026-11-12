# Usuarios y autenticación

## Primera instalación — Clínica San Rafael

1. Clona el repositorio y selecciona `config/usuarios-autenticacion`:

   ```powershell
   git clone https://github.com/carloz-chavez/clinica-san-rafael-grupo5.git
   cd clinica-san-rafael-grupo5
   git switch config/usuarios-autenticacion
   ```

2. Abre Docker Desktop. El script utiliza Python dentro de Docker para preparar
   la base, así que aún no necesitas configurar el entorno virtual.
3. Desde la raíz ejecuta:

   ```powershell
   .\db\configurar_usuarios_equipo.ps1
   ```

   Si falta `.env`, lo prepara desde `.env.example`. Acepta la conexión local
   con Enter y escribe una clave JWT propia, o pulsa Enter para generar una.
   Los valores que escribas se ocultan. Si copiaste el ejemplo manualmente,
   también te pedirá reemplazar la clave de ejemplo. Una clave ya configurada
   se conserva.
   Si no copiaste la configuración privada del equipo, introduce y confirma las
   siete claves académicas acordadas cuando las solicite el asistente.
4. Espera el resumen de siete cuentas verificadas. La primera ejecución necesita
   Internet para descargar las imágenes y dependencias.
5. Con Python 3.11 instalado, prepara e inicia el backend desde la raíz:

   ```powershell
   python -m venv backend/.venv
   .\backend\.venv\Scripts\Activate.ps1
   pip install -r backend/requirements.txt
   python -m uvicorn aplicacion.principal:aplicacion --app-dir backend --host 127.0.0.1 --port 8000
   ```

6. Con Node.js instalado, abre otra terminal y ejecuta:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

7. Abre `http://localhost:5173` e inicia sesión con una cuenta de
   `db/desarrollo/cuentas_ficticias.json`. Este archivo local queda fuera de Git;
   las claves son académicas y nunca se usan en producción.

El script solo prepara PostgreSQL y las cuentas; no inicia FastAPI ni React.
Puedes comprobar el backend en `/salud`, `/salud/base-datos` y `/openapi.json`.
Cada integrante mantiene su propio `.env` y su propia clave JWT, fuera de Git.

## Si ya tienes una base local

Ejecuta el mismo comando. Conserva tu conexión, clave JWT y preferencia de modo
simulado. Si esta última está activa, te indica cómo pasar al login real.

| Estado encontrado | Qué hace |
|---|---|
| Diez tablas vacías con esquema y permisos válidos | Carga C2 y configura las siete cuentas en una transacción |
| C2 con cuatro cuentas | Pide `RESTABLECER`, respalda y completa las tres faltantes |
| Siete cuentas con las claves compartidas | Solo verifica; conserva filas y hashes |
| Siete cuentas con claves distintas o inactivas | Exige respaldo y confirmación antes de restablecer |
| Esquema incompleto, otros usuarios o datos incompatibles | Se detiene sin sobrescribir datos |

Para revisar el estado sin cargar datos ni cambiar cuentas:

```powershell
.\db\configurar_usuarios_equipo.ps1 -SoloVerificar
```

La conexión admitida es `localhost:5433/clinica_san_rafael` o su equivalente
`127.0.0.1`. Un contenedor existente se inicia si está detenido, sin recrearlo.
Docker solo ejecuta `01_esquema.sql` y `02_permisos.sql` al crear un volumen
vacío. No se reaplica el esquema sobre una base existente para intentar repararla.

Los respaldos previos a un restablecimiento quedan en `respaldos/`, con su SHA-256.
Se comprueban con `pg_restore --list` antes de cambiar las claves. Conserva esos
archivos; para ensayar una recuperación completa, usa un servidor aislado y
`pg_restore --exit-on-error`, manteniendo propietarios y permisos. `pg_dump` no
incluye los roles globales: prepara los roles requeridos con los atributos del
origen, sin copiar sus contraseñas. Los roles de auditoría se definen en
`01_esquema.sql` y sus permisos se restringen en `02_permisos.sql`.

## Cuentas compartidas

| ID usuario | Correo | Rol | ID médico |
|---|---|---|---|
| 800001 | admision.c2@sanrafael.invalid | ADMISION | — |
| 800002 | medico1.c2@sanrafael.invalid | MEDICO | 800001 |
| 800003 | medico2.c2@sanrafael.invalid | MEDICO | 800002 |
| 800004 | admin.c2@sanrafael.invalid | ADMINISTRADOR | — |
| 800005 | medico3.c2@sanrafael.invalid | MEDICO | 800003 |
| 800006 | medico4.c2@sanrafael.invalid | MEDICO | 800004 |
| 800007 | medico5.c2@sanrafael.invalid | MEDICO | 800005 |

El procedimiento reutiliza el seed y `administracion.configurar_usuarios`.
Cada instalación genera sus propios hashes Argon2id. La carga inicial y las
cuentas se confirman juntas; un fallo revierte la operación. En bases existentes
solo cambia usuarios, manteniendo los datos clínicos intactos.

No vuelvas a ejecutar el seed después de personalizar las claves: abortará ante
las diferencias. Tampoco necesitas los registros del modo simulado para estas
cuentas. Para elegir otras claves manualmente sigue disponible, desde `backend`:

```powershell
python -m administracion.configurar_usuarios --aplicar-local
```

Ese administrador pide las claves sin mostrarlas y también acepta las variables
`CLAVE_C2_ADMISION`, `CLAVE_C2_ADMIN` y `CLAVE_C2_MEDICO1` a `CLAVE_C2_MEDICO5`.
Requiere coordinar el cambio y respaldar antes: restablece las claves suministradas.
El script del equipo, en cambio, primero comprueba si ya coinciden.

## Autenticación y pruebas

Las instalaciones nuevas usan `AUTENTICACION_SIMULADA=false`. En una instalación
existente, cambia ese valor cuando decidas usar login real y reinicia el backend.
Desactiva también `VITE_AUTENTICACION_SIMULADA` en el frontend si estaba activo.
En producción declara `ENTORNO=produccion`, que impide activar la simulación.

La plantilla `cuentas_ficticias.example.json` no contiene claves. Comparte la
configuración completa solo por el canal privado del equipo. El login de la API
no lee este archivo. La carpeta está fuera
del paquete del backend y excluida de las imágenes mediante `.dockerignore`.
No copies sus credenciales a otros empaquetados de producción.

Para ejecutar Ruff y Pytest con PostgreSQL aislado:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File db/probar_usuarios.ps1
```

El ejecutor comprueba cuentas, C3, concurrencia, flujo autenticado e instalación
compartida. Los reportes quedan en `reportes_qa/`, fuera de Git. Las pruebas de
preparación reciben `EQUIPO_BASE_DATOS_QA`; nunca uses tu base de desarrollo.
La opción `-ExcluirTruncate` evita únicamente el caso que intenta esa sentencia.
Si ya tienes una imagen QA con las dependencias instaladas, puedes indicarla
con `-ImagenPython nombre:etiqueta` para evitar descargarlas de nuevo.
Consulta también los [permisos y pendientes](verificacion_autenticacion_real.md).

## Errores habituales

- **Docker no disponible:** abre Docker Desktop y espera a que termine de iniciar.
- **Destino rechazado:** revisa host, puerto 5433 y nombre `clinica_san_rafael`.
  El script no admite servidores remotos ni contextos Docker remotos.
- **Esquema o permisos incompatibles:** revisa los logs y compara el esquema con
  el repositorio. No borres el volumen ni desactives restricciones para continuar.
- **Restablecimiento cancelado:** no se cambiaron cuentas. Coordina el cambio
  antes de volver a ejecutarlo.
- **Fallo de respaldo o checksum:** no se cambian las claves. Comprueba el archivo
  y el espacio disponible; conserva cualquier respaldo anterior.
- **Fallo de carga:** la transacción se revierte. Corrige la causa y vuelve a
  ejecutar sin borrar datos.
- **Política de PowerShell:** si bloquea el archivo, usa
  `powershell -NoProfile -ExecutionPolicy Bypass -File db/configurar_usuarios_equipo.ps1`.
