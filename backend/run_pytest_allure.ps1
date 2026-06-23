# Ejecuta pytest con salida Allure y opcionalmente abre el reporte.
#
# Uso:
#   .\run_pytest_allure.ps1              # solo genera allure-results/
#   .\run_pytest_allure.ps1 -Serve       # genera y abre en el navegador
#   .\run_pytest_allure.ps1 -Static      # genera allure-report/index.html
#   .\run_pytest_allure.ps1 dashboard/tests/test_modelos_arima.py
#
# Requisitos: pip install -r requirements.txt
# Para ver HTML: Node.js (npx) + Java 8+ en PATH para allure-commandline.

param(
    [switch]$Serve,
    [switch]$Static,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArgs
)

$ErrorActionPreference = "Stop"
$BackendRoot = $PSScriptRoot
$ResultsDir = Join-Path $BackendRoot "allure-results"
$ReportDir = Join-Path $BackendRoot "allure-report"

Set-Location $BackendRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Error "No se encontró .venv en backend/. Cree el entorno e instale requirements.txt."
}

Write-Host "pytest → Allure: $ResultsDir" -ForegroundColor Cyan
$pytestCmd = @(".\.venv\Scripts\python.exe", "-m", "pytest", "--alluredir=$ResultsDir", "--clean-alluredir") + $PytestArgs
& $pytestCmd[0] $pytestCmd[1..($pytestCmd.Length - 1)]
$pytestExit = $LASTEXITCODE

if ($pytestExit -ne 0) {
    Write-Host "pytest código $pytestExit (pueden existir fallos; revise el reporte)." -ForegroundColor Yellow
}

function Invoke-AllureCli {
    param([string[]]$AllureArgs)
    if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
        Write-Error "npx no está en PATH. Instale Node.js o use solo la carpeta allure-results con otra máquina."
    }
    Set-Location $BackendRoot
    npx --yes allure-commandline @AllureArgs
}

if ($Static) {
    Write-Host "Generando reporte estático en $ReportDir ..." -ForegroundColor Green
    Invoke-AllureCli @("generate", "allure-results", "-o", "allure-report", "--clean")
    Write-Host "Abra: $ReportDir\index.html"
}
elseif ($Serve) {
    Write-Host "Abriendo servidor Allure (Ctrl+C para cerrar) ..." -ForegroundColor Green
    Invoke-AllureCli @("serve", "allure-results")
}
else {
    Write-Host ""
    Write-Host "Reporte generado. Para visualizar:" -ForegroundColor Green
    Write-Host "  .\run_pytest_allure.ps1 -Serve"
    Write-Host "  .\run_pytest_allure.ps1 -Static   → allure-report\index.html"
}

exit $pytestExit
