
-- ============================================================
-- CLINICA SAN RAFAEL S.A.C.
-- SPRINT 1 - ESQUEMA DE BASE DE DATOS
-- Ejecutar sobre una base de datos vacia.
-- ============================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS btree_gist;


-- ============================================================
-- 1. ESPECIALIDADES
-- ============================================================

CREATE TABLE especialidades (
    id_especialidad INTEGER GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT,

    CONSTRAINT chk_especialidad_nombre
        CHECK (LENGTH(TRIM(nombre)) > 0)
);


-- ============================================================
-- 2. MEDICOS
-- ============================================================

CREATE TABLE medicos (
    id_medico INTEGER GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    numero_colegiatura VARCHAR(30) NOT NULL UNIQUE,
    id_especialidad INTEGER NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT fk_medico_especialidad
        FOREIGN KEY (id_especialidad)
        REFERENCES especialidades(id_especialidad),

    CONSTRAINT chk_medico_nombres
        CHECK (LENGTH(TRIM(nombres)) > 0),

    CONSTRAINT chk_medico_apellidos
        CHECK (LENGTH(TRIM(apellidos)) > 0),

    CONSTRAINT chk_medico_colegiatura
        CHECK (LENGTH(TRIM(numero_colegiatura)) > 0)
);


-- ============================================================
-- 3. USUARIOS
-- ============================================================

CREATE TABLE usuarios (
    id_usuario INTEGER GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    correo VARCHAR(150) NOT NULL,
    contrasena_hash TEXT NOT NULL,
    rol VARCHAR(20) NOT NULL,
    id_medico INTEGER UNIQUE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT fk_usuario_medico
        FOREIGN KEY (id_medico)
        REFERENCES medicos(id_medico),

    CONSTRAINT chk_usuario_rol
        CHECK (
            rol IN (
                'ADMISION',
                'MEDICO',
                'ADMINISTRADOR'
            )
        ),

    CONSTRAINT chk_usuario_medico
        CHECK (
            (rol = 'MEDICO' AND id_medico IS NOT NULL)
            OR
            (rol <> 'MEDICO' AND id_medico IS NULL)
        ),

    CONSTRAINT chk_usuario_correo
        CHECK (
            correo = TRIM(correo)
            AND correo ~*
                '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'
        ),

    CONSTRAINT chk_usuario_hash
        CHECK (LENGTH(TRIM(contrasena_hash)) > 0)
);

CREATE UNIQUE INDEX uq_usuario_correo_normalizado
ON usuarios (LOWER(correo));


-- ============================================================
-- 4. PACIENTES
-- ============================================================

CREATE TABLE pacientes (
    id_paciente INTEGER GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    dni CHAR(8) NOT NULL UNIQUE,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    fecha_nacimiento DATE NOT NULL,
    sexo CHAR(1),
    telefono VARCHAR(20),
    correo VARCHAR(150),
    direccion VARCHAR(250),
    fecha_registro TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT chk_paciente_dni
        CHECK (dni ~ '^[0-9]{8}$'),

    CONSTRAINT chk_paciente_nombres
        CHECK (LENGTH(TRIM(nombres)) > 0),

    CONSTRAINT chk_paciente_apellidos
        CHECK (LENGTH(TRIM(apellidos)) > 0),

    CONSTRAINT chk_paciente_fecha_nacimiento
        CHECK (
            fecha_nacimiento BETWEEN
                DATE '1900-01-01'
                AND DATE '2100-12-31'
        ),

    CONSTRAINT chk_paciente_sexo
        CHECK (
            sexo IS NULL
            OR sexo IN ('M', 'F')
        ),

    CONSTRAINT chk_paciente_correo
        CHECK (
            correo IS NULL
            OR correo ~*
                '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'
        )
);

CREATE INDEX idx_pacientes_apellidos_nombres
ON pacientes (apellidos, nombres);


-- ============================================================
-- 5. HORARIOS MEDICOS
-- ============================================================
CREATE TABLE horarios_medicos (
    id_horario INTEGER GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    id_medico INTEGER NOT NULL,
    dia_semana SMALLINT NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT fk_horario_medico
        FOREIGN KEY (id_medico)
        REFERENCES medicos(id_medico),

    CONSTRAINT chk_horario_dia
        CHECK (dia_semana BETWEEN 1 AND 7),

    CONSTRAINT chk_horario_horas
        CHECK (hora_inicio < hora_fin),

    CONSTRAINT chk_horario_bloques
        CHECK (
            EXTRACT(MINUTE FROM hora_inicio) IN (0, 30)
            AND EXTRACT(SECOND FROM hora_inicio) = 0
            AND EXTRACT(MINUTE FROM hora_fin) IN (0, 30)
            AND EXTRACT(SECOND FROM hora_fin) = 0
        ),

    CONSTRAINT uq_horario_medico
        UNIQUE (id_medico, dia_semana, hora_inicio),

    CONSTRAINT ex_horarios_superpuestos
        EXCLUDE USING gist (
            id_medico WITH =,
            dia_semana WITH =,
            int4range(
                EXTRACT(EPOCH FROM hora_inicio)::INTEGER,
                EXTRACT(EPOCH FROM hora_fin)::INTEGER,
                '[)'
            ) WITH &&
        )
        WHERE (activo = TRUE)
);


-- ============================================================
-- 6. CITAS
-- ============================================================

CREATE TABLE citas (
    id_cita INTEGER GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    id_paciente INTEGER NOT NULL,
    id_medico INTEGER NOT NULL,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    estado VARCHAR(15) NOT NULL DEFAULT 'registrada',
    motivo VARCHAR(200) NOT NULL,
    fecha_registro TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_cita_paciente
        FOREIGN KEY (id_paciente)
        REFERENCES pacientes(id_paciente),

    CONSTRAINT fk_cita_medico
        FOREIGN KEY (id_medico)
        REFERENCES medicos(id_medico),

    CONSTRAINT chk_cita_estado
        CHECK (
            estado IN (
                'registrada',
                'confirmada',
                'cancelada',
                'atendida'
            )
        ),

    CONSTRAINT chk_cita_motivo
        CHECK (LENGTH(TRIM(motivo)) > 0),

    CONSTRAINT chk_cita_bloque
        CHECK (
            EXTRACT(MINUTE FROM hora) IN (0, 30)
            AND EXTRACT(SECOND FROM hora) = 0
        ),

    CONSTRAINT uq_cita_paciente_medico
        UNIQUE (id_cita, id_paciente, id_medico)
);

-- Un medico no puede tener dos citas
-- no canceladas en el mismo turno.
CREATE UNIQUE INDEX uq_cita_medico_fecha_hora
ON citas (id_medico, fecha, hora)
WHERE estado <> 'cancelada';

-- Un paciente no puede tener dos citas
-- no canceladas en el mismo turno.
CREATE UNIQUE INDEX uq_cita_paciente_fecha_hora
ON citas (id_paciente, fecha, hora)
WHERE estado <> 'cancelada';

CREATE INDEX idx_citas_paciente_fecha
ON citas (id_paciente, fecha DESC);

CREATE INDEX idx_citas_medico_fecha
ON citas (id_medico, fecha, hora);


-- ============================================================
-- 6.1. BLOQUEO TRANSACCIONAL POR MEDICO
-- ============================================================
CREATE OR REPLACE FUNCTION public.bloquear_agenda_medico(
    p_id_medico INTEGER
)
RETURNS VOID SET search_path = pg_catalog, public AS $$
BEGIN
    -- Una instantanea REPEATABLE READ puede quedar obsoleta tras esperar.
    -- READ COMMITTED renueva la instantanea; SERIALIZABLE puede exigir 40001.
    IF current_setting('transaction_isolation') = 'repeatable read' THEN
        RAISE EXCEPTION USING ERRCODE = '0A000', MESSAGE =
            'Agenda no admite REPEATABLE READ; usar READ COMMITTED o SERIALIZABLE';
    END IF;
    PERFORM pg_advisory_xact_lock(
        724001,
        p_id_medico
    );
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 6.2. VALIDACION DE CITAS
-- ============================================================

CREATE OR REPLACE FUNCTION validar_horario_cita()
RETURNS TRIGGER AS $$
DECLARE
    v_medico_activo BOOLEAN;
    v_paciente_activo BOOLEAN;
BEGIN

    -- Si una cita cambia de medico, bloquear
    -- ambas agendas en orden ascendente.
    IF TG_OP = 'UPDATE' THEN

        IF OLD.id_medico <> NEW.id_medico THEN
            PERFORM bloquear_agenda_medico(
                LEAST(OLD.id_medico, NEW.id_medico)
            );

            PERFORM bloquear_agenda_medico(
                GREATEST(OLD.id_medico, NEW.id_medico)
            );
        ELSE
            PERFORM bloquear_agenda_medico(NEW.id_medico);
        END IF;

    ELSE
        PERFORM bloquear_agenda_medico(NEW.id_medico);
    END IF;

    -- Las citas canceladas no ocupan disponibilidad.
    IF NEW.estado = 'cancelada' THEN
        RETURN NEW;
    END IF;

    -- Verificar medico activo.
    SELECT activo
    INTO v_medico_activo
    FROM medicos
    WHERE id_medico = NEW.id_medico;

    IF v_medico_activo IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION
            'El medico no existe o esta inactivo';
    END IF;

    -- Verificar paciente activo.
    SELECT activo
    INTO v_paciente_activo
    FROM pacientes
    WHERE id_paciente = NEW.id_paciente;

    IF v_paciente_activo IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION
            'El paciente no existe o esta inactivo';
    END IF;

    -- Validar los 30 minutos completos.
    -- Usar segundos evita desbordamientos
    -- al sumar intervalos cerca de medianoche.
    IF NOT EXISTS (
        SELECT 1
        FROM horarios_medicos h
        WHERE h.id_medico = NEW.id_medico
          AND h.activo = TRUE
          AND h.dia_semana =
              EXTRACT(ISODOW FROM NEW.fecha)::INTEGER
          AND NEW.hora >= h.hora_inicio
          AND (
              EXTRACT(EPOCH FROM NEW.hora) + 1800
          ) <= EXTRACT(EPOCH FROM h.hora_fin)
    ) THEN
        RAISE EXCEPTION
            'El turno no esta dentro del horario del medico';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_horario_cita
BEFORE INSERT OR UPDATE OF
    id_paciente,
    id_medico,
    fecha,
    hora,
    estado
ON citas
FOR EACH ROW
EXECUTE FUNCTION validar_horario_cita();


-- ============================================================
-- 6.3. PROTECCION DE CAMBIOS DE HORARIO
-- ============================================================

CREATE OR REPLACE FUNCTION proteger_horario_medico()
RETURNS TRIGGER AS $$
DECLARE
    v_id_medico INTEGER;
    v_nuevo_activo BOOLEAN := FALSE;
    v_nuevo_dia SMALLINT;
    v_nueva_hora_inicio TIME;
    v_nueva_hora_fin TIME;
    v_cita_afectada INTEGER;
BEGIN

    -- bloquear agenda y permitir crear
    -- el horario. La restriccion EXCLUDE
    -- comprobara posibles superposiciones.
    IF TG_OP = 'INSERT' THEN
        PERFORM bloquear_agenda_medico(NEW.id_medico);
        RETURN NEW;
    END IF;

    v_id_medico := OLD.id_medico;

    -- No se permite transferir un horario
    -- existente a otro medico.
    IF TG_OP = 'UPDATE' THEN

        IF NEW.id_medico <> OLD.id_medico THEN
            RAISE EXCEPTION
                'No se puede cambiar el medico del horario';
        END IF;

        v_nuevo_activo := NEW.activo;
        v_nuevo_dia := NEW.dia_semana;
        v_nueva_hora_inicio := NEW.hora_inicio;
        v_nueva_hora_fin := NEW.hora_fin;
    END IF;

    PERFORM bloquear_agenda_medico(v_id_medico);

    -- Buscar citas futuras que perderian cobertura.
    -- Se excluye la version antigua del horario.
    -- Para UPDATE se considera la version nueva.
    -- Para DELETE no hay horario sustituto.

    SELECT c.id_cita
    INTO v_cita_afectada
    FROM citas c
    WHERE c.id_medico = v_id_medico
      AND c.estado <> 'cancelada'
      AND (c.fecha + c.hora) >= LOCALTIMESTAMP

      AND NOT (
          EXISTS (
              SELECT 1
              FROM horarios_medicos h
              WHERE h.id_medico = c.id_medico
                AND h.id_horario <> OLD.id_horario
                AND h.activo = TRUE
                AND h.dia_semana =
                    EXTRACT(ISODOW FROM c.fecha)::INTEGER
                AND c.hora >= h.hora_inicio
                AND (
                    EXTRACT(EPOCH FROM c.hora) + 1800
                ) <= EXTRACT(EPOCH FROM h.hora_fin)
          )

          OR (
              v_nuevo_activo = TRUE
              AND v_nuevo_dia =
                  EXTRACT(ISODOW FROM c.fecha)::INTEGER
              AND c.hora >= v_nueva_hora_inicio
              AND (
                  EXTRACT(EPOCH FROM c.hora) + 1800
              ) <= EXTRACT(EPOCH FROM v_nueva_hora_fin)
          )
      )
    LIMIT 1;

    IF v_cita_afectada IS NOT NULL THEN
        RAISE EXCEPTION
            'No se puede modificar el horario: '
            'la cita % quedaria sin disponibilidad',
            v_cita_afectada;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_proteger_horario_medico
BEFORE INSERT OR UPDATE OR DELETE
ON horarios_medicos
FOR EACH ROW
EXECUTE FUNCTION proteger_horario_medico();


-- ============================================================
-- 6.4. PROTEGER DESACTIVACION DE MEDICOS
-- ============================================================

CREATE OR REPLACE FUNCTION proteger_desactivacion_medico()
RETURNS TRIGGER AS $$
BEGIN

    -- Bloquear la agenda cuando cambia
    -- el estado de disponibilidad del medico.
    IF NEW.activo IS DISTINCT FROM OLD.activo THEN

        PERFORM bloquear_agenda_medico(NEW.id_medico);

        IF NEW.activo = FALSE
           AND EXISTS (
               SELECT 1
               FROM citas c
               WHERE c.id_medico = NEW.id_medico
                 AND c.estado <> 'cancelada'
                 AND (c.fecha + c.hora) >= LOCALTIMESTAMP
           ) THEN

            RAISE EXCEPTION
                'No se puede desactivar un medico '
                'con citas futuras pendientes';
        END IF;

    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_proteger_desactivacion_medico
BEFORE UPDATE OF activo
ON medicos
FOR EACH ROW
EXECUTE FUNCTION proteger_desactivacion_medico();


-- ============================================================
-- 7. CONSULTAS MEDICAS
-- ============================================================

CREATE TABLE consultas_medicas (
    id_consulta INTEGER GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    id_paciente INTEGER NOT NULL,
    id_medico INTEGER NOT NULL,
    id_cita INTEGER UNIQUE,
    fecha_hora TIMESTAMP NOT NULL,
    diagnostico_cie10 VARCHAR(100),
    observaciones TEXT,
    anulada BOOLEAN NOT NULL DEFAULT FALSE,
    motivo_anulacion VARCHAR(200),
    fecha_anulacion TIMESTAMP,
    id_usuario_anulacion INTEGER,

    CONSTRAINT fk_consulta_paciente
        FOREIGN KEY (id_paciente)
        REFERENCES pacientes(id_paciente),

    CONSTRAINT fk_consulta_medico
        FOREIGN KEY (id_medico)
        REFERENCES medicos(id_medico),

    CONSTRAINT fk_consulta_cita
        FOREIGN KEY (
            id_cita,
            id_paciente,
            id_medico
        )
        REFERENCES citas (
            id_cita,
            id_paciente,
            id_medico
        ),

    CONSTRAINT fk_consulta_usuario_anulacion
        FOREIGN KEY (id_usuario_anulacion)
        REFERENCES usuarios(id_usuario),

    CONSTRAINT chk_consulta_anulacion
        CHECK (
            (
                anulada = FALSE
                AND motivo_anulacion IS NULL
                AND fecha_anulacion IS NULL
                AND id_usuario_anulacion IS NULL
            )
            OR
            (
                anulada = TRUE
                AND NULLIF(
                    TRIM(motivo_anulacion), ''
                ) IS NOT NULL
                AND fecha_anulacion IS NOT NULL
                AND id_usuario_anulacion IS NOT NULL
            )
        ),

    CONSTRAINT chk_consulta_fecha_anulacion
        CHECK (
            fecha_anulacion IS NULL
            OR fecha_anulacion >= fecha_hora
        )
);

CREATE INDEX idx_consultas_paciente_fecha
ON consultas_medicas (id_paciente, fecha_hora DESC);

CREATE INDEX idx_consultas_medico_fecha
ON consultas_medicas (id_medico, fecha_hora DESC);


-- ============================================================
-- 8. RECETAS
-- ============================================================

CREATE TABLE recetas (
    id_receta INTEGER GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    id_consulta INTEGER NOT NULL,
    medicamento VARCHAR(150) NOT NULL,
    dosis VARCHAR(100) NOT NULL,
    frecuencia VARCHAR(100) NOT NULL,
    duracion VARCHAR(100),
    indicaciones TEXT,
    fecha_registro TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_receta_consulta
        FOREIGN KEY (id_consulta)
        REFERENCES consultas_medicas(id_consulta),

    CONSTRAINT chk_receta_medicamento
        CHECK (LENGTH(TRIM(medicamento)) > 0),

    CONSTRAINT chk_receta_dosis
        CHECK (LENGTH(TRIM(dosis)) > 0),

    CONSTRAINT chk_receta_frecuencia
        CHECK (LENGTH(TRIM(frecuencia)) > 0),

    CONSTRAINT chk_receta_duracion
        CHECK (
            duracion IS NULL
            OR LENGTH(TRIM(duracion)) > 0
        )
);

CREATE INDEX idx_recetas_consulta
ON recetas (id_consulta);


-- ============================================================
-- 9. BITACORA AUDITORIA
-- ============================================================

CREATE TABLE bitacora_auditoria (
    id_auditoria BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    id_usuario INTEGER NOT NULL,
    id_paciente INTEGER,
    accion VARCHAR(30) NOT NULL,
    entidad VARCHAR(100) NOT NULL,
    id_registro INTEGER NOT NULL,
    fecha_evento TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,
    detalle TEXT,

    CONSTRAINT fk_auditoria_usuario
        FOREIGN KEY (id_usuario)
        REFERENCES usuarios(id_usuario),

    CONSTRAINT fk_auditoria_paciente
        FOREIGN KEY (id_paciente)
        REFERENCES pacientes(id_paciente),

    CONSTRAINT chk_auditoria_accion
        CHECK (
            accion IN (
                'CREAR',
                'ACTUALIZAR',
                'CONSULTAR',
                'ANULAR'
            )
        ),

    CONSTRAINT chk_auditoria_entidad
        CHECK (LENGTH(TRIM(entidad)) > 0),

    CONSTRAINT chk_auditoria_id_registro
        CHECK (id_registro > 0)
);

-- Proteger registros contra UPDATE y DELETE.
CREATE OR REPLACE FUNCTION impedir_modificacion_auditoria()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'Los registros de auditoria no pueden '
        'modificarse ni eliminarse';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_bitacora_inmutable
BEFORE UPDATE OR DELETE
ON bitacora_auditoria
FOR EACH ROW
EXECUTE FUNCTION impedir_modificacion_auditoria();

-- Evitar vaciar la tabla mediante TRUNCATE.
CREATE TRIGGER trg_bitacora_no_truncate
BEFORE TRUNCATE
ON bitacora_auditoria
FOR EACH STATEMENT
EXECUTE FUNCTION impedir_modificacion_auditoria();

CREATE INDEX idx_auditoria_paciente_fecha
ON bitacora_auditoria (id_paciente, fecha_evento DESC);

CREATE INDEX idx_auditoria_usuario_fecha
ON bitacora_auditoria (id_usuario, fecha_evento DESC);


-- ============================================================
-- 10. INDICACIONES MEDICAS
-- ============================================================

CREATE TABLE indicaciones_medicas (
    id_indicacion INTEGER GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    id_consulta INTEGER NOT NULL,
    descripcion TEXT NOT NULL,
    fecha_registro TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_indicacion_consulta
        FOREIGN KEY (id_consulta)
        REFERENCES consultas_medicas(id_consulta),

    CONSTRAINT chk_indicacion_descripcion
        CHECK (LENGTH(TRIM(descripcion)) > 0)
);

CREATE INDEX idx_indicaciones_consulta
ON indicaciones_medicas (id_consulta);


-- ============================================================
-- 11. ROLES TECNICOS DE AUDITORIA
-- ============================================================
DO $$
BEGIN

    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'clinica_auditoria_writer'
    ) THEN
        CREATE ROLE clinica_auditoria_writer NOLOGIN;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'clinica_auditoria_reader'
    ) THEN
        CREATE ROLE clinica_auditoria_reader NOLOGIN;
    END IF;

END;
$$ LANGUAGE plpgsql;

REVOKE ALL
ON TABLE bitacora_auditoria
FROM PUBLIC;

-- Writer: solamente insertar eventos.
GRANT USAGE ON SCHEMA public
TO clinica_auditoria_writer;

GRANT INSERT
ON bitacora_auditoria
TO clinica_auditoria_writer;

GRANT USAGE
ON SEQUENCE bitacora_auditoria_id_auditoria_seq
TO clinica_auditoria_writer;

-- Reader: solamente consultar eventos.
GRANT USAGE ON SCHEMA public
TO clinica_auditoria_reader;

GRANT SELECT
ON bitacora_auditoria
TO clinica_auditoria_reader;


-- ============================================================
-- FIN DEL ESQUEMA
-- ============================================================

COMMIT;
