param([string]$Contenedor = 'clinica-sprint1-qa')
$ErrorActionPreference = 'Stop'
if ($Contenedor -notmatch '^clinica-sprint1-qa[-a-z0-9]*$') { throw 'Solo contenedores QA de esta suite' }
$etiquetas = & docker inspect --format '{{json .Config.Labels}}' $Contenedor
$etiqueta = ($etiquetas | ConvertFrom-Json).'clinica.qa'
if ($LASTEXITCODE -ne 0 -or $etiqueta -ne 'sprint1') { throw 'Falta etiqueta clinica.qa=sprint1' }
function Consultar([string]$Sql) {
    $salida = & docker exec $Contenedor psql -X -qAt -v ON_ERROR_STOP=1 -U clinica -d clinica_pruebas -c $Sql 2>&1
    if ($LASTEXITCODE -ne 0) { throw ($salida -join "`n") }
    return ($salida -join "`n").Trim()
}
function Abrir {
    $inicio = New-Object Diagnostics.ProcessStartInfo
    $inicio.FileName = 'docker'
    $inicio.Arguments = "exec -i $Contenedor psql -X -qAt -v ON_ERROR_STOP=1 -v VERBOSITY=verbose -U clinica -d clinica_pruebas"
    $inicio.UseShellExecute = $false
    $inicio.CreateNoWindow = $true
    $inicio.RedirectStandardInput = $true
    $inicio.RedirectStandardOutput = $true
    $inicio.RedirectStandardError = $true
    $proceso = New-Object Diagnostics.Process
    $proceso.StartInfo = $inicio
    [void]$proceso.Start()
    return $proceso
}
function Enviar($Proceso,[string]$Sql) { $Proceso.StandardInput.WriteLine($Sql); $Proceso.StandardInput.Flush() }
function EsperarMarca($Proceso) {
    $lectura = $Proceso.StandardOutput.ReadLineAsync()
    if (-not $lectura.Wait(15000) -or $lectura.Result -ne 'LISTO') { throw 'No llego la barrera LISTO' }
}
function Pareja([string]$Nombre,[string]$Primera,[string]$Segunda,[string]$Estado,[string]$Invariante) {
    $a = Abrir
    $b = Abrir
    try {
        Enviar $a "BEGIN; SET LOCAL statement_timeout='20s'; $Primera"
        Enviar $a '\echo LISTO'
        EsperarMarca $a
        Enviar $b "SET application_name='clinica_qa_b'; SET statement_timeout='20s'; BEGIN; $Segunda COMMIT;"
        Enviar $b '\q'
        $reloj = [Diagnostics.Stopwatch]::StartNew()
        do {
            $espera = Consultar "SELECT count(*) FROM pg_stat_activity WHERE application_name='clinica_qa_b' AND wait_event_type='Lock';"
            if ($espera -eq '1') { break }
            if ($b.HasExited -or $reloj.Elapsed.TotalSeconds -gt 10) { throw "${Nombre}: segunda sesion no espero bloqueo" }
            Start-Sleep -Milliseconds 50
        } while ($true)
        Enviar $a 'COMMIT;'
        Enviar $a '\q'
        if (-not $a.WaitForExit(15000) -or $a.ExitCode -ne 0) { throw "Fallo primera sesion: $($a.StandardError.ReadToEnd())" }
        if (-not $b.WaitForExit(15000)) { throw 'Timeout segunda sesion' }
        $errorSql = $b.StandardError.ReadToEnd()
        if ($b.ExitCode -eq 0 -or $errorSql -notmatch $Estado) { throw "${Nombre}: rechazo incorrecto: $errorSql" }
        if ((Consultar $Invariante) -ne 't') { throw "${Nombre}: invariante final violado" }
        Write-Output "OK $Nombre ($Estado; bloqueo observado y estado final comprobado)"
    } finally {
        foreach ($p in @($a,$b)) {
            if (-not $p.HasExited) { $p.StandardInput.Close(); [void]$p.WaitForExit(25000) }
            $p.Dispose()
        }
    }
}
if ((Consultar 'SELECT (SELECT count(*) FROM especialidades)+(SELECT count(*) FROM pacientes);') -ne '0') { throw 'QA no esta vacia; utilizar un contenedor nuevo' }
Consultar @'
INSERT INTO especialidades(id_especialidad,nombre) OVERRIDING SYSTEM VALUE VALUES(920001,'Concurrencia ficticia');
INSERT INTO medicos(id_medico,nombres,apellidos,numero_colegiatura,id_especialidad) OVERRIDING SYSTEM VALUE
 VALUES(920001,'QA','Uno','QA-C1',920001),(920002,'QA','Dos','QA-C2',920001);
INSERT INTO pacientes(id_paciente,dni,nombres,apellidos,fecha_nacimiento) OVERRIDING SYSTEM VALUE
 VALUES(920001,'99000011','QA','Uno','2000-01-01'),(920002,'99000012','QA','Dos','2000-01-01');
INSERT INTO horarios_medicos(id_horario,id_medico,dia_semana,hora_inicio,hora_fin) OVERRIDING SYSTEM VALUE
 VALUES(920001,920001,extract(isodow from current_date+14),'08:00','18:00'),(920002,920002,extract(isodow from current_date+14),'08:00','18:00');
'@ | Out-Null
Pareja 'turno medico' "INSERT INTO citas(id_paciente,id_medico,fecha,hora,motivo) VALUES(920001,920001,current_date+14,'09:00','QA');" "INSERT INTO citas(id_paciente,id_medico,fecha,hora,motivo) VALUES(920002,920001,current_date+14,'09:00','QA');" '23505' "SELECT count(*)=1 FROM citas WHERE hora='09:00';"
Pareja 'turno paciente entre medicos' "INSERT INTO citas(id_paciente,id_medico,fecha,hora,motivo) VALUES(920001,920001,current_date+14,'10:00','QA');" "INSERT INTO citas(id_paciente,id_medico,fecha,hora,motivo) VALUES(920001,920002,current_date+14,'10:00','QA');" '23505' "SELECT count(*)=1 FROM citas WHERE hora='10:00';"
Pareja 'cita antes de reducir horario' "INSERT INTO citas(id_paciente,id_medico,fecha,hora,motivo) VALUES(920002,920001,current_date+14,'17:00','QA');" "UPDATE horarios_medicos SET hora_fin='17:00' WHERE id_horario=920001;" 'P0001' "SELECT hora_fin='18:00' FROM horarios_medicos WHERE id_horario=920001;"
Pareja 'cita antes de desactivar medico' "INSERT INTO citas(id_paciente,id_medico,fecha,hora,motivo) VALUES(920002,920002,current_date+14,'11:00','QA');" 'UPDATE medicos SET activo=false WHERE id_medico=920002;' 'P0001' 'SELECT activo FROM medicos WHERE id_medico=920002;'
Pareja 'horario reducido antes de cita' "UPDATE horarios_medicos SET hora_inicio='08:30' WHERE id_horario=920001;" "INSERT INTO citas(id_paciente,id_medico,fecha,hora,motivo) VALUES(920002,920001,current_date+14,'08:00','QA');" 'P0001' "SELECT count(*)=0 FROM citas WHERE hora='08:00';"
$rr = Abrir
try {
    Enviar $rr 'BEGIN ISOLATION LEVEL REPEATABLE READ; SELECT public.bloquear_agenda_medico(920001);'
    Enviar $rr '\q'
    if (-not $rr.WaitForExit(15000)) { throw 'Timeout RR' }
    $errorRr = $rr.StandardError.ReadToEnd()
    if ($rr.ExitCode -eq 0 -or $errorRr -notmatch '0A000') { throw "RR no fue rechazado: $errorRr" }
    Write-Output 'OK REPEATABLE READ rechazado (0A000)'
} finally { $rr.Dispose() }
Write-Output '6 pruebas concurrentes/aislamiento aprobadas; fixtures conservadas solo en QA efimero.'
