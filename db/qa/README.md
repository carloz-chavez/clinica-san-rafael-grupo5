# PostgreSQL QA para SW705, Parte 4

El job `test` de `.github/workflows/ci.yml` usa un servidor `postgres:16`
exclusivo de la ejecucion. Su directorio de datos esta en `tmpfs`, sin volumen
persistente ni conexion con `docker-compose.yml` de desarrollo. El puerto del
host lo asigna Docker. El health check espera a que PostgreSQL acepte conexiones.

Las credenciales `clinica_ci` / `solo-qa-ci` son ficticias y exclusivas del
contenedor QA. No deben reutilizarse fuera de este entorno. El administrador
del contenedor es necesario para crear los roles tecnicos del esquema, probar
`SET ROLE` y crear/eliminar las bases temporales de concurrencia. Los permisos
del writer se prueban cambiando al rol real, sin privilegios de administrador.

Antes de ejecutar pruebas, se procesan en orden y con `psql -X` y
`ON_ERROR_STOP=1`:

1. `db/qa/00_precondiciones.sql`: comprueba base `clinica_c3_qa`, servidor 16,
   extension disponible `btree_gist`, privilegios administrativos y entorno vacio.
2. `db/01_esquema.sql`: crea tablas, restricciones, triggers y roles NOLOGIN.
3. `db/02_permisos.sql`: verifica atributos y membresias de los roles y ajusta
   los permisos minimos de auditoria, incluyendo sus comprobaciones de ACL.

Se usa el cliente `psql` del contenedor; no se necesita instalar otro cliente
en el runner. No se cargan seeds ni datos de personas reales. Las fixtures
insertan datos ficticios y revierten sus transacciones. Las pruebas de
concurrencia crean `clinica_c6_qa_<uuid>` y la eliminan en su finalizador.

`C3_BASE_DATOS_QA` y `AUTENTICACION_SIMULADA=false` solo se definen en el paso
de pruebas. La URL QA no sustituye la configuracion de desarrollo de la API.

## Dependencias de las 109 pruebas antes omitidas

| Modulo | Fixture | Casos parametrizados |
|---|---|---:|
| prueba_anulaciones.py | conexion_c3 | 18 |
| prueba_citas.py | conexion_c3 | 10 |
| prueba_integracion_c3.py | conexion_c3 | 14 |
| prueba_pacientes.py | conexion_c3 | 41 |
| prueba_recetas.py | conexion_c3 | 23 |
| prueba_concurrencia_anulaciones.py | destino_concurrencia | 3 |

Las 109 dependen de `C3_BASE_DATOS_QA`. La prueba de visibilidad transaccional
abre otra conexion observadora a esa misma base; las tres de concurrencia usan
sesiones independientes en su base temporal. Ningun caso recolectado solicita
la fixture heredada `conexion_bd`, que conserva su implementacion anterior.
Los otros 91 casos no necesitan un servidor PostgreSQL.

## Evidencia local, 8 de noviembre de 2026

Se conservaron los cambios previos de fixtures y de aislamiento de `.env`.
Docker Desktop no tenia daemon disponible; se uso PostgreSQL **16.15** nativo
en un cluster temporal exclusivo, escuchando solo en `127.0.0.1:55432`.
Se inicializo una nueva base `clinica_c3_qa` con los tres scripts anteriores.
Como esos binarios no incluyen `psql`, la validacion local ejecuto el SQL con
Psycopg en autocommit, omitiendo solo el metacomando `\set ON_ERROR_STOP`;
los errores SQL se propagan como excepciones y detienen la inicializacion.

Entorno: Windows, Python **3.12.14**, Ruff **0.17.4**, Pytest **9.2.0**,
pytest-cov **7.1.0**. GitHub Actions conserva Ubuntu y Python **3.11**.
Con la URL del cluster temporal en `C3_BASE_DATOS_QA` y autenticacion simulada
desactivada, se ejecutaron desde `backend/` los mismos comandos del workflow:

```sh
ruff check --select E4,E7,E9,F aplicacion pruebas
python -m pytest -q
python -m pytest --cov=aplicacion --cov-fail-under=80
```

- Ruff: `All checks passed!`.
- Pytest: **200 passed, 0 failed, 0 skipped**.
- Pytest con cobertura: **200 passed, 0 failed, 0 skipped**.
- Cobertura de lineas: **90.69 %** (977 sentencias, 91 sin ejecutar).
- Se observaron ocho advertencias: una deprecacion de TestClient, seis sobre
  longitud corta de claves JWT de prueba y una de permisos del cache local.
- No hicieron falta pruebas adicionales ni cambios de logica de negocio.
- Se valido la sintaxis YAML y se ejecuto `git diff --check`.

Los resultados locales no certifican una ejecucion verde de GitHub Actions.
Falta publicar los cambios tras su revision y comprobar el nuevo run del PR #18.
No se hizo commit, push ni merge; el commit del primer build rojo `f89e48b`
permanece intacto. No se modificaron `.env`, scripts de esquema/permisos,
el compose de desarrollo ni bases de desarrollo.

Referencia para el servicio y su puerto dinamico:
[documentacion oficial de GitHub Actions](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers).
El comportamiento de `-X` y `ON_ERROR_STOP` se describe en
[la documentacion de psql 16](https://www.postgresql.org/docs/16/app-psql.html).
