$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$executable = Join-Path $root 'desktop\installer\win-unpacked\ERGoSIGHT.exe'
$profile = Join-Path $root 'desktop\installer\smoke-profile'
$electronRunAsNode = $env:ELECTRON_RUN_AS_NODE
Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
$process = Start-Process -FilePath $executable -ArgumentList "--user-data-dir=$profile" -WindowStyle Hidden -PassThru

try {
    $health = $null
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Start-Sleep -Milliseconds 500
        if ($process.HasExited) { throw "Packaged Electron exited with code $($process.ExitCode)." }
        try {
            $health = Invoke-RestMethod 'http://127.0.0.1:8000/health'
            if ($health.status -eq 'ok') { break }
        }
        catch {}
    }
    if ($health.status -ne 'ok') { throw 'Backend health check failed.' }
    Write-Output 'Packaged Electron smoke test passed.'
}
finally {
    if (-not $process.HasExited) {
        $null = $process.CloseMainWindow()
        if (-not $process.WaitForExit(5000)) { Stop-Process -Id $process.Id -Force }
    }
    if ($null -ne $electronRunAsNode) { $env:ELECTRON_RUN_AS_NODE = $electronRunAsNode }
}
