$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$smoke = Join-Path $root 'backend\dist\package-smoke'
$executable = Join-Path $root 'backend\dist\ergosight-backend\ergosight-backend.exe'

if (Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 8010 is already in use.'
}

New-Item -ItemType Directory -Force -Path $smoke | Out-Null
$env:DATABASE_URL = 'sqlite:///' + ((Join-Path $smoke 'ergosight.sqlite3') -replace '\\', '/')
$env:MEDIA_ROOT = Join-Path $smoke 'media'
$env:JWT_SECRET_KEY = 'package-smoke-test-secret-that-is-not-used-in-production'
$env:PORT = '8010'
$process = Start-Process -FilePath $executable -WorkingDirectory $smoke -WindowStyle Hidden -PassThru

try {
    $health = $null
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            $health = Invoke-RestMethod 'http://127.0.0.1:8010/health'
            if ($health.status -eq 'ok') { break }
        }
        catch {}
    }
    if ($health.status -ne 'ok') { throw 'Bundled backend did not become healthy.' }

    $schema = Invoke-RestMethod 'http://127.0.0.1:8010/openapi.json'
    if ($schema.info.title -ne 'ERGoSIGHT Backend') { throw 'Unexpected backend identity.' }
    if (-not (Test-Path (Join-Path $smoke 'ergosight.sqlite3'))) { throw 'Database was not created.' }

    Write-Output 'Packaged backend smoke test passed.'
}
finally {
    if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
}
