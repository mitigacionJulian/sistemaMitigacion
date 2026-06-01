# Arranque del backend con .env y GDAL (Windows, desarrollo local)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path "..\.env")) {
    Write-Host "Falta ..\.env — copie .env.example a la raiz del proyecto." -ForegroundColor Red
    exit 1
}

& ".\.venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
