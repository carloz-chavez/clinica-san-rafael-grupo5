param([switch]$SoloVerificar)
$ErrorActionPreference = 'Stop'
$raizEquipo = (Resolve-Path "$PSScriptRoot/..").Path
$pythonEquipo = $null
Push-Location $raizEquipo

function DockerEquipo([string[]]$Argumentos) {
    $salida = & docker @Argumentos
    if ($LASTEXITCODE -ne 0) { throw 'Docker no pudo completar la operacion. Revisar Docker Desktop y el servicio postgres.' }
    return $salida
}

function LeerOculto([string]$Mensaje) {
    $seguro = Read-Host $Mensaje -AsSecureString
    $puntero = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($seguro)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($puntero) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($puntero); $seguro.Dispose() }
}

function ValorEnv([string]$Texto, [string]$Nombre) {
    $coincidencia = [regex]::Match($Texto, "(?m)^$Nombre\s*=\s*([^\r\n]*)")
    return $coincidencia.Groups[1].Value.Trim().Trim('"').Trim("'")
}

function ValidarConexionEquipo([string]$Texto) {
    try { $uri = [uri](ValorEnv $Texto 'BASE_DATOS_URL') }
    catch { throw 'La conexion no es una URL PostgreSQL valida; revisa el valor sin publicarlo.' }
    if ($uri.Scheme -notin @('postgresql','postgres') -or $uri.Host -notin @('localhost','127.0.0.1') -or
        $uri.Port -ne 5433 -or $uri.AbsolutePath -ne '/clinica_san_rafael' -or $uri.Query -or $uri.Fragment) {
        throw 'Destino rechazado. Usa localhost:5433/clinica_san_rafael sin parametros adicionales.'
    }
}

function NuevaClaveEquipo {
    $clave = LeerOculto 'Clave JWT local (Enter para generar una clave aleatoria)'
    if (-not $clave) {
        $bytes = New-Object byte[] 48
        $generador = [Security.Cryptography.RandomNumberGenerator]::Create()
        try { $generador.GetBytes($bytes) } finally { $generador.Dispose() }
        $clave = [Convert]::ToBase64String($bytes)
    }
    if ($clave.Length -lt 32 -or $clave -match '[\r\n#''"\s]') {
        throw 'Usa una clave JWT de al menos 32 caracteres, sin espacios, comillas ni saltos de linea.'
    }
    return $clave
}

try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Instala Docker Desktop y vuelve a ejecutar este comando.' }
    DockerEquipo @('info','--format','{{.ServerVersion}}') | Out-Null
    DockerEquipo @('compose','version','--short') | Out-Null
    $contextoEquipo = DockerEquipo @('context','inspect') | ConvertFrom-Json
    $endpointEquipo = $contextoEquipo.Endpoints.docker.Host
    if ($endpointEquipo -notmatch '^(npipe:|unix:|tcp://(localhost|127\.0\.0\.1):)') {
        throw 'El contexto Docker no es local. Selecciona Docker Desktop antes de continuar.'
    }
    $rutaEnvEquipo = Join-Path $raizEquipo '.env'
    if (-not (Test-Path -LiteralPath $rutaEnvEquipo)) {
        if ($SoloVerificar) { throw 'Falta .env. Ejecuta el comando sin -SoloVerificar para prepararlo.' }
        $textoEquipo = [IO.File]::ReadAllText((Join-Path $raizEquipo '.env.example'))
        $conexionEquipo = LeerOculto 'Conexion local PostgreSQL (Enter para usar la de .env.example)'
        if ($conexionEquipo) {
            if ($conexionEquipo -match '[\r\n]') { throw 'La conexion debe ocupar una sola linea.' }
            $textoEquipo = [regex]::Replace($textoEquipo,'(?m)^BASE_DATOS_URL=.*$', { param($m) 'BASE_DATOS_URL=' + $conexionEquipo })
        }
        $claveEquipo = NuevaClaveEquipo
        $textoEquipo = [regex]::Replace($textoEquipo,'(?m)^CLAVE_SECRETA_JWT=.*$', { param($m) 'CLAVE_SECRETA_JWT=' + $claveEquipo })
        $textoEquipo = [regex]::Replace($textoEquipo,'(?m)^AUTENTICACION_SIMULADA=.*$', 'AUTENTICACION_SIMULADA=false')
        ValidarConexionEquipo $textoEquipo
        # CreateNew evita sobrescribir un archivo creado simultaneamente por otro proceso.
        $archivoEquipo = [IO.File]::Open($rutaEnvEquipo,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
        try { $datosEquipo = [Text.Encoding]::UTF8.GetBytes($textoEquipo); $archivoEquipo.Write($datosEquipo,0,$datosEquipo.Length) }
        finally { $archivoEquipo.Dispose(); $claveEquipo=$null; $conexionEquipo=$null }
    }
    $textoEquipo = [IO.File]::ReadAllText($rutaEnvEquipo)
    ValidarConexionEquipo $textoEquipo
    $jwtEquipo = ValorEnv $textoEquipo 'CLAVE_SECRETA_JWT'
    if (-not $jwtEquipo -or $jwtEquipo -eq 'cambiar-por-un-valor-largo-y-aleatorio') {
        if ($SoloVerificar) { throw 'Falta una clave JWT propia. Ejecuta sin -SoloVerificar para configurarla.' }
        $claveEquipo = NuevaClaveEquipo
        if ($textoEquipo -match '(?m)^CLAVE_SECRETA_JWT\s*=') {
            $textoEquipo = [regex]::Replace($textoEquipo,'(?m)^CLAVE_SECRETA_JWT=.*$', { param($m) 'CLAVE_SECRETA_JWT=' + $claveEquipo })
        } else { $textoEquipo += "`nCLAVE_SECRETA_JWT=$claveEquipo`n" }
        [IO.File]::WriteAllText($rutaEnvEquipo,$textoEquipo,[Text.UTF8Encoding]::new($false))
        $claveEquipo=$null
    }
    $jwtEquipo=$null; $textoEquipo=$null
    $rutaClavesEquipo = Join-Path $raizEquipo 'db/desarrollo/cuentas_ficticias.json'
    if (-not (Test-Path -LiteralPath $rutaClavesEquipo)) {
        if ($SoloVerificar) { throw 'Falta la configuracion local de cuentas. Ejecuta sin -SoloVerificar o copia el archivo compartido por el equipo.' }
        $plantillaEquipo = Get-Content -Encoding UTF8 -Raw (Join-Path $raizEquipo 'db/desarrollo/cuentas_ficticias.example.json') | ConvertFrom-Json
        foreach ($propiedadEquipo in $plantillaEquipo.claves.PSObject.Properties) {
            $claveCuentaEquipo = LeerOculto ('Clave academica acordada para ' + $propiedadEquipo.Name)
            $confirmacionEquipo = LeerOculto 'Repite la clave'
            if (-not $claveCuentaEquipo -or $claveCuentaEquipo -cne $confirmacionEquipo) {
                throw 'Las claves estan vacias o no coinciden. No se preparo la configuracion de cuentas.'
            }
            $propiedadEquipo.Value = $claveCuentaEquipo
        }
        $datosClavesEquipo = [Text.Encoding]::UTF8.GetBytes(($plantillaEquipo | ConvertTo-Json -Depth 4))
        $archivoClavesEquipo = [IO.File]::Open($rutaClavesEquipo,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
        try { $archivoClavesEquipo.Write($datosClavesEquipo,0,$datosClavesEquipo.Length) }
        finally { $archivoClavesEquipo.Dispose() }
        $claveCuentaEquipo=$null; $confirmacionEquipo=$null; $plantillaEquipo=$null; $datosClavesEquipo=$null
    }
    $idPostgresEquipo = DockerEquipo @('compose','ps','-a','-q','postgres')
    if (-not $idPostgresEquipo) {
        if ($SoloVerificar) { throw 'PostgreSQL no esta preparado; ejecuta el comando sin -SoloVerificar.' }
        DockerEquipo @('compose','up','-d','--no-deps','postgres') | Out-Null
        $idPostgresEquipo = DockerEquipo @('compose','ps','-a','-q','postgres')
    } else {
        $estadoEquipo = DockerEquipo @('inspect','--format','{{.State.Status}}',$idPostgresEquipo)
        if ($estadoEquipo -eq 'exited' -or $estadoEquipo -eq 'created') {
            if ($SoloVerificar) { throw 'PostgreSQL esta detenido.' }
            DockerEquipo @('start',$idPostgresEquipo) | Out-Null
        } elseif ($estadoEquipo -ne 'running') { throw 'El contenedor PostgreSQL tiene un estado inesperado.' }
    }
    $puertoEquipo = DockerEquipo @('port',$idPostgresEquipo,'5432')
    if ($puertoEquipo.Trim() -ne '127.0.0.1:5433') { throw 'El puerto publicado no coincide con la base local autorizada.' }
    $listoEquipo=$false
    for ($intentoEquipo=0; $intentoEquipo -lt 60; $intentoEquipo++) {
        $saludEquipo = DockerEquipo @('inspect','--format','{{.State.Health.Status}}',$idPostgresEquipo)
        if ($saludEquipo -eq 'healthy') {
            $pidPostgresEquipo = DockerEquipo @('exec',$idPostgresEquipo,'sh','-c',
                'head -1 /var/lib/postgresql/data/postmaster.pid 2>/dev/null || true')
            if ($pidPostgresEquipo -eq '1') { $listoEquipo=$true; break }
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $listoEquipo) { throw 'PostgreSQL no esta saludable. Revisa docker compose logs postgres; no borres volumenes.' }
    $pythonEquipo = 'clinica-equipo-' + [guid]::NewGuid().ToString('N').Substring(0,8)
    DockerEquipo @('run','-d','--name',$pythonEquipo,'--network',"container:$idPostgresEquipo",
        '--mount',"type=bind,source=$raizEquipo,target=/repo,readonly",'-w','/repo/backend',
        '-e','PYTHONDONTWRITEBYTECODE=1','python:3.11-slim','sleep','1800') | Out-Null
    DockerEquipo @('exec',$pythonEquipo,'pip','install','--disable-pip-version-check','--timeout','20','--retries','1','-q','-r','/repo/backend/requirements.txt') | Out-Null
    $baseComandoEquipo = @('exec',$pythonEquipo,'python','-m','administracion.preparar_equipo')
    $resultadoEquipo = DockerEquipo ($baseComandoEquipo + @('inspeccionar','--puerto-contenedor')) | ConvertFrom-Json
    $restablecerEquipo = @()
    if ($resultadoEquipo.estado -eq 'configurada') {
        Write-Output 'Las siete cuentas C2 ya estan configuradas. No se modificaron datos ni hashes.'
    } elseif ($SoloVerificar) {
        Write-Output ('Estado detectado: ' + $resultadoEquipo.estado + '. No se realizaron cambios.')
    } else {
        if ($resultadoEquipo.estado -ne 'vacia') {
            Write-Output 'Las claves existentes necesitan restablecerse. Se creara un respaldo completo antes de cambiarlas.'
            if ((Read-Host 'Escribe RESTABLECER para autorizar el cambio de las siete claves') -cne 'RESTABLECER') {
                throw 'Restablecimiento cancelado; no se modificaron cuentas.'
            }
            New-Item -ItemType Directory -Force (Join-Path $raizEquipo 'respaldos') | Out-Null
            $nombreRespaldoEquipo = 'equipo-' + [guid]::NewGuid().ToString('N')
            $rutaRespaldoEquipo = Join-Path $raizEquipo "respaldos/$nombreRespaldoEquipo.dump"
            DockerEquipo @('exec',$idPostgresEquipo,'pg_dump','-U','clinica','-d','clinica_san_rafael','-Fc','-f',"/tmp/$nombreRespaldoEquipo.dump") | Out-Null
            DockerEquipo @('cp',"${idPostgresEquipo}:/tmp/$nombreRespaldoEquipo.dump",$rutaRespaldoEquipo) | Out-Null
            $hashOrigenEquipo = DockerEquipo @('exec',$idPostgresEquipo,'sha256sum',"/tmp/$nombreRespaldoEquipo.dump")
            $hashCopiaEquipo = (Get-FileHash -Algorithm SHA256 -LiteralPath $rutaRespaldoEquipo).Hash
            if (($hashOrigenEquipo -split '\s+')[0].ToUpper() -ne $hashCopiaEquipo) {
                throw 'La copia del respaldo no coincide con el origen; no se cambiaran claves.'
            }
            DockerEquipo @('exec',$idPostgresEquipo,'pg_restore','--list',"/tmp/$nombreRespaldoEquipo.dump") | Out-Null
            $hashCopiaEquipo |
                Set-Content -Encoding UTF8 ([IO.Path]::ChangeExtension($rutaRespaldoEquipo,'.sha256'))
            Write-Output ('Respaldo verificado: respaldos/' + $nombreRespaldoEquipo + '.dump')
            $restablecerEquipo = @('--restablecer','--respaldo',"/repo/respaldos/$nombreRespaldoEquipo.dump")
        }
        $aplicadoEquipo = DockerEquipo ($baseComandoEquipo + @('aplicar','--puerto-contenedor') + $restablecerEquipo) | ConvertFrom-Json
        if ($aplicadoEquipo.estado -ne 'configurada') { throw 'La verificacion final no termino correctamente.' }
        Write-Output 'Siete cuentas activas, cinco relaciones medicas y siete claves verificadas. Datos clinicos conservados.'
    }
    if ($resultadoEquipo.simulacion) { Write-Output 'Tu .env conserva el modo simulado. Cambia AUTENTICACION_SIMULADA=false cuando quieras usar login real.' }
    Write-Output 'PostgreSQL preparado. El backend y el frontend no se iniciaron.'
} finally {
    if ($pythonEquipo) { & docker rm -f $pythonEquipo | Out-Null }
    Pop-Location
}
