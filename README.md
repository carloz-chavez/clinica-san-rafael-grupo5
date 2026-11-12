# Sistema de Gestión Clínica San Rafael

Aplicación web de historia clínica electrónica (M1) y agenda de citas (M2) para la Clínica San Rafael S.A.C.
Proyecto del curso SW705 – Taller de Ingeniería de Software I (UNI). Sprint 1: 44 puntos, historias HU01 a HU04, HU06 a HU10.

**Stack:** Python 3.11+ con FastAPI · React con Vite · PostgreSQL 16.
**Arquitectura:** monolito en capas con dos módulos (M1 y M2). Detalle en el documento integral (sección 5).

## Estructura

```
clinica-san-rafael/
├─ db/                         Esquema y datos de prueba (Carlos)
├─ backend/
│  ├─ aplicacion/
│  │  ├─ principal.py          Punto de entrada de la API
│  │  ├─ nucleo/               Piezas compartidas: constantes, errores, dependencias, auditoría
│  │  ├─ m1_hce/               Historia Clínica Electrónica
│  │  │  ├─ autenticacion/     HU09
│  │  │  ├─ pacientes/         HU01
│  │  │  ├─ consultas/         HU02, HU03
│  │  │  ├─ recetas/           HU04, HU10
│  │  │  └─ publico.py         Interfaz de M1 que otros módulos pueden usar
│  │  └─ m2_agenda/            Agenda y Citas
│  │     ├─ disponibilidad/    HU06
│  │     └─ citas/             HU07, HU08
│  └─ pruebas/
└─ frontend/                   React + Vite (Gonzalo)
```

## Responsables

| Área | Responsable |
|---|---|
| `db/`, `nucleo/auditoria.py`, `m1_hce/publico.py`, `m1_hce/pacientes/`, `m1_hce/recetas/` | Carlos |
| `nucleo/` (excepto auditoría), `principal.py`, `m1_hce/autenticacion/`, `m1_hce/consultas/`, `pruebas/conftest.py` | Angel |
| `m2_agenda/`, base del `frontend/` (rutas, diseño, cliente de API, componentes) | Gonzalo |

Pantallas del frontend: `InicioSesion` (Gonzalo), `GestionPacientes` (Carlos), `AgendaCitas` (Gonzalo), `HistoriaClinica` (Angel, con componentes de receta y anulación de Carlos).

## Cómo ejecutar

**Backend** (desde la carpeta `backend`):

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate        Linux/Mac:  source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env               # en Windows: copy ..\.env.example ..\.env
uvicorn aplicacion.principal:aplicacion --reload
```

Comprobar en `http://localhost:8000/salud` y la documentación en `http://localhost:8000/docs`.

El archivo `.env` se lee automáticamente al arrancar. Para comprobar la conexión con la base de datos abre `http://localhost:8000/salud/base-datos`: responde 503 hasta que la base de datos esté levantada.

**Base de datos:** `docker compose up` crea las tablas desde `db/01_esquema.sql` y los permisos de `db/02_permisos.sql`.

**Frontend** (desde la carpeta `frontend`):

```bash
npm install
npm run dev
```

Abre `http://localhost:5173`. Vite redirige las rutas de la API al backend del
puerto 8000. Detalle de sesión, roles y modo simulado en
[frontend/README.md](frontend/README.md).

**Pruebas:** `pytest` desde `backend` y `npm run prueba` desde `frontend`.

## Autenticación

Para preparar las siete cuentas C2 con claves independientes, ver
[procedimiento y diagnostico](docs/configuracion_usuarios.md).
Su aplicacion a la base local requiere autorizacion y respaldo previos.

El login real de HU09 está disponible en `POST /auth/login`; devuelve un JWT que
el frontend envía como `Bearer`. Con `AUTENTICACION_SIMULADA=true` en `.env`,
las rutas protegidas sin token usan un usuario ficticio para desarrollo. Cambia
`ROL_SIMULADO` (`ADMISION`, `MEDICO` o `ADMINISTRADOR`) para probar permisos y 403.
No uses la autenticación simulada en demostraciones.

### Datos del modo simulado

Para que el modo simulado pueda operar el flujo completo del médico, la
base necesita unos registros ficticios (especialidad, médico, usuario de
bitácora y un paciente de prueba). Con Docker levantado, desde la raíz:

```powershell
docker compose cp db/03_modo_simulado.sql postgres:/tmp/03_modo_simulado.sql
docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U clinica -d clinica_san_rafael -f /tmp/03_modo_simulado.sql
```

Y para que el panel aparezca en la pantalla de login, crea
`frontend/.env.local` con `VITE_AUTENTICACION_SIMULADA=true` antes de
`npm run dev` (ese archivo no se sube al repositorio). Al entrar con el
panel "Entrar en modo simulado" como Médico podrás registrar atenciones,
recetas y anulaciones sin login real. Todos los datos son ficticios y
exclusivos de desarrollo.

## Cómo trabajamos

Lee [CONVENCIONES.md](CONVENCIONES.md): nombres en español, capas, formato de errores, ramas, commits, revisión de pull requests y Definición de Hecho.

Todas las pruebas y demostraciones usan datos ficticios.

## Datos ficticios de desarrollo (C2)

`db/02_seed.sql` se ejecuta manualmente sobre C1 inicializado; Docker no lo
carga automáticamente. Incluye 4 especialidades, 5 médicos, 4 usuarios,
8 pacientes, 25 horarios, 10 citas, 6 consultas (una anulada), 6 recetas,
6 indicaciones y 8 eventos de auditoría. Las fechas son fijas: historia el
05/10/2026 y agenda el 07/01/2030. Todo es ficticio y exclusivo de desarrollo.

Cuentas: `admision.c2@sanrafael.invalid` (ADMISION),
`medico1.c2@sanrafael.invalid` y `medico2.c2@sanrafael.invalid` (MEDICO),
`admin.c2@sanrafael.invalid` (ADMINISTRADOR).

No hay contraseña predeterminada. Con Python y las dependencias del backend
instaladas, elegir una clave **solo para estas cuatro cuentas demostrativas**
mediante entrada oculta y generar su hash Argon2id. Desde la raíz, PowerShell:

```powershell
$hashC2 = python -c "from argon2 import PasswordHasher; from getpass import getpass; print(PasswordHasher().hash(getpass('Clave exclusiva C2: ')))"
if ($LASTEXITCODE -ne 0) { throw 'No se pudo generar el hash' }
docker compose cp db/02_seed.sql postgres:/tmp/02_seed.sql
docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -v "seed_hash=$hashC2" -U clinica -d clinica_san_rafael -f /tmp/02_seed.sql
```

El comando de carga modifica desarrollo: ejecutarlo solo cuando el equipo
autorice esa carga. Repetir con el **mismo `$hashC2`**, sin volver a generarlo:
un hash nuevo cambia la sal y se considera un conflicto. El seed no cambia
contraseñas ni sobrescribe filas; ante cualquier diferencia revierte la carga.
Reservar IDs 800001–800099 para C2. No guardar claves ni hashes en el repositorio.

QA completo (requiere Docker; descarga Python 3.11 y `argon2-cffi==23.1.0`
en un contenedor temporal):
`powershell -NoProfile -ExecutionPolicy Bypass -File db/ejecutar_pruebas.ps1`.
No carga desarrollo. Los hashes se verifican con la dependencia Argon2
declarada; el login de HU09 ya valida estas cuentas por HTTP.
