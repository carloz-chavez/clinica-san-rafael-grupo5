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

**Base de datos:** pendiente de Carlos (tarea C1): `docker compose up` creará las tablas desde `db/01_esquema.sql`.

**Frontend:** pendiente de Gonzalo (tarea G1).

**Pruebas** (desde `backend`): `pytest`

## Autenticación simulada (mientras no exista el login real)

Con `AUTENTICACION_SIMULADA=true` en `.env`, las rutas protegidas usan un usuario ficticio. Cambia `ROL_SIMULADO` (`ADMISION`, `MEDICO` o `ADMINISTRADOR`) para probar los permisos y los 403. Angel reemplaza esto con el login real en la HU09.

## Cómo trabajamos

Lee [CONVENCIONES.md](CONVENCIONES.md): nombres en español, capas, formato de errores, ramas, commits, revisión de pull requests y Definición de Hecho.

Todas las pruebas y demostraciones usan datos ficticios.
