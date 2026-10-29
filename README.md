# Clínica San Rafael S.A.C. — Grupo 5
Proyecto académico SW705: Historia Clínica Electrónica (M1) y Agenda y Citas Médicas (M2), coherente con el Entregable 1.
## Estado
Repositorio inicial. Ninguna historia de usuario está implementada. FastAPI, React y PostgreSQL están pendientes de integrar; no hay todavía una aplicación ejecutable.
## Arquitectura acordada
Monolito en capas con API REST: presentación en React, negocio en Python/FastAPI y datos en PostgreSQL. Cada módulo separa rutas, servicios y repositorios. M2 valida pacientes mediante la interfaz pública de M1; no importa sus repositorios ni consulta directamente sus tablas. Se prevé una sola unidad de despliegue de aplicación.
## Estructura prevista (pendiente de incorporar)
```text
backend/app/
  main.py
  m1_hce/{routes,services,repositories}/
  m2_agenda/{routes,services,repositories}/
frontend/src/
database/
tests/{unit,integration}/
docs/
```
## Equipo y Sprint Backlog 1
| Integrante | Rol | Historias |
|---|---|---|
| Albornoz Azurza Gonzalo Alessandro | Product Owner | HU06, HU07, HU08 |
| Chavez Oliva Carlos Daniel | Scrum Master | HU01, HU04, HU10 |
| Vargas Ponce Luis Angel | Developer | HU02, HU03, HU09 |
| HU | Descripción | Puntos | Estado |
|---|---|---|---|
| HU01 | Registrar y actualizar paciente evitando duplicados por DNI | 5 | Por hacer |
| HU02 | Registrar consulta clínica | 5 | Por hacer |
| HU03 | Consultar historia clínica unificada en orden cronológico | 8 | Por hacer |
| HU04 | Registrar indicaciones y recetas de una consulta | 5 | Por hacer |
| HU06 | Consultar disponibilidad por especialidad, médico y fecha | 5 | Por hacer |
| HU07 | Registrar cita con paciente, médico, fecha, hora y motivo | 5 | Por hacer |
| HU08 | Impedir dos citas del mismo médico en el mismo horario | 3 | Por hacer |
| HU09 | Iniciar sesión con correo, contraseña y acceso por rol | 5 | Por hacer |
| HU10 | Anular consulta con motivo conservando el original | 3 | Por hacer |
Total Sprint 1: **44 puntos**. HU05 (recordatorios) y HU11 (confirmar/cancelar citas) pertenecen al Sprint 2. M3–M5 se prevén para Sprint 2; M6 es deseable. La numeración ilustrativa de la guía Semana 9 no reemplaza la del entregable: reservar cita es HU07, no HU03.
## Ejecución
Pendiente de implementar y verificar. Cuando exista el backend, se documentarán sus dependencias y el arranque desde backend con `uvicorn app.main:app --reload`. El frontend React y la conexión PostgreSQL tendrán instrucciones propias verificadas; ese comando todavía no funciona en esta base.
## Convenciones de trabajo
Ramas: `feature/HU01-registrar-paciente`, `fix/HU08-horario-duplicado`, `docs/guia-de-estilo`. Commits pequeños: `feat: registra paciente (HU01)`, `fix: rechaza DNI duplicado (HU01)`, `test: cubre DNI duplicado (HU01)`, `docs: explica registro de paciente (HU01)`.
Todo cambio se propone mediante pull request y requiere al menos una aprobación de otro integrante. Nadie aprueba su propio PR. La guía de estilo, herramientas, primera HU y práctica de conflicto todavía deben elaborarse y verificarse.
## Definición de Hecho
- Criterios de aceptación satisfechos y revisión de pares.
- Pruebas unitarias e integración aprobadas; rechazo 403 a roles no autorizados cuando corresponda.
- Auditoría de operaciones clínicas y anulación con motivo, fecha y usuario, sin eliminación física.
- Solo datos ficticios o anonimizados, sin secretos en el repositorio.
Metas pendientes de validar: apertura de HCE en menos de 2 segundos con 8 000 pacientes y prevención transaccional de citas duplicadas mediante índice único parcial en PostgreSQL.
## Referencias
Entregable1Caso_Clinica_SW705.docx, secciones 5, 8 y 9; Guia_Practica_Semana9_SW705.docx.
