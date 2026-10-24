$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$smoke = Join-Path $root ('backend\dist\package-smoke-' + [guid]::NewGuid().ToString('N'))
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

    $base = 'http://127.0.0.1:8010'
    $account = @{ email = 'package-smoke@example.com'; username = 'package-smoke'; full_name = 'Package QA'; password = 'package-smoke-only-password' } | ConvertTo-Json
    Invoke-RestMethod "$base/api/v1/auth/register" -Method Post -ContentType 'application/json' -Body $account | Out-Null
    $login = Invoke-RestMethod "$base/api/v1/auth/login" -Method Post -ContentType 'application/json' -Body $account
    $headers = @{ Authorization = 'Bearer ' + $login.access_token }
    $session = Invoke-RestMethod "$base/api/v1/sessions" -Method Post -Headers $headers -ContentType 'application/json' -Body '{"notes":"Packaged PDF and archive check"}'
    $report = Invoke-RestMethod "$base/api/v1/reports/sessions/$($session.id)" -Method Post -Headers $headers
    $pdf = Invoke-WebRequest "$base$($report.download_url)" -Headers $headers -UseBasicParsing
    $zip = Invoke-WebRequest "$base$($report.archive_url)" -Headers $headers -UseBasicParsing
    $excel = Invoke-WebRequest "$base$($report.excel_url)" -Headers $headers -UseBasicParsing
    if ($excel.Headers['Content-Type'] -notmatch 'spreadsheetml.sheet') { throw 'Bundled Excel report failed.' }
    if ($pdf.Headers['Content-Type'] -notmatch 'application/pdf' -or $zip.Headers['Content-Type'] -notmatch 'application/zip') {
        throw 'Bundled report or documentation archive failed.'
    }
    $diagnostics = Invoke-WebRequest "$base/api/v1/diagnostics" -Headers $headers -UseBasicParsing
    if ($diagnostics.Headers['Content-Type'] -notmatch 'application/zip') { throw 'Bundled diagnostics failed.' }

    Write-Output 'Packaged backend migration, authentication, PDF/fonts/logo, Excel, documentation ZIP and diagnostics passed.'
}
finally {
    if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
}
