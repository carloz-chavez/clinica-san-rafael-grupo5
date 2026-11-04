-- C2: datos EXCLUSIVAMENTE ficticios. Carga manual; nunca montar en initdb.
-- psql -X -v ON_ERROR_STOP=1 -v seed_hash='<hash Argon2id>' -f db/02_seed.sql
-- Generar el hash con argon2.PasswordHasher (dependencia declarada del backend).
-- Reutilizar EL MISMO hash al repetir. No es un mecanismo de cambio de claves.
-- HU09 aun no implementa login: se comprueba formato/biblioteca, no acceso HTTP.
-- IDs 800001..800099 reservados para C2; no se alteran las secuencias.
-- Fechas fijas: historia el lunes 2026-10-05; agenda el lunes 2030-01-07.
-- Esta ultima es futura hasta esa fecha, no se desplaza al volver a cargar.
\set ON_ERROR_STOP on
\if :{?seed_hash}
\else
    DO $$ BEGIN RAISE EXCEPTION 'C2 requiere -v seed_hash con un hash Argon2id generado localmente'; END $$;
\endif
BEGIN;
SET LOCAL search_path = pg_catalog, public;
SET LOCAL TIME ZONE 'America/Lima';
SET LOCAL lock_timeout = '5s';
-- Evita carreras entre la comparacion y el INSERT, incluyendo otros seeds.
-- Ejecutar en desarrollo sin escrituras concurrentes; no usar en produccion.
LOCK TABLE public.bitacora_auditoria, public.citas, public.consultas_medicas,
 public.especialidades, public.horarios_medicos, public.indicaciones_medicas,
 public.medicos, public.pacientes, public.recetas, public.usuarios
 IN SHARE ROW EXCLUSIVE MODE;
CREATE TEMP TABLE seed_config(hash text) ON COMMIT DROP;
INSERT INTO seed_config VALUES (:'seed_hash');
DO $$ BEGIN
 IF (SELECT hash !~ '^\$argon2id\$v=19\$m=[0-9]+,t=[0-9]+,p=[0-9]+\$[A-Za-z0-9+/]+\$[A-Za-z0-9+/]+$' FROM seed_config) THEN
  RAISE EXCEPTION 'C2: seed_hash no tiene formato Argon2id PHC';
 END IF;
END $$;

-- Tablas temporales con exactamente las columnas y defaults del contrato C1.
CREATE TEMP TABLE seed_especialidades (LIKE public.especialidades INCLUDING DEFAULTS) ON COMMIT DROP;
CREATE TEMP TABLE seed_medicos (LIKE public.medicos INCLUDING DEFAULTS) ON COMMIT DROP;
CREATE TEMP TABLE seed_usuarios (LIKE public.usuarios INCLUDING DEFAULTS) ON COMMIT DROP;
CREATE TEMP TABLE seed_pacientes (LIKE public.pacientes INCLUDING DEFAULTS) ON COMMIT DROP;
CREATE TEMP TABLE seed_horarios_medicos (LIKE public.horarios_medicos INCLUDING DEFAULTS) ON COMMIT DROP;
CREATE TEMP TABLE seed_citas (LIKE public.citas INCLUDING DEFAULTS) ON COMMIT DROP;
CREATE TEMP TABLE seed_consultas_medicas (LIKE public.consultas_medicas INCLUDING DEFAULTS) ON COMMIT DROP;
CREATE TEMP TABLE seed_recetas (LIKE public.recetas INCLUDING DEFAULTS) ON COMMIT DROP;
CREATE TEMP TABLE seed_indicaciones_medicas (LIKE public.indicaciones_medicas INCLUDING DEFAULTS) ON COMMIT DROP;
CREATE TEMP TABLE seed_bitacora_auditoria (LIKE public.bitacora_auditoria INCLUDING DEFAULTS) ON COMMIT DROP;

INSERT INTO seed_especialidades VALUES
 (800001,'Medicina general C2','Catalogo de demostracion C2'),
 (800002,'Pediatria C2','Catalogo de demostracion C2'),
 (800003,'Cardiologia C2','Catalogo de demostracion C2'),
 (800004,'Dermatologia C2','Catalogo de demostracion C2');
INSERT INTO seed_medicos VALUES
 (800001,'Alba Ficticia','Ejemplo Uno','FICTICIO-C2-001',800001,true),
 (800002,'Bruno Ficticio','Ejemplo Dos','FICTICIO-C2-002',800002,true),
 (800003,'Clara Ficticia','Ejemplo Tres','FICTICIO-C2-003',800003,true),
 (800004,'Dario Ficticio','Ejemplo Cuatro','FICTICIO-C2-004',800004,true),
 (800005,'Elena Ficticia','Ejemplo Cinco','FICTICIO-C2-005',800001,true);
INSERT INTO seed_usuarios
SELECT 800000+n,correo,c.hash,rol,medico,true FROM seed_config c CROSS JOIN
 (VALUES (1,'admision.c2@sanrafael.invalid','ADMISION',NULL::integer),
         (2,'medico1.c2@sanrafael.invalid','MEDICO',800001),
         (3,'medico2.c2@sanrafael.invalid','MEDICO',800002),
         (4,'admin.c2@sanrafael.invalid','ADMINISTRADOR',NULL::integer))
 AS u(n,correo,rol,medico);
INSERT INTO seed_pacientes
 (id_paciente,dni,nombres,apellidos,fecha_nacimiento,sexo,telefono,correo,direccion,fecha_registro,activo)
SELECT 800000+n, lpad((2000+n)::text,8,'0'),'Paciente Ficticio '||n,
 'Ejemplo C2',DATE '1988-01-01'+(n*365),CASE WHEN n%2=0 THEN 'F' ELSE 'M' END,
 'FICTICIO-C2-'||n,'paciente'||n||'.c2@example.invalid',
 'Direccion ficticia C2 '||n,TIMESTAMP '2026-10-01 08:00',true
FROM generate_series(1,8) n;
-- Lunes a viernes, 08:00..12:00: 25 horarios, cinco por medico.
INSERT INTO seed_horarios_medicos
SELECT 800000+(m-1)*5+d,800000+m,d,TIME '08:00',TIME '12:00',true
FROM generate_series(1,5) m CROSS JOIN generate_series(1,5) d;
INSERT INTO seed_citas
 (id_cita,id_paciente,id_medico,fecha,hora,estado,motivo,fecha_registro)
SELECT 800000+n,800000+n,800000+((n-1)%5+1),DATE '2026-10-05',
 TIME '08:00'+(n-1)*INTERVAL '30 minutes','atendida',
 'Atencion ficticia C2',TIMESTAMP '2026-10-01 08:00'
FROM generate_series(1,6) n;
INSERT INTO seed_citas VALUES
 (800007,800007,800001,'2030-01-07','09:00','registrada','Agenda ficticia C2','2026-10-01 08:00'),
 (800008,800008,800002,'2030-01-07','09:30','confirmada','Agenda ficticia C2','2026-10-01 08:00'),
 (800009,800001,800003,'2030-01-07','10:00','cancelada','Cancelacion ficticia C2','2026-10-01 08:00'),
 (800010,800002,800003,'2030-01-07','10:00','registrada','Turno liberado C2','2026-10-01 08:00');
INSERT INTO seed_consultas_medicas
SELECT 800000+n,800000+n,800000+((n-1)%5+1),800000+n,
 TIMESTAMP '2026-10-05 08:00'+(n-1)*INTERVAL '30 minutes',
 NULL,'Caso ficticio C2, sin diagnostico real',n=6,
 CASE WHEN n=6 THEN 'Anulacion ficticia C2' END,
 CASE WHEN n=6 THEN TIMESTAMP '2026-10-06 09:00' END,
 CASE WHEN n=6 THEN 800004 END
FROM generate_series(1,6) n;
INSERT INTO seed_recetas
SELECT 800000+n,800000+n,'Producto ficticio C2 (no administrar)',
 'Dosis ilustrativa, sin uso clinico','Frecuencia de demostracion',
 'Duracion de demostracion','Solo pruebas de software',TIMESTAMP '2026-10-05 11:30'
FROM generate_series(1,6) n;
INSERT INTO seed_indicaciones_medicas
SELECT 800000+n,800000+n,'Indicacion ficticia C2: solo demostracion de software',
 TIMESTAMP '2026-10-05 11:30' FROM generate_series(1,6) n;
-- Entidades y acciones del contrato de constantes.py; no copiar texto clinico.
INSERT INTO seed_bitacora_auditoria VALUES
 (800001,800002,800001,'CREACION','CONSULTA_MEDICA',800001,'2026-10-05 08:30','C2: evento ficticio'),
 (800002,800003,800002,'CREACION','CONSULTA_MEDICA',800002,'2026-10-05 09:00','C2: evento ficticio'),
 (800003,800002,800006,'CREACION','CONSULTA_MEDICA',800006,'2026-10-05 11:00','C2: evento ficticio'),
 (800004,800002,800001,'MODIFICACION','CONSULTA_MEDICA',800001,'2026-10-05 11:30','C2: evento ficticio'),
 (800005,800004,800006,'ANULACION','CONSULTA_MEDICA',800006,'2026-10-06 09:00','C2: evento ficticio'),
 (800006,800002,800001,'CONSULTA','HISTORIA',NULL,'2026-10-06 09:30','C2: evento ficticio'),
 (800007,800002,800001,'CREACION','RECETA_INDICACION',800001,'2026-10-05 11:30','C2: evento ficticio'),
 (800008,800003,800002,'CONSULTA','HISTORIA',NULL,'2026-10-06 10:00','C2: evento ficticio');

DO $$
DECLARE tabla text; clave text; diferente boolean; restriccion text;
BEGIN
 FOR tabla,clave IN SELECT * FROM (VALUES
  ('especialidades','id_especialidad'),('medicos','id_medico'),
  ('usuarios','id_usuario'),('pacientes','id_paciente'),
  ('horarios_medicos','id_horario'),('citas','id_cita'),
  ('consultas_medicas','id_consulta'),('recetas','id_receta'),
  ('indicaciones_medicas','id_indicacion'),('bitacora_auditoria','id_auditoria')
 ) AS orden(tabla,clave) LOOP
  EXECUTE format('SELECT EXISTS (SELECT FROM public.%I t JOIN pg_temp.%I s USING (%I)
                  WHERE to_jsonb(t) IS DISTINCT FROM to_jsonb(s))',tabla,'seed_'||tabla,clave)
   INTO diferente;
  IF diferente THEN
   RAISE EXCEPTION 'Conflicto C2 en %: ID reservado con contenido diferente; no se sobrescribio',tabla;
  END IF;
  BEGIN
   EXECUTE format('INSERT INTO public.%I OVERRIDING SYSTEM VALUE
                  SELECT s.* FROM pg_temp.%I s WHERE NOT EXISTS
                  (SELECT FROM public.%I t WHERE t.%I=s.%I)',tabla,'seed_'||tabla,tabla,clave,clave);
  EXCEPTION WHEN unique_violation OR exclusion_violation THEN
   GET STACKED DIAGNOSTICS restriccion=CONSTRAINT_NAME;
   RAISE EXCEPTION 'Conflicto C2 en %, restriccion %; se revierte toda la carga',tabla,restriccion;
  END;
 END LOOP;
END $$;
COMMIT;
\echo 'C2 cargado: 4 especialidades, 5 medicos, 4 usuarios, 8 pacientes, 25 horarios, 10 citas, 6 consultas, 6 recetas, 6 indicaciones y 8 eventos'
