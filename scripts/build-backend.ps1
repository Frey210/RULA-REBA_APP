$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$python = Join-Path $backend '.venv\Scripts\python.exe'
$alembic = Join-Path $backend 'alembic'
$alembicIni = Join-Path $backend 'alembic.ini'
$entrypoint = Join-Path $backend 'app\standalone.py'
$icon = Join-Path $root 'desktop\build\icon.ico'
$assets = Join-Path $backend 'assets'

if (-not (Test-Path -LiteralPath $python)) {
    throw "Backend virtual environment not found at $python"
}

Push-Location $backend
try {
    & $python -m PyInstaller `
        --noconfirm `
        --clean `
        --onedir `
        --name ergosight-backend `
        --icon $icon `
        --add-data "$alembic;alembic" `
        --add-data "$alembicIni;." `
        --add-data "$assets;assets" `
        --collect-data reportlab `
        --collect-all uvicorn `
        --hidden-import passlib.handlers.bcrypt `
        --hidden-import app.db.base `
        --distpath dist `
        --workpath build\pyinstaller `
        --specpath build `
        $entrypoint
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
