-- ============================================================
-- DATOS DEL MODO SIMULADO (solo desarrollo)
-- ============================================================
-- El modo simulado (AUTENTICACION_SIMULADA=true) opera como el
-- usuario id 1 con rol MEDICO e id_medico 1. Este script crea esos
-- registros ficticios para que el flujo completo del medico funcione
-- sin cargar el seed C2 ni iniciar sesion.
--
-- Carga manual sobre un esquema inicializado, desde la raiz:
--   docker compose cp db/03_modo_simulado.sql postgres:/tmp/03_modo_simulado.sql
--   docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U clinica -d clinica_san_rafael -f /tmp/03_modo_simulado.sql
--
-- El usuario nace con un hash invalido a proposito: no permite inicio
-- de sesion real. Todos los datos son ficticios.

INSERT INTO especialidades (id_especialidad, nombre, descripcion)
OVERRIDING SYSTEM VALUE
VALUES (1, 'Medicina General', 'Especialidad ficticia del modo simulado de desarrollo')
ON CONFLICT (id_especialidad) DO NOTHING;

INSERT INTO medicos (id_medico, nombres, apellidos, numero_colegiatura, id_especialidad, activo)
OVERRIDING SYSTEM VALUE
VALUES (1, 'Medico', 'Simulado', 'SIM-0001', 1, true)
ON CONFLICT (id_medico) DO NOTHING;

INSERT INTO usuarios (id_usuario, correo, contrasena_hash, rol, id_medico, activo)
OVERRIDING SYSTEM VALUE
VALUES (1, 'desarrollo.local@sanrafael.invalid', 'hash-ficticio-solo-desarrollo', 'MEDICO', 1, true)
ON CONFLICT (id_usuario) DO NOTHING;

INSERT INTO pacientes (dni, nombres, apellidos, fecha_nacimiento)
VALUES ('87654321', 'Paciente', 'De Prueba', '1990-05-14')
ON CONFLICT (dni) DO NOTHING;

SELECT setval(pg_get_serial_sequence('especialidades', 'id_especialidad'),
              (SELECT MAX(id_especialidad) FROM especialidades));
SELECT setval(pg_get_serial_sequence('medicos', 'id_medico'),
              (SELECT MAX(id_medico) FROM medicos));
SELECT setval(pg_get_serial_sequence('usuarios', 'id_usuario'),
              (SELECT MAX(id_usuario) FROM usuarios));
