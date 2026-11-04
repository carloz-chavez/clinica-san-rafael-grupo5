\set ON_ERROR_STOP on
BEGIN;
SET LOCAL TIME ZONE 'America/Lima';
SET LOCAL statement_timeout = '15s';
CREATE TEMP TABLE resultados(nombre text, aprobada boolean, detalle text);
CREATE FUNCTION pg_temp.probar(nombre text, sentencia text, estado text DEFAULT NULL,
                               patron text DEFAULT NULL, rol text DEFAULT NULL)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE codigo text; mensaje text; correcto boolean := false;
BEGIN
    BEGIN
        IF rol IS NOT NULL THEN EXECUTE format('SET LOCAL ROLE %I',rol); END IF;
        EXECUTE sentencia;
        correcto := estado IS NULL;
        mensaje := CASE WHEN correcto THEN 'aceptada' ELSE 'ERROR: no rechazo la operacion' END;
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS codigo = RETURNED_SQLSTATE, mensaje = MESSAGE_TEXT;
        correcto := estado IS NOT NULL AND codigo = estado
                    AND (patron IS NULL OR mensaje LIKE '%' || patron || '%');
        mensaje := codigo || ': ' || mensaje;
    END;
    RESET ROLE;
    INSERT INTO resultados VALUES(nombre,correcto,mensaje);
END $$;
-- IDs explicitos y transaccion revertida: no consumir secuencias existentes.
SELECT pg_temp.probar('01 especialidad', $s$INSERT INTO especialidades OVERRIDING SYSTEM VALUE VALUES (910001,'Especialidad ficticia QA',NULL)$s$);
SELECT pg_temp.probar('02 medico', $s$INSERT INTO medicos(id_medico,nombres,apellidos,numero_colegiatura,id_especialidad) OVERRIDING SYSTEM VALUE VALUES (910001,'Medico','Ficticio','QA-910001',910001),(910002,'Medico','Alternativo','QA-910002',910001)$s$);
SELECT pg_temp.probar('03 paciente', $s$INSERT INTO pacientes(id_paciente,dni,nombres,apellidos,fecha_nacimiento) OVERRIDING SYSTEM VALUE VALUES (910001,'99000001','Paciente','Ficticio','2000-01-01'),(910002,'99000002','Paciente','Alternativo','2000-01-01')$s$);
SELECT pg_temp.probar('04 horario', $s$INSERT INTO horarios_medicos(id_horario,id_medico,dia_semana,hora_inicio,hora_fin) OVERRIDING SYSTEM VALUE VALUES (910001,910001,extract(isodow from current_date+14), '08:00','12:00'),(910002,910002,extract(isodow from current_date+14),'08:00','12:00')$s$);
SELECT pg_temp.probar('05 cita 30 minutos', $s$INSERT INTO citas(id_cita,id_paciente,id_medico,fecha,hora,motivo) OVERRIDING SYSTEM VALUE VALUES (910001,910001,910001,current_date+14,'09:00','Prueba ficticia')$s$);
SELECT pg_temp.probar('06 consulta', $s$INSERT INTO consultas_medicas(id_consulta,id_paciente,id_medico,id_cita,fecha_hora) OVERRIDING SYSTEM VALUE VALUES (910001,910001,910001,910001,(current_date+14)+time '09:00')$s$);
SELECT pg_temp.probar('07 receta', $s$INSERT INTO recetas(id_receta,id_consulta,medicamento,dosis,frecuencia) OVERRIDING SYSTEM VALUE VALUES (910001,910001,'Producto ficticio','Dosis ficticia','Frecuencia ficticia')$s$);
SELECT pg_temp.probar('08 indicacion', $s$INSERT INTO indicaciones_medicas(id_indicacion,id_consulta,descripcion) OVERRIDING SYSTEM VALUE VALUES(910001,910001,'Indicacion ficticia')$s$);
SELECT pg_temp.probar('09 DNI duplicado', $s$INSERT INTO pacientes(id_paciente,dni,nombres,apellidos,fecha_nacimiento) OVERRIDING SYSTEM VALUE VALUES (910003,'99000001','Otro','Ficticio','2000-01-01')$s$,'23505','pacientes_dni_key');
SELECT pg_temp.probar('10 medico duplicado', $s$INSERT INTO citas(id_cita,id_paciente,id_medico,fecha,hora,motivo) OVERRIDING SYSTEM VALUE VALUES (910003,910002,910001,current_date+14,'09:00','QA')$s$,'23505','uq_cita_medico_fecha_hora');
SELECT pg_temp.probar('11 paciente duplicado', $s$INSERT INTO citas(id_cita,id_paciente,id_medico,fecha,hora,motivo) OVERRIDING SYSTEM VALUE VALUES (910003,910001,910002,current_date+14,'09:00','QA')$s$,'23505','uq_cita_paciente_fecha_hora');
SELECT pg_temp.probar('12 fuera de horario', $s$INSERT INTO citas(id_cita,id_paciente,id_medico,fecha,hora,motivo) OVERRIDING SYSTEM VALUE VALUES (910003,910002,910001,current_date+14,'12:00','QA')$s$,'P0001','El turno no esta dentro');
SELECT pg_temp.probar('13 bloque invalido', $s$INSERT INTO citas(id_cita,id_paciente,id_medico,fecha,hora,motivo) OVERRIDING SYSTEM VALUE VALUES (910003,910002,910001,current_date+14,'09:15','QA')$s$,'23514','chk_cita_bloque');
SELECT pg_temp.probar('14 superposicion', $s$INSERT INTO horarios_medicos(id_horario,id_medico,dia_semana,hora_inicio,hora_fin) OVERRIDING SYSTEM VALUE VALUES (910003,910001,extract(isodow from current_date+14),'08:30','10:00')$s$,'23P01','ex_horarios_superpuestos');
SELECT pg_temp.probar('15 cambiar horario', 'UPDATE horarios_medicos SET hora_fin=''09:00'' WHERE id_horario=910001','P0001','quedaria sin disponibilidad');
SELECT pg_temp.probar('15b eliminar horario','DELETE FROM horarios_medicos WHERE id_horario=910001','P0001','quedaria sin disponibilidad');
SELECT pg_temp.probar('15c desactivar horario','UPDATE horarios_medicos SET activo=false WHERE id_horario=910001','P0001','quedaria sin disponibilidad');
SELECT pg_temp.probar('16 desactivar medico','UPDATE medicos SET activo=false WHERE id_medico=910001','P0001','con citas futuras');
SELECT pg_temp.probar('17 consulta paciente diferente', $s$UPDATE consultas_medicas SET id_paciente=910002 WHERE id_consulta=910001$s$,'23503','fk_consulta_cita');
INSERT INTO usuarios(id_usuario,correo,contrasena_hash,rol) OVERRIDING SYSTEM VALUE VALUES(910001,'qa@example.invalid','hash-ficticio-no-utilizable','ADMINISTRADOR');
INSERT INTO bitacora_auditoria(id_auditoria,id_usuario,accion,entidad,id_registro) OVERRIDING SYSTEM VALUE VALUES(910001,910001,'CREACION','PRUEBA',910001);
SELECT pg_temp.probar('18 auditoria UPDATE','UPDATE bitacora_auditoria SET detalle=''QA'' WHERE id_auditoria=910001','P0001','no pueden');
SELECT pg_temp.probar('19 auditoria DELETE','DELETE FROM bitacora_auditoria WHERE id_auditoria=910001','P0001','no pueden');
SELECT pg_temp.probar('19b auditoria TRUNCATE','TRUNCATE bitacora_auditoria','P0001','no pueden');
SELECT pg_temp.probar('20 writer INSERT', $s$INSERT INTO bitacora_auditoria(id_usuario,accion,entidad,id_registro) VALUES(910001,'CREACION','PRUEBA',910001)$s$,NULL,NULL,'clinica_auditoria_writer');
SELECT pg_temp.probar('20 writer SELECT','SELECT * FROM bitacora_auditoria','42501',NULL,'clinica_auditoria_writer');
SELECT pg_temp.probar('20 reader SELECT','SELECT * FROM bitacora_auditoria',NULL,NULL,'clinica_auditoria_reader');
SELECT pg_temp.probar('20 reader INSERT', $s$INSERT INTO bitacora_auditoria(id_usuario,accion,entidad,id_registro) VALUES(910001,'CREACION','PRUEBA',910001)$s$,'42501',NULL,'clinica_auditoria_reader');
SELECT pg_temp.probar('20 writer RETURNING', $s$INSERT INTO bitacora_auditoria(id_usuario,accion,entidad,id_registro) VALUES(910001,'CREACION','PRUEBA',910001) RETURNING *$s$,'42501',NULL,'clinica_auditoria_writer');
SELECT pg_temp.probar('20 writer UPDATE','UPDATE bitacora_auditoria SET detalle=''QA''','42501',NULL,'clinica_auditoria_writer');
SELECT pg_temp.probar('20 writer DELETE','DELETE FROM bitacora_auditoria','42501',NULL,'clinica_auditoria_writer');
SELECT pg_temp.probar('20 writer TRUNCATE','TRUNCATE bitacora_auditoria','42501',NULL,'clinica_auditoria_writer');
SELECT pg_temp.probar('20 reader UPDATE','UPDATE bitacora_auditoria SET detalle=''QA''','42501',NULL,'clinica_auditoria_reader');
SELECT pg_temp.probar('20 reader DELETE','DELETE FROM bitacora_auditoria','42501',NULL,'clinica_auditoria_reader');
SELECT pg_temp.probar('20 reader TRUNCATE','TRUNCATE bitacora_auditoria','42501',NULL,'clinica_auditoria_reader');
-- La cancelacion libera el turno y permite cambiar disponibilidad.
SELECT pg_temp.probar('21 cancelar', 'UPDATE citas SET estado=''cancelada'' WHERE id_cita=910001');
SELECT pg_temp.probar('22 reutilizar turno', $s$INSERT INTO citas(id_cita,id_paciente,id_medico,fecha,hora,motivo) OVERRIDING SYSTEM VALUE VALUES (910004,910002,910001,current_date+14,'09:00','QA')$s$);
SELECT pg_temp.probar('23 limite final 30 minutos', $s$INSERT INTO citas(id_cita,id_paciente,id_medico,fecha,hora,motivo) OVERRIDING SYSTEM VALUE VALUES (910005,910001,910001,current_date+14,'11:30','QA')$s$);
TABLE resultados;
SELECT count(*) FILTER(WHERE aprobada) AS aprobadas,
       count(*) FILTER(WHERE NOT aprobada) AS fallidas FROM resultados;
SELECT EXISTS(SELECT FROM resultados WHERE NOT aprobada) AS hay_fallos \gset
ROLLBACK;
\if :hay_fallos
    \echo 'FALLO: revisar resultados anteriores; datos revertidos'
    DO $$ BEGIN RAISE EXCEPTION 'La suite contiene pruebas fallidas'; END $$;
\endif
\echo 'OK: pruebas aprobadas; datos revertidos (identity de auditoria puede avanzar)'
