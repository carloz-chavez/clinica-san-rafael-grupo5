-- Ejecutar como propietario/administrador tras 01_esquema.sql.
-- No crea LOGIN, contrasenas, membresias ni cambia propietarios.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = pg_catalog, public;
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM pg_roles
        WHERE rolname IN ('clinica_auditoria_writer', 'clinica_auditoria_reader')
          AND (rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication
               OR rolbypassrls OR rolcanlogin)
    ) OR (SELECT count(*) FROM pg_roles WHERE rolname IN
        ('clinica_auditoria_writer', 'clinica_auditoria_reader')) <> 2 THEN
        RAISE EXCEPTION 'Se requieren los dos roles NOLOGIN sin atributos administrativos de 01';
    END IF;
    IF EXISTS (SELECT FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member
               WHERE r.rolname IN ('clinica_auditoria_writer','clinica_auditoria_reader')) THEN
        RAISE EXCEPTION 'Revisar membresias heredadas de los roles tecnicos antes de continuar';
    END IF;
END $$;
REVOKE ALL ON public.bitacora_auditoria FROM PUBLIC,
    clinica_auditoria_writer, clinica_auditoria_reader;
REVOKE ALL ON SEQUENCE public.bitacora_auditoria_id_auditoria_seq
    FROM PUBLIC, clinica_auditoria_writer, clinica_auditoria_reader;
GRANT USAGE ON SCHEMA public TO clinica_auditoria_writer, clinica_auditoria_reader;
-- Identity genera su valor sin conceder acceso directo a la secuencia.
GRANT INSERT (id_usuario, id_paciente, accion, entidad, id_registro, detalle)
    ON public.bitacora_auditoria TO clinica_auditoria_writer;
GRANT SELECT ON public.bitacora_auditoria TO clinica_auditoria_reader;
-- Fallar atomicamente si PUBLIC u otros grants de columna dan acceso adicional.
DO $$
DECLARE r text; p text;
BEGIN
    FOREACH r IN ARRAY ARRAY['clinica_auditoria_writer','clinica_auditoria_reader'] LOOP
        FOREACH p IN ARRAY ARRAY['UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'] LOOP
            IF has_table_privilege(r,'public.bitacora_auditoria',p) THEN
                RAISE EXCEPTION 'Privilegio inesperado: % %',r,p;
            END IF;
        END LOOP;
    END LOOP;
    IF has_any_column_privilege('clinica_auditoria_writer','public.bitacora_auditoria','SELECT')
       OR has_any_column_privilege('clinica_auditoria_writer','public.bitacora_auditoria','UPDATE')
       OR has_any_column_privilege('clinica_auditoria_reader','public.bitacora_auditoria','INSERT')
       OR has_any_column_privilege('clinica_auditoria_reader','public.bitacora_auditoria','UPDATE') THEN
        RAISE EXCEPTION 'Acceso de columna incompatible; revisar ACL existentes';
    END IF;
END $$;
COMMIT;
