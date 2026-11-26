# Apaga solo lo de Secrets of Style (backend, motor, tunel y Expo). MongoDB y Ollama no se tocan.
$patrones = 'uvicorn servidor\.principal:aplicacion', 'uvicorn motor:aplicacion', 'servir_app\.py', 'cloudflared.*localhost:8000', 'expo[\\/ ].*start --lan|expo start --lan'
$apagados = 0
Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.Name -match '^(python|cloudflared|node)\.exe$' } | ForEach-Object {
    foreach ($patron in $patrones) {
        if ($_.CommandLine -match $patron) {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            $apagados++
            break
        }
    }
}
Write-Host "Secrets of Style apagado ($apagados procesos)."
