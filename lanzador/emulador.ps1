# Abre Secrets of Style en el emulador de Android de esta laptop: enciende backend y motor, arranca el telefono virtual
# "SecretsOfStyle", conecta su localhost:8000 con el de la laptop (adb reverse), instala la app y la abre.
# Sin acentos a proposito: Windows PowerShell 5.1 lee mal los archivos UTF-8 sin BOM.
$raiz = Split-Path -Parent $PSScriptRoot
$sdk = Join-Path $env:LOCALAPPDATA 'Android\Sdk'
$adb = Join-Path $sdk 'platform-tools\adb.exe'
$emulador = Join-Path $sdk 'emulator\emulator.exe'
$apk = Join-Path $raiz 'apk\SecretsOfStyle-emulador.apk'
$avd = 'SecretsOfStyle'
$paquete = 'com.secretsofstyle.app'

foreach ($archivo in $adb, $emulador, $apk) {
    if (-not (Test-Path $archivo)) { Write-Host "[X] No existe $archivo" -ForegroundColor Red; exit 1 }
}

& (Join-Path $PSScriptRoot 'iniciar.ps1') -SinTunel

# El numero de serie (emulator-55xx) de NUESTRO telefono virtual: puede haber otros emuladores abiertos
function Get-Serie {
    foreach ($linea in (& $adb devices)) {
        if ($linea -match '^(emulator-\d+)\s') {
            $serie = $Matches[1]
            $nombre = (& $adb -s $serie emu avd name 2>$null | Select-Object -First 1)
            if ("$nombre".Trim() -eq $avd) { return $serie }
        }
    }
    return $null
}

& $adb start-server 2>$null | Out-Null
$serie = Get-Serie
if (-not $serie) {
    Write-Host '... arrancando el telefono virtual (la primera vez tarda un par de minutos)'
    Start-Process -FilePath $emulador -ArgumentList '-avd', $avd, '-no-boot-anim'
    $limite = (Get-Date).AddMinutes(5)
    while (-not $serie -and (Get-Date) -lt $limite) { Start-Sleep -Seconds 3; $serie = Get-Serie }
}
if (-not $serie) { Write-Host '[X] El emulador no arranco' -ForegroundColor Red; exit 1 }

$limite = (Get-Date).AddMinutes(5)
while ("$(& $adb -s $serie shell getprop sys.boot_completed 2>$null)".Trim() -ne '1') {
    if ((Get-Date) -gt $limite) { Write-Host '[X] Android no termino de arrancar' -ForegroundColor Red; exit 1 }
    Start-Sleep -Seconds 3
}
Write-Host "[OK] Telefono virtual listo ($serie)" -ForegroundColor Green

# localhost:8000 dentro del emulador = el backend de la laptop (la app no necesita liga ni tunel)
& $adb -s $serie reverse tcp:8000 tcp:8000 | Out-Null

# Se instala la primera vez y cuando el APK es mas nuevo que el instalado la ultima vez
$marca = Join-Path $raiz 'apk\.emulador-instalado'
$instalada = (& $adb -s $serie shell pm list packages $paquete) -match $paquete
if (-not $instalada -or -not (Test-Path $marca) -or (Get-Item $apk).LastWriteTime -gt (Get-Item $marca).LastWriteTime) {
    Write-Host '... instalando la app'
    & $adb -s $serie install -r $apk
    if ($LASTEXITCODE -ne 0) { Write-Host '[X] No se pudo instalar la app' -ForegroundColor Red; exit 1 }
    Set-Content -Path $marca -Value (Get-Date)
}

& $adb -s $serie shell monkey -p $paquete -c android.intent.category.LAUNCHER 1 2>$null | Out-Null
Write-Host '[OK] Secrets of Style abierta en el emulador' -ForegroundColor Green
