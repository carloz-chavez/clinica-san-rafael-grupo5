param([string]$Contenedor = ('clinica-sprint1-qa-' + [guid]::NewGuid().ToString('N').Substring(0,8)))
$ErrorActionPreference = 'Stop'
if ($Contenedor -notmatch '^clinica-sprint1-qa-[a-z0-9]+$') { throw 'Nombre QA invalido' }
$creado = $false
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
    Write-Output 'OK validacion integral QA; no se modifico la base de desarrollo'
} finally {
    if ($creado) {
        # Solo el contenedor creado por esta ejecucion, sin volumen persistente.
        DockerOk @('stop',$Contenedor)
        DockerOk @('rm',$Contenedor)
    }
}
