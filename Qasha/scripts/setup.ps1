# Qasha first-time setup (Windows PowerShell)
# Run from project root:  .\scripts\setup.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "=== Qasha setup ===" -ForegroundColor Cyan

if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
}

Write-Host "Installing dependencies..."
& .\venv\Scripts\python.exe -m pip install --upgrade pip
& .\venv\Scripts\pip.exe install -r requirements.txt

if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example (PostgreSQL / Docker)..."
    Copy-Item ".env.example" ".env"
}

Write-Host "Starting PostgreSQL (Docker)..."
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "Could not start PostgreSQL. Open Docker Desktop and run setup again." -ForegroundColor Red
    exit 1
}

Write-Host "Running migrations..."
$env:USE_POSTGRES = "true"
& .\venv\Scripts\python.exe manage.py migrate

Write-Host "Health check..."
& .\venv\Scripts\python.exe manage.py qasha_doctor

Write-Host ""
Write-Host "Daily use (after reboot):" -ForegroundColor Green
Write-Host "  .\start.bat"
Write-Host "  or:  .\scripts\start.ps1"
Write-Host ""
Write-Host "First-time only:" -ForegroundColor Green
Write-Host "  1. .\venv\Scripts\Activate.ps1"
Write-Host "  2. python manage.py createsuperuser"
Write-Host "  3. Open http://127.0.0.1:8000/rentals/"
