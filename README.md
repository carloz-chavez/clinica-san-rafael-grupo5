# Clínica San Rafael S.A.C.

Grupo 5 · SW705

## Alcance

El proyecto contempla dos módulos: Historia Clínica Electrónica (M1) y Agenda y Citas Médicas (M2). Esta etapa prepara la estructura del repositorio; todavía no implementa historias de usuario ni integra servicios.

## Arquitectura

La aplicación seguirá un monolito en capas con React, FastAPI/Python y PostgreSQL. Cada módulo separará rutas, servicios y repositorios. M2 validará pacientes a través de la interfaz de M1; no accederá directamente a sus repositorios.

## Estructura inicial

```text
backend/app/
  m1_hce/
    routes/
    services/
    repositories/
  m2_agenda/
    routes/
    services/
    repositories/
frontend/src/
database/
tests/
  unit/
  integration/
docs/
```

## Equipo

| Integrante | Rol | GitHub | Historias asignadas |
|---|---|---|---|
| Chavez Oliva Carlos Daniel | Scrum Master | — | HU01, HU04, HU10 |
| Vargas Ponce Luis Angel | Developer | [AngelVarP](https://github.com/AngelVarP) | HU02, HU03, HU09 |
| Albornoz Azurza Gonzalo Alessandro | Product Owner | [gonzalouni](https://github.com/gonzalouni) | HU06, HU07, HU08 |

## Sprint 1

| Historia | Descripción | Puntos |
|---|---|---:|
| HU01 | Registrar y actualizar pacientes evitando duplicados por DNI | 5 |
| HU02 | Registrar una consulta clínica | 5 |
| HU03 | Consultar la historia clínica unificada en orden cronológico | 8 |
| HU04 | Registrar indicaciones y recetas de una consulta | 5 |
| HU06 | Consultar disponibilidad por especialidad, médico y fecha | 5 |
| HU07 | Registrar una cita con paciente, médico, fecha, hora y motivo | 5 |
| HU08 | Impedir dos citas del mismo médico en el mismo horario | 3 |
| HU09 | Iniciar sesión con correo, contraseña y acceso por rol | 5 |
| HU10 | Anular una consulta con motivo y conservar el registro original | 3 |
| **Total** |  | **44** |

## Sprint 2

- HU05: recordatorios.
- HU11: confirmar o cancelar citas.

La numeración del entregable es la referencia: reservar una cita corresponde a HU07.

## Estado y ejecución

El repositorio aún no contiene una aplicación ejecutable. Las instrucciones para instalar dependencias y arrancar frontend, backend y base de datos se añadirán cuando esa configuración esté implementada y verificada.

## Trabajo en equipo

Los cambios se proponen mediante pull request y requieren al menos una aprobación de otro integrante. Nadie aprueba su propio PR. Usamos ramas por tarea y commits pequeños que describan el cambio, por ejemplo `feature/HU01-registrar-paciente` o `docs: organiza el README`.

## Definición de Hecho

- Criterios de aceptación satisfechos y revisión de pares.
- Pruebas unitarias y de integración aprobadas; autorización verificada cuando corresponda.
- Operaciones clínicas auditables; las anulaciones conservan motivo, fecha y usuario, sin eliminación física.
- Uso exclusivo de datos ficticios o anonimizados y ausencia de secretos en el repositorio.

Metas por validar: apertura de la HCE en menos de 2 segundos con 8 000 pacientes y prevención transaccional de citas duplicadas mediante un índice único parcial en PostgreSQL.
