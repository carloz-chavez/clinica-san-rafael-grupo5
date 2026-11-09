-- Solo para un servidor QA efimero y vacio, nunca para desarrollo.
\set ON_ERROR_STOP on
DO $$
BEGIN
    IF current_database() <> 'clinica_c3_qa' THEN
        RAISE EXCEPTION 'La inicializacion requiere clinica_c3_qa';
    END IF;
    IF current_setting('server_version_num')::integer / 10000 <> 16 THEN
        RAISE EXCEPTION 'QA requiere PostgreSQL 16';
    END IF;
    -- 01 crea roles; C3 hace SET ROLE y concurrencia crea/elimina bases.
    -- El superusuario se limita al servidor desechable del job.
    IF NOT EXISTS (
        SELECT FROM pg_roles
        WHERE rolname = current_user AND rolsuper AND rolcreatedb AND rolcreaterole
    ) THEN
        RAISE EXCEPTION 'QA requiere administrador con CREATEDB y CREATEROLE';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_available_extensions WHERE name = 'btree_gist') THEN
        RAISE EXCEPTION 'Falta la extension btree_gist requerida por el esquema';
    END IF;
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public')
       OR EXISTS (
           SELECT FROM pg_roles
           WHERE rolname IN ('clinica_auditoria_writer', 'clinica_auditoria_reader')
       ) THEN
        RAISE EXCEPTION 'QA debe comenzar con base vacia y sin roles de otra ejecucion';
    END IF;
END $$;
