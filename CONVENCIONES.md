# Convenciones del equipo

Reglas para que los tres escribamos el código de la misma manera. Si algo no está aquí y genera dudas, se decide en la reunión diaria y se agrega a este archivo.

## 1. Nombres en español

Todo lo que dependa de nosotros se nombra en español: carpetas, archivos, funciones, variables, clases, constantes, campos JSON, ramas y mensajes de commit.

**Reglas**

- Python: `snake_case` para funciones, variables y archivos (`obtener_paciente`, `fecha_nacimiento`); `PascalCase` para clases (`UsuarioActual`); `MAYUSCULAS` para constantes (`ROL_MEDICO`).
- JavaScript/React: `camelCase` para funciones y variables (`obtenerCitas`); `PascalCase` para componentes y sus archivos (`AgendaCitas.jsx`).
- Sin tildes ni `ñ` en identificadores ni nombres de archivo (`contrasena`, `diseno`, `anio`). En textos para el usuario sí se usan.
- Los campos JSON de la API usan los mismos nombres que las columnas de la base de datos (`id_paciente`, `fecha_nacimiento`).
- Las rutas HTTP se mantienen como están documentadas en el E4 y el SAD (`/pacientes`, `/citas`, `/consultas`, `/auth/login`) para no romper la trazabilidad.

**Excepciones (nombres que no controlamos)**

- Archivos exigidos por herramientas: `README.md`, `requirements.txt`, `pytest.ini`, `docker-compose.yml`, `package.json`, `__init__.py`, `.gitignore`.
- API de librerías y del lenguaje: `Depends`, `APIRouter`, `BaseModel`, `useState`, `async`, métodos HTTP (`GET`, `POST`).
- Términos técnicos sin traducción natural: `token`, `JWT`, `hash`, `API`.

**Glosario para usar el mismo término**

| Inglés | Español |
|---|---|
| router | enrutador |
| service | servicio |
| repository | repositorio |
| schema (modelo de datos de la API) | esquema |
| dependency | dependencia |
| connection | conexion |
| session | sesion |
| request / response | solicitud / respuesta |
| audit log | bitacora |
| role | rol |
| seed (datos de prueba) | datos_prueba |
| layout | diseno |
| pages | paginas |
| components | componentes |
| test | prueba |

Las pruebas siguen esta convención: archivos `prueba_*.py` y funciones `probar_*` (configurado en `backend/pytest.ini`).

## 2. Estructura por módulo

Cada carpeta de historia tiene las mismas capas (ADR 4 y ADR 5):

| Archivo | Capa | Responsabilidad |
|---|---|---|
| `enrutador.py` | Presentación | Rutas HTTP, validación de entrada, roles permitidos |
| `servicio.py` | Negocio | Reglas de negocio, bitácora, transacciones |
| `repositorio.py` | Datos | Consultas SQL; no contiene reglas de negocio |
| `esquemas.py` | Contrato | Modelos de entrada y salida de la API |

Regla de dependencia: el enrutador llama al servicio y el servicio al repositorio, nunca al revés. **Un módulo no importa el repositorio de otro.** M2 solo usa `aplicacion.m1_hce.publico`.

## 3. Errores de la API

Todo error devuelve `{"detalle": "mensaje", "codigo": "CODIGO"}`. Se lanza con `ErrorNegocio` (`aplicacion/nucleo/errores.py`).

| Estado | Cuándo | Ejemplo de código |
|---|---|---|
| 401 | Sin sesión o credenciales inválidas | `CREDENCIALES_INVALIDAS` |
| 403 | Rol no autorizado | `ROL_NO_AUTORIZADO` |
| 404 | No existe el recurso | `PACIENTE_NO_ENCONTRADO` |
| 409 | Conflicto | `HORARIO_OCUPADO`, `DNI_DUPLICADO` |
| 422 | Datos inválidos | `DATOS_INVALIDOS` |

## 4. Ramas, commits y pull requests

**Ramas**

- `main` está protegida: no se sube directo. Solo se integra por pull request con al menos una aprobación.
- Una rama por historia o tarea: `prefijo/descripcion-en-minusculas-con-guiones`.
- Prefijos: `historia/`, `arreglo/`, `config/`, `docs/`. Ejemplo: `historia/hu07-registrar-cita`.

**Commits:** `tipo(ambito): descripcion`

| Tipo | Cuándo se usa |
|---|---|
| `historia` | Implementa o completa una historia de usuario |
| `arreglo` | Corrige un error |
| `config` | Estructura, dependencias, Docker, integración continua |
| `docs` | Documentación |
| `prueba` | Agrega o cambia pruebas |
| `refactor` | Reordena código sin cambiar el comportamiento |

- Ámbito opcional: `nucleo`, `autenticacion`, `pacientes`, `consultas`, `recetas`, `disponibilidad`, `citas`, `db`, `backend`, `frontend`.
- Descripción en español, presente imperativo, minúscula inicial, sin punto final y con un asunto de 72 caracteres como máximo.
- Si el commit corresponde a una historia, se agrega al pie la línea `Historia: HU07`.
- El cuerpo es opcional, va separado por una línea en blanco y explica el porqué.
- Ejemplo: `historia(citas): registra cita y rechaza horario ocupado`

**Pull requests**

- El título sigue el mismo formato que un commit.
- El cuerpo usa la plantilla `.github/pull_request_template.md`.
- Pequeñas y frecuentes: una rama no debe vivir más de unos pocos días.
- Se integran con *Squash and merge*, usando el título de la pull request como mensaje.

**Base de datos:** `db/01_esquema.sql` solo lo modifica Carlos. Si alguien necesita un campo nuevo, se lo pide.

## 5. Revisión de pull requests

- Otro integrante revisa cada pull request antes del merge: **nadie aprueba su propio cambio**.
- Se revisa si cumple la historia y sus criterios de aceptación, si respeta el estándar de este documento, si tiene pruebas y si no introduce riesgos de seguridad.
- Los comentarios apuntan al código, no a la persona; se proponen alternativas y se agradece la corrección.
- La rama principal se protege: exige pull request y al menos una aprobación antes de aceptar cambios.

## 6. Definición de Hecho

Una historia está terminada cuando:

1. Cumple todos los criterios de aceptación (Dado/Cuando/Entonces) y fue revisada por al menos otro integrante.
2. Sus pruebas unitarias y de integración pasan, incluidas las de roles (403 a roles no autorizados) cuando aplique.
3. Toda operación sobre información clínica queda en la bitácora de auditoría y ninguna entrada clínica se elimina físicamente (RNF02 y RNF04).
4. Las pruebas y demostraciones usan solo datos ficticios o anonimizados, nunca datos reales de pacientes.
