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

-- C2 es optativo para conservar las 36 pruebas originales de C1 sin seed.
\if :{?probar_seed}
BEGIN;
CREATE FUNCTION pg_temp.verificar_c2(nombre text, cumple boolean) RETURNS void
LANGUAGE plpgsql AS $$ BEGIN
 IF cumple IS DISTINCT FROM true THEN RAISE EXCEPTION 'Fallo C2: %',nombre; END IF;
 RAISE NOTICE 'OK C2: %',nombre;
END $$;
SELECT pg_temp.verificar_c2('4 especialidades',(SELECT count(*)=4 FROM especialidades WHERE id_especialidad BETWEEN 800001 AND 800099));
SELECT pg_temp.verificar_c2('5 medicos activos y especialidades correctas',(SELECT count(*)=5 AND bool_and(m.activo AND e.id_especialidad IS NOT NULL) FROM medicos m LEFT JOIN especialidades e USING(id_especialidad) WHERE m.id_medico BETWEEN 800001 AND 800099));
SELECT pg_temp.verificar_c2('4 usuarios con roles y medicos esperados',(SELECT array_agg(rol ORDER BY id_usuario)=ARRAY['ADMISION','MEDICO','MEDICO','ADMINISTRADOR']::varchar[] AND bool_and(activo AND CASE WHEN rol='MEDICO' THEN id_medico=id_usuario-1 ELSE id_medico IS NULL END) FROM usuarios WHERE id_usuario BETWEEN 800001 AND 800099));
SELECT pg_temp.verificar_c2('hashes Argon2id',(SELECT count(*)=4 AND bool_and(contrasena_hash LIKE '$argon2id$v=19$%') FROM usuarios WHERE id_usuario BETWEEN 800001 AND 800099));
SELECT pg_temp.verificar_c2('8 pacientes ficticios',(SELECT count(*)=8 AND count(DISTINCT dni)=8 AND bool_and(correo LIKE '%@example.invalid' AND activo) FROM pacientes WHERE id_paciente BETWEEN 800001 AND 800099));
SELECT pg_temp.verificar_c2('25 horarios validos',(SELECT count(*)=25 AND bool_and(activo AND dia_semana BETWEEN 1 AND 5 AND hora_inicio='08:00' AND hora_fin='12:00') FROM horarios_medicos WHERE id_horario BETWEEN 800001 AND 800099));
SELECT pg_temp.verificar_c2('sin horarios superpuestos',NOT EXISTS(SELECT FROM horarios_medicos a JOIN horarios_medicos b ON a.id_medico=b.id_medico AND a.dia_semana=b.dia_semana AND a.id_horario<b.id_horario AND a.hora_inicio<b.hora_fin AND b.hora_inicio<a.hora_fin WHERE a.activo AND b.activo AND a.id_horario BETWEEN 800001 AND 800099));
SELECT pg_temp.verificar_c2('10 citas y cuatro estados',(SELECT count(*)=10 AND array_agg(DISTINCT estado ORDER BY estado)=ARRAY['atendida','cancelada','confirmada','registrada']::varchar[] FROM citas WHERE id_cita BETWEEN 800001 AND 800099));
SELECT pg_temp.verificar_c2('citas de 30 minutos cubiertas',NOT EXISTS(SELECT FROM citas c WHERE c.id_cita BETWEEN 800001 AND 800099 AND NOT EXISTS(SELECT FROM horarios_medicos h WHERE h.id_medico=c.id_medico AND h.activo AND h.dia_semana=extract(isodow FROM c.fecha) AND c.hora>=h.hora_inicio AND extract(epoch FROM c.hora)+1800<=extract(epoch FROM h.hora_fin))));
SELECT pg_temp.verificar_c2('sin reservas simultaneas',NOT EXISTS(SELECT FROM citas a JOIN citas b ON a.id_cita<b.id_cita AND a.fecha=b.fecha AND a.hora=b.hora AND (a.id_medico=b.id_medico OR a.id_paciente=b.id_paciente) WHERE a.estado<>'cancelada' AND b.estado<>'cancelada' AND a.id_cita BETWEEN 800001 AND 800099));
SELECT pg_temp.verificar_c2('6 consultas, una anulada y cronologia correcta',(SELECT count(*)=6 AND count(*) FILTER(WHERE q.anulada)=1 AND bool_and(c.id_cita IS NOT NULL AND q.id_paciente=c.id_paciente AND q.id_medico=c.id_medico AND q.fecha_hora=c.fecha+c.hora AND c.estado='atendida') FROM consultas_medicas q LEFT JOIN citas c USING(id_cita) WHERE q.id_consulta BETWEEN 800001 AND 800099));
SELECT pg_temp.verificar_c2('6 recetas asociadas',(SELECT count(*)=6 AND bool_and(q.id_consulta IS NOT NULL AND r.fecha_registro>=q.fecha_hora) FROM recetas r LEFT JOIN consultas_medicas q USING(id_consulta) WHERE r.id_receta BETWEEN 800001 AND 800099));
SELECT pg_temp.verificar_c2('6 indicaciones asociadas',(SELECT count(*)=6 AND bool_and(q.id_consulta IS NOT NULL AND i.fecha_registro>=q.fecha_hora) FROM indicaciones_medicas i LEFT JOIN consultas_medicas q USING(id_consulta) WHERE i.id_indicacion BETWEEN 800001 AND 800099));
SELECT pg_temp.verificar_c2('8 eventos, cuatro acciones y registro NULL',(SELECT count(*)=8 AND count(*) FILTER(WHERE id_registro IS NULL)=2 AND array_agg(DISTINCT accion ORDER BY accion)=ARRAY['ANULACION','CONSULTA','CREACION','MODIFICACION']::varchar[] FROM bitacora_auditoria WHERE id_auditoria BETWEEN 800001 AND 800099));
SELECT pg_temp.verificar_c2('sin huerfanos de usuarios/pacientes en auditoria',NOT EXISTS(SELECT FROM bitacora_auditoria b LEFT JOIN usuarios u USING(id_usuario) LEFT JOIN pacientes p USING(id_paciente) WHERE b.id_auditoria BETWEEN 800001 AND 800099 AND (u.id_usuario IS NULL OR (b.id_paciente IS NOT NULL AND p.id_paciente IS NULL))));
SELECT pg_temp.verificar_c2('restricciones C1 validadas',NOT EXISTS(SELECT FROM pg_constraint WHERE connamespace='public'::regnamespace AND NOT convalidated));
ROLLBACK;
\echo 'OK: 16 comprobaciones C2 aprobadas'
\endif
