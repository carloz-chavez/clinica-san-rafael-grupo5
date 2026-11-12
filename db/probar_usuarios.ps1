# Pruebas aisladas: no monta volumenes ni se conecta a PostgreSQL de desarrollo.
$ErrorActionPreference = 'Stop'
$nombreQa = 'clinica-usuarios-qa-' + [guid]::NewGuid().ToString('N').Substring(0,8)
$nombrePython = "$nombreQa-python"
$raizProyecto = (Resolve-Path "$PSScriptRoot/..").Path
$qaCreado = $false
$pythonCreado = $false
function DockerOk([string[]]$Argumentos) {
    & docker @Argumentos
    if ($LASTEXITCODE -ne 0) { throw "Docker fallo: $($Argumentos[0])" }
}
try {
    DockerOk @('run','-d','--name',$nombreQa,'--label','clinica.qa=usuarios',
        '--mount','type=tmpfs,destination=/var/lib/postgresql/data',
        '-e','POSTGRES_HOST_AUTH_METHOD=trust','-e','POSTGRES_USER=clinica',
        '-e','POSTGRES_DB=clinica_usuarios_qa','postgres:16')
    $qaCreado = $true
    $listo = $false
    for ($intento=0; $intento -lt 60; $intento++) {
        $ErrorActionPreference = 'Continue'
        $pidQa = & docker exec $nombreQa head -1 /var/lib/postgresql/data/postmaster.pid 2>$null
        $ErrorActionPreference = 'Stop'
        if ($LASTEXITCODE -eq 0 -and $pidQa -eq '1') { $listo=$true; break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $listo) { throw 'PostgreSQL QA no disponible' }
    DockerOk @('run','-d','--name',$nombrePython,'--network',"container:$nombreQa",
        '--mount',"type=bind,source=$raizProyecto,target=/repo,readonly",
        '-w','/repo/backend','-e','AUTENTICACION_SIMULADA=false','-e','ENTORNO=pruebas',
        '-e','BASE_DATOS_URL=postgresql://clinica@localhost:5432/clinica_usuarios_qa',
        '-e',('CLAVE_SECRETA_JWT=' + [guid]::NewGuid().ToString('N')),
        '-e','USUARIOS_BASE_DATOS_QA=postgresql://clinica@localhost:5432/clinica_usuarios_qa',
        '-e','C3_BASE_DATOS_QA=postgresql://clinica@localhost:5432/clinica_c3_qa',
        '-e','FLUJO_BASE_DATOS_QA=postgresql://clinica@localhost:5432/clinica_flujo_qa',
        'python:3.11-slim','sleep','900')
    $pythonCreado=$true
    DockerOk @('exec',$nombrePython,'pip','install','--disable-pip-version-check','-q',
        '-r','/repo/backend/requirements.txt','ruff')
    $hashQa = & docker exec $nombrePython python -c 'import secrets; from argon2 import PasswordHasher; print(PasswordHasher().hash(secrets.token_urlsafe(24)))'
    if ($LASTEXITCODE -ne 0) { throw 'No se genero hash QA' }
    DockerOk @('cp',"$PSScriptRoot/.","${nombreQa}:/pruebas")
    foreach ($archivo in @('01_esquema.sql','02_permisos.sql')) {
        DockerOk @('exec',$nombreQa,'psql','-X','-q','-v','ON_ERROR_STOP=1','-U','clinica',
            '-d','clinica_usuarios_qa','-f',"/pruebas/$archivo")
    }
    foreach ($baseQa in @('clinica_c3_qa','clinica_flujo_qa')) {
        DockerOk @('exec',$nombreQa,'createdb','-U','clinica',$baseQa)
        foreach ($archivo in @('01_esquema.sql','02_permisos.sql')) {
            DockerOk @('exec',$nombreQa,'psql','-X','-q','-v','ON_ERROR_STOP=1','-U','clinica',
                '-d',$baseQa,'-f',"/pruebas/$archivo")
        }
    }
    DockerOk @('exec',$nombreQa,'psql','-X','-q','-v','ON_ERROR_STOP=1','-v',"seed_hash=$hashQa",'-U','clinica',
        '-d','clinica_usuarios_qa','-f','/pruebas/02_seed.sql')
    DockerOk @('exec',$nombrePython,'ruff','check','--no-cache','--select','E,F,I','--ignore','E501',
        'administracion','pruebas/prueba_configurar_usuarios.py','pruebas/prueba_nucleo.py',
        'pruebas/prueba_flujo_autenticado.py',
        'aplicacion/nucleo/configuracion.py','aplicacion/nucleo/dependencias.py',
        'aplicacion/m1_hce/autenticacion/servicio.py')
    $directorioEvidencia = Join-Path $raizProyecto 'reportes_qa'
    New-Item -ItemType Directory -Force $directorioEvidencia | Out-Null
    DockerOk @('exec',$nombrePython,'python','-m','pytest','-q','--tb=short',
        '--junitxml=/tmp/pruebas.xml','-p','no:cacheprovider') |
        Tee-Object -FilePath (Join-Path $directorioEvidencia 'pruebas.txt')
    DockerOk @('cp',"${nombrePython}:/tmp/pruebas.xml",(Join-Path $directorioEvidencia 'pruebas.xml'))
} finally {
    # Solo contenedores efimeros creados por esta ejecucion; sin volumenes persistentes.
    if ($pythonCreado) { & docker rm -f $nombrePython | Out-Null }
    if ($qaCreado) { & docker rm -f $nombreQa | Out-Null }
}
