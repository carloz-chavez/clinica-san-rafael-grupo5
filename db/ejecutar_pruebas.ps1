param([string]$Contenedor = ('clinica-sprint1-qa-' + [guid]::NewGuid().ToString('N').Substring(0,8)))
$ErrorActionPreference = 'Stop'
if ($Contenedor -notmatch '^clinica-sprint1-qa-[a-z0-9]+$') { throw 'Nombre QA invalido' }
$creado = $false
$pythonCreado = $false
$contenedorPython = "$Contenedor-python"
function DockerOk([string[]]$Argumentos) {
    & docker @Argumentos
    if ($LASTEXITCODE -ne 0) { throw "Docker fallo: $($Argumentos[0]) ($LASTEXITCODE)" }
}
function SqlArchivo([string]$Nombre) {
    DockerOk @('exec',$Contenedor,'psql','-X','-q','-v','ON_ERROR_STOP=1','-U','clinica','-d','clinica_pruebas','-f',"/pruebas/$Nombre")
}
try {
    DockerOk @('run','-d','--name',$Contenedor,'--label','clinica.qa=sprint1','--mount','type=tmpfs,destination=/var/lib/postgresql/data','-e','POSTGRES_HOST_AUTH_METHOD=trust','-e','POSTGRES_USER=clinica','-e','POSTGRES_DB=clinica_pruebas','postgres:16')
    $creado = $true
    $listo = $false
    for ($i=0; $i -lt 60; $i++) {
        & docker exec $Contenedor pg_isready -U clinica -d clinica_pruebas 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            # pg_isready puede detectar el servidor transitorio de initdb.
            $estado = & docker exec $Contenedor head -1 /var/lib/postgresql/data/postmaster.pid
            if ($LASTEXITCODE -eq 0 -and $estado -eq '1') { $listo = $true; break }
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $listo) { throw 'PostgreSQL QA no esta listo' }
    DockerOk @('cp',"$PSScriptRoot/.","${Contenedor}:/pruebas")
    SqlArchivo '01_esquema.sql'
    SqlArchivo '02_permisos.sql'
    $verificarEsquema = @'
DO $$
BEGIN
    IF (SELECT array_agg(tablename::text ORDER BY tablename) FROM pg_tables WHERE schemaname='public')
       IS DISTINCT FROM ARRAY['bitacora_auditoria','citas','consultas_medicas','especialidades',
          'horarios_medicos','indicaciones_medicas','medicos','pacientes','recetas','usuarios'] THEN
        RAISE EXCEPTION 'No se encontraron exactamente las diez tablas esperadas';
    END IF;
END $$;
BEGIN ISOLATION LEVEL READ COMMITTED;
SELECT public.bloquear_agenda_medico(0);
ROLLBACK;
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT public.bloquear_agenda_medico(0);
ROLLBACK;
'@
    DockerOk @('exec',$Contenedor,'psql','-X','-v','ON_ERROR_STOP=1','-U','clinica','-d','clinica_pruebas','-c',$verificarEsquema)
    SqlArchivo '03_pruebas.sql'
    # Repetibilidad de permisos y pruebas sobre el esquema definitivo.
    SqlArchivo '02_permisos.sql'
    SqlArchivo '03_pruebas.sql'
    & "$PSScriptRoot/pruebas_concurrencia.ps1" -Contenedor $Contenedor
    # Mutacion controlada SOLO en QA: demostrar que la suite detecta un defecto.
    DockerOk @('exec',$Contenedor,'psql','-X','-v','ON_ERROR_STOP=1','-U','clinica','-d','clinica_pruebas','-c','ALTER TABLE public.bitacora_auditoria DISABLE TRIGGER trg_bitacora_inmutable;')
    try {
        # Windows PowerShell convierte stderr nativo en ErrorRecord; aqui se
        # espera un error SQL y se valida expresamente su salida y mensaje.
        $preferencia = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            $resultado = & docker exec $Contenedor psql -X -q -v ON_ERROR_STOP=1 -U clinica -d clinica_pruebas -f /pruebas/03_pruebas.sql 2>&1
            $codigo = $LASTEXITCODE
        } finally { $ErrorActionPreference = $preferencia }
        if ($codigo -ne 3 -or ($resultado -join "`n") -notmatch 'La suite contiene pruebas fallidas') { throw 'La mutacion no produjo el fallo esperado' }
        Write-Output 'OK mutacion: suite rechazo auditoria sin trigger, codigo 3'
    } finally {
        DockerOk @('exec',$Contenedor,'psql','-X','-v','ON_ERROR_STOP=1','-U','clinica','-d','clinica_pruebas','-c','ALTER TABLE public.bitacora_auditoria ENABLE TRIGGER trg_bitacora_inmutable;')
    }
    SqlArchivo '03_pruebas.sql'
    # C2: runtime aislado para la dependencia Argon2 declarada por el backend.
    # No se instala nada en Windows ni se escriben contrasenas en archivos.
    DockerOk @('run','-d','--name',$contenedorPython,'--label','clinica.qa=sprint1','python:3.11-slim','sleep','600')
    $pythonCreado = $true
    DockerOk @('exec',$contenedorPython,'python','-m','pip','install','--quiet','--disable-pip-version-check','argon2-cffi==23.1.0')
    $generarHash = @'
import json, secrets
from argon2 import PasswordHasher
clave = secrets.token_urlsafe(32)
ph = PasswordHasher()
hash_clave = ph.hash(clave)
assert ph.verify(hash_clave, clave)
print(json.dumps(dict(clave=clave, hash=hash_clave)))
'@
    $jsonCredenciales = $generarHash | & docker exec -i $contenedorPython python -
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo generar/verificar Argon2id' }
    $credenciales = $jsonCredenciales | ConvertFrom-Json
    # Clave natural ocupada por una fila ajena antes de la primera carga.
    # El seed debe revertir tambien las entidades insertadas antes del choque.
    $conflictoDni = @'
BEGIN;
INSERT INTO pacientes(id_paciente,dni,nombres,apellidos,fecha_nacimiento)
OVERRIDING SYSTEM VALUE VALUES(799999,'00002001','Ajeno QA','Ficticio','2000-01-01');
\i /pruebas/02_seed.sql
'@
    $preferenciaDni = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $rechazoDni = $conflictoDni | & docker exec -i $Contenedor psql -X -q -v ON_ERROR_STOP=1 -v "seed_hash=$($credenciales.hash)" -U clinica -d clinica_pruebas 2>&1
        $codigoDni = $LASTEXITCODE
    } finally { $ErrorActionPreference = $preferenciaDni }
    if ($codigoDni -ne 3 -or ($rechazoDni -join "`n") -notmatch 'Conflicto C2 en pacientes, restriccion pacientes_dni_key') { throw 'C2 no rechazo el DNI ocupado' }
    $parcialesC2 = & docker exec $Contenedor psql -X -qAt -v ON_ERROR_STOP=1 -U clinica -d clinica_pruebas -c 'SELECT (SELECT count(*) FROM especialidades WHERE id_especialidad BETWEEN 800001 AND 800099)+(SELECT count(*) FROM medicos WHERE id_medico BETWEEN 800001 AND 800099)+(SELECT count(*) FROM usuarios WHERE id_usuario BETWEEN 800001 AND 800099)+(SELECT count(*) FROM pacientes WHERE id_paciente BETWEEN 799999 AND 800099);'
    if ($LASTEXITCODE -ne 0 -or $parcialesC2 -ne '0') { throw 'C2 dejo una carga parcial tras conflicto de DNI' }
    Write-Output 'OK C2: DNI ocupado detectado, sin carga parcial ni sobrescritura'
    DockerOk @('exec',$Contenedor,'psql','-X','-q','-v','ON_ERROR_STOP=1','-v',"seed_hash=$($credenciales.hash)",'-U','clinica','-d','clinica_pruebas','-f','/pruebas/02_seed.sql')
    # Compara el contenido completo de las diez tablas tras la segunda carga.
    # La instantanea temporal persiste entre los COMMIT del seed en esta sesion.
    $repetirSeed = @'
\set ON_ERROR_STOP on
CREATE TEMP TABLE antes_c2(tabla text, contenido jsonb);
DO $$ DECLARE t text; BEGIN
 FOR t IN SELECT tablename FROM pg_tables WHERE schemaname='public' LOOP
  EXECUTE format('INSERT INTO antes_c2 SELECT %L,coalesce(jsonb_agg(fila ORDER BY fila::text),''[]''::jsonb) FROM (SELECT to_jsonb(x) AS fila FROM public.%I x) s',t,t);
 END LOOP;
END $$;
\i /pruebas/02_seed.sql
DO $$ DECLARE t record; actual jsonb; BEGIN
 FOR t IN SELECT * FROM antes_c2 LOOP
  EXECUTE format('SELECT coalesce(jsonb_agg(fila ORDER BY fila::text),''[]''::jsonb) FROM (SELECT to_jsonb(x) AS fila FROM public.%I x) s',t.tabla) INTO actual;
  IF actual IS DISTINCT FROM t.contenido THEN RAISE EXCEPTION 'Seed no idempotente: %',t.tabla; END IF;
 END LOOP;
END $$;
\echo 'OK C2: segunda carga sin cambios en ninguna tabla'
'@
    $repetirSeed | & docker exec -i $Contenedor psql -X -q -v ON_ERROR_STOP=1 -v "seed_hash=$($credenciales.hash)" -U clinica -d clinica_pruebas
    if ($LASTEXITCODE -ne 0) { throw 'Fallo repetibilidad C2' }
    $hashes = @(& docker exec $Contenedor psql -X -qAt -v ON_ERROR_STOP=1 -U clinica -d clinica_pruebas -c 'SELECT contrasena_hash FROM usuarios WHERE id_usuario BETWEEN 800001 AND 800004 ORDER BY id_usuario;')
    if ($LASTEXITCODE -ne 0 -or $hashes.Count -ne 4) { throw 'Faltan hashes de usuarios C2' }
    $datosHash = @{ clave=$credenciales.clave; hashes=$hashes } | ConvertTo-Json -Compress
    $verificarHash = "from argon2 import PasswordHasher`ndatos = $datosHash`nassert len(datos['hashes']) == 4`nassert all(PasswordHasher().verify(h, datos['clave']) for h in datos['hashes'])`nprint('OK C2: cuatro hashes almacenados verificados con argon2-cffi 23.1.0')"
    $verificarHash | & docker exec -i $contenedorPython python -
    if ($LASTEXITCODE -ne 0) { throw 'Hashes C2 incompatibles con argon2-cffi' }
    DockerOk @('exec',$Contenedor,'psql','-X','-q','-v','ON_ERROR_STOP=1','-v','probar_seed=1','-U','clinica','-d','clinica_pruebas','-f','/pruebas/03_pruebas.sql')
    # Alteracion ajena simulada, dentro de una transaccion que debe revertirse.
    $conflictoC2 = @'
BEGIN;
UPDATE pacientes SET nombres='Contenido ajeno de prueba QA' WHERE id_paciente=800001;
\i /pruebas/02_seed.sql
'@
    $preferenciaC2 = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $rechazoC2 = $conflictoC2 | & docker exec -i $Contenedor psql -X -q -v ON_ERROR_STOP=1 -v "seed_hash=$($credenciales.hash)" -U clinica -d clinica_pruebas 2>&1
        $codigoC2 = $LASTEXITCODE
    } finally { $ErrorActionPreference = $preferenciaC2 }
    if ($codigoC2 -ne 3 -or ($rechazoC2 -join "`n") -notmatch 'Conflicto C2 en pacientes') { throw 'C2 no detecto el conflicto de contenido esperado' }
    $pacienteC2 = & docker exec $Contenedor psql -X -qAt -v ON_ERROR_STOP=1 -U clinica -d clinica_pruebas -c 'SELECT nombres FROM pacientes WHERE id_paciente=800001;'
    if ($LASTEXITCODE -ne 0 -or $pacienteC2 -ne 'Paciente Ficticio 1') { throw 'El conflicto C2 no revirtio su transaccion' }
    Write-Output 'OK C2: conflicto detectado y rollback comprobado'
    Write-Output 'OK validacion integral QA; no se modifico la base de desarrollo'
} finally {
    if ($pythonCreado) {
        DockerOk @('stop',$contenedorPython)
        DockerOk @('rm',$contenedorPython)
    }
    if ($creado) {
        # Solo el contenedor creado por esta ejecucion, sin volumen persistente.
        DockerOk @('stop',$Contenedor)
        DockerOk @('rm',$Contenedor)
    }
}
