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

## Primera instalación — Clínica San Rafael

Con Git, Docker Desktop, Python 3.11 y Node.js instalados:

```powershell
git clone https://github.com/carloz-chavez/clinica-san-rafael-grupo5.git
cd clinica-san-rafael-grupo5
git switch config/usuarios-autenticacion
.\db\configurar_usuarios_equipo.ps1
```

Abre Docker Desktop antes de ejecutar el script. Si falta `.env`, lo prepara
desde `.env.example` y pide la conexión y una clave JWT; puedes dejar la conexión
por defecto y generar una clave aleatoria. Conserva las claves ya configuradas.
En un volumen nuevo, Docker inicializa esquema y permisos; el script carga C2
y configura las siete cuentas académicas. Pide sus claves por entrada oculta o
lee la configuración compartida por el equipo en un canal privado. El archivo
local `db/desarrollo/cuentas_ficticias.json` queda fuera de Git.

Si ya tienes una base local, ejecuta el mismo comando: si las cuentas coinciden,
no cambia nada. Para restablecer claves distintas, pide confirmación y crea un
respaldo. Puedes revisar el estado con `-SoloVerificar`, sin aplicar cambios.

El script no inicia la aplicación. Continúa con los comandos de backend y
frontend de la siguiente sección e inicia sesión en `http://localhost:5173`.
Consulta [configuración y errores habituales](docs/configuracion_usuarios.md).

## Cómo ejecutar

**Backend** (desde la carpeta `backend`):

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate        Linux/Mac:  source .venv/bin/activate
pip install -r requirements.txt
uvicorn aplicacion.principal:aplicacion --reload
```

Comprobar en `http://localhost:8000/salud` y la documentación en `http://localhost:8000/docs`.

El archivo `.env`, preparado en el paso anterior, se lee al arrancar. Comprueba la conexión en `http://localhost:8000/salud/base-datos`.

**Base de datos:** Docker ejecuta `db/01_esquema.sql` y `db/02_permisos.sql` solo al inicializar un volumen vacío. El seed C2 se carga por separado mediante el script del equipo.

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

El script del equipo reutiliza `db/02_seed.sql` para cargar cuatro especialidades,
cinco médicos, ocho pacientes, 25 horarios, diez citas y seis consultas, recetas
e indicaciones, con ocho eventos de auditoría. Después completa las siete cuentas.
Las fechas de demostración son fijas: historia el 05/10/2026 y agenda el 07/01/2030.

Docker no carga este seed automáticamente. No lo ejecutes de nuevo sobre una
base con claves personalizadas: detectará diferencias y abortará. Usa
`db/configurar_usuarios_equipo.ps1` para detectar el estado y preparar las cuentas.
Los identificadores 800001–800099 están reservados para C2.

El repositorio incluye una plantilla de cuentas sin claves en `db/desarrollo/`.
No agregues contraseñas, hashes de usuarios ni archivos `.env`.
Las pruebas completas del backend se ejecutan en bases aisladas con
`powershell -NoProfile -ExecutionPolicy Bypass -File db/probar_usuarios.ps1`.
