# Enciende Secrets of Style: backend (8000), motor (8001) y tunel de Cloudflare; muestra la liga para el APK.
# Lo que ya este encendido y respondiendo se deja como esta (asi la liga no cambia). Parametro -Expo: tambien Expo Go.
# -App: abre la app en su propia ventana en esta laptop. -SinTunel: no crea la liga publica.
# Sin acentos a proposito: Windows PowerShell 5.1 lee mal los archivos UTF-8 sin BOM.
param([switch]$Expo, [switch]$App, [switch]$SinTunel)

$raiz = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $raiz 'backend'
$registroTunel = Join-Path $env:TEMP 'tunel.log'
$cloudflared = @("${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe", "$env:ProgramFiles\cloudflared\cloudflared.exe") |
    Where-Object { Test-Path $_ } | Select-Object -First 1

function Test-Direccion($url) {
    try { (Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 6).StatusCode -eq 200 } catch { $false }
}

function Wait-Direccion($url, $segundos) {
    $limite = (Get-Date).AddSeconds($segundos)
    while ((Get-Date) -lt $limite) {
        if (Test-Direccion $url) { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Start-Servidor($nombre, $salud, $carpeta, $argumentos, $registro, $segundos) {
    if (Test-Direccion $salud) { Write-Host "[OK] $nombre ya estaba encendido" -ForegroundColor Green; return }
    $python = Join-Path $carpeta '.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) { Write-Host "[X] $nombre : no existe $python" -ForegroundColor Red; return }
    Write-Host "... encendiendo $nombre"
    Start-Process -FilePath $python -ArgumentList $argumentos -WorkingDirectory $carpeta -WindowStyle Hidden `
        -RedirectStandardError (Join-Path $env:TEMP $registro) -RedirectStandardOutput (Join-Path $env:TEMP "$registro.salida")
    if (Wait-Direccion $salud $segundos) { Write-Host "[OK] $nombre encendido" -ForegroundColor Green }
    else { Write-Host "[X] $nombre no respondio. Revisa $env:TEMP\$registro" -ForegroundColor Red }
}

function Get-LigaTunel {
    if (-not (Test-Path $registroTunel)) { return $null }
    $hallazgo = Select-String -Path $registroTunel -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' | Select-Object -First 1
    if ($hallazgo) { return $hallazgo.Matches[0].Value }
    return $null
}

Write-Host ''
Write-Host '  SECRETS OF STYLE - encendiendo el sistema' -ForegroundColor Cyan
Write-Host ''

# 1. MongoDB (servicio de Windows) y Ollama (la IA que reconoce prendas)
if (Get-Process mongod -ErrorAction SilentlyContinue) { Write-Host '[OK] MongoDB' -ForegroundColor Green }
else { Write-Host '[X] MongoDB no esta corriendo: abre "Servicios" e inicia MongoDB' -ForegroundColor Red }
if (Get-Process ollama -ErrorAction SilentlyContinue) { Write-Host '[OK] Ollama' -ForegroundColor Green }
elseif (Get-Command ollama -ErrorAction SilentlyContinue) {
    Start-Process ollama -ArgumentList 'serve' -WindowStyle Hidden
    Write-Host '[OK] Ollama encendido' -ForegroundColor Green
}
else { Write-Host '[!] Ollama no encontrado: no se reconoceran las prendas en las fotos' -ForegroundColor Yellow }

# 2. Backend y motor
Start-Servidor 'Backend' 'http://127.0.0.1:8000/api/salud' $backend `
    '-m uvicorn servidor.principal:aplicacion --host 0.0.0.0 --port 8000' 'backend.log' 60
Start-Servidor 'Motor (quitar fondos y probador)' 'http://127.0.0.1:8001/salud' (Join-Path $backend 'motor') `
    '-m uvicorn motor:aplicacion --host 127.0.0.1 --port 8001' 'motor.log' 120

# 3. Tunel: si el actual responde se conserva; si no, se crea uno nuevo (con otra liga)
$liga = $null
if ($SinTunel) { }
elseif (-not $cloudflared) { Write-Host '[X] No esta instalado cloudflared (winget install Cloudflare.cloudflared)' -ForegroundColor Red }
else {
    $anterior = Get-LigaTunel
    if ($anterior -and (Get-Process cloudflared -ErrorAction SilentlyContinue) -and (Test-Direccion "$anterior/api/salud")) {
        $liga = $anterior
        Write-Host '[OK] Tunel ya estaba encendido' -ForegroundColor Green
    }
    else {
        for ($intento = 1; $intento -le 3 -and -not $liga; $intento++) {
            Write-Host "... creando el tunel (intento $intento de 3)"
            Get-CimInstance Win32_Process -Filter "Name='cloudflared.exe'" |
                Where-Object { $_.CommandLine -match 'localhost:8000' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
            Start-Sleep -Seconds 1
            Remove-Item $registroTunel -ErrorAction SilentlyContinue
            Start-Process -FilePath $cloudflared -WindowStyle Hidden -ArgumentList `
                "tunnel --url http://localhost:8000 --no-autoupdate --protocol http2 --logfile `"$registroTunel`""
            $limite = (Get-Date).AddSeconds(30)
            while (-not (Get-LigaTunel) -and (Get-Date) -lt $limite) { Start-Sleep -Seconds 2 }
            $nueva = Get-LigaTunel
            if ($nueva -and (Wait-Direccion "$nueva/api/salud" 45)) { $liga = $nueva; Write-Host '[OK] Tunel encendido' -ForegroundColor Green }
        }
        if (-not $liga) { Write-Host "[X] El tunel no respondio. Revisa tu internet y $registroTunel" -ForegroundColor Red }
    }
}

# 5. La app en esta laptop: la version web ya compilada (movil\dist) en una ventana propia
if ($App) {
    $dist = Join-Path $raiz 'movil\dist'
    if (-not (Test-Path (Join-Path $dist 'index.html'))) {
        Write-Host '[X] Falta movil\dist. En la carpeta movil ejecuta: npx expo export -p web' -ForegroundColor Red
    }
    else {
        if (-not (Test-Direccion 'http://localhost:8090/')) {
            Start-Process -FilePath (Join-Path $backend '.venv\Scripts\python.exe') -WindowStyle Hidden `
                -ArgumentList "`"$(Join-Path $PSScriptRoot 'servir_app.py')`""
        }
        if (Wait-Direccion 'http://localhost:8090/' 20) {
            $edge = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe", "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe") |
                Where-Object { Test-Path $_ } | Select-Object -First 1
            if ($edge) { Start-Process $edge -ArgumentList '--app=http://localhost:8090', '--window-size=430,900' }
            else { Start-Process 'http://localhost:8090' }
            Write-Host '[OK] App abierta en esta laptop' -ForegroundColor Green
        }
        else { Write-Host '[X] No se pudo abrir la app web' -ForegroundColor Red }
    }
}

# 4. Expo Go (solo con -Expo): en su propia ventana, para ver el codigo QR
$ip = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'Wi-Fi' -ErrorAction SilentlyContinue | Select-Object -First 1).IPAddress
if ($Expo -and $ip) {
    if (Test-Direccion 'http://127.0.0.1:8081/status') { Write-Host '[OK] Expo ya estaba encendido' -ForegroundColor Green }
    else {
        $env:REACT_NATIVE_PACKAGER_HOSTNAME = $ip
        Start-Process cmd -ArgumentList '/k', 'npx expo start --lan' -WorkingDirectory (Join-Path $raiz 'movil')
        Write-Host '[OK] Expo se abre en otra ventana' -ForegroundColor Green
    }
}

Write-Host ''
if ($liga) {
    Set-Clipboard -Value $liga
    Write-Host '  LIGA PARA LA APP (ya quedo copiada al portapapeles):' -ForegroundColor Cyan
    Write-Host "  $liga" -ForegroundColor White
    Write-Host '  En la app: "Servidor - Cambiar", pegala y toca "Guardar servidor".'
}
if ($ip) { Write-Host "  En tu Wi-Fi tambien sirve: http://${ip}:8000" }
Write-Host ''
Write-Host '  Puedes cerrar esta ventana: el sistema sigue encendido. No suspendas la laptop.'
Write-Host '  Para apagarlo usa "Detener Secrets of Style".'
