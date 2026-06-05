# Start Qasha after reboot (starts Postgres, waits until ready, runs dev server)
# Run from project root:  .\scripts\start.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

function Get-Python {
    if (Test-Path "venv\Scripts\python.exe") {
        return ".\venv\Scripts\python.exe"
    }
    return "python"
}

function Wait-DockerReady {
    param([int]$MaxSeconds = 120)

    for ($i = 0; $i -lt $MaxSeconds; $i += 2) {
        docker info 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
        if ($i -eq 0) {
            Write-Host ""
            Write-Host "Docker is not running yet." -ForegroundColor Yellow
            Write-Host "Open Docker Desktop and wait for it to finish starting..." -ForegroundColor Yellow
            Write-Host ""
        }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Wait-PostgresHealthy {
    param([int]$MaxSeconds = 90)

    for ($i = 0; $i -lt $MaxSeconds; $i += 2) {
        $status = docker inspect --format='{{.State.Health.Status}}' qasha-postgres 2>$null
        if ($status -eq "healthy") {
            return $true
        }
        if ($i -eq 0) {
            Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Cyan
        }
        Start-Sleep -Seconds 2
    }
    return $false
}

Write-Host "=== Starting Qasha ===" -ForegroundColor Cyan

if (-not (Wait-DockerReady)) {
    Write-Host "Docker did not start in time. Open Docker Desktop, then run this script again." -ForegroundColor Red
    exit 1
}

Write-Host "Starting PostgreSQL container..."
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "Could not start PostgreSQL. Check Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

if (-not (Wait-PostgresHealthy)) {
    Write-Host "PostgreSQL did not become healthy in time. Try: docker compose logs db" -ForegroundColor Red
    exit 1
}

Write-Host "PostgreSQL is ready." -ForegroundColor Green

if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item ".env.example" ".env"
}
elseif ((Get-Content ".env" -Raw) -notmatch '(?m)^USE_POSTGRES\s*=\s*true\s*$') {
    Write-Host "Updating .env: USE_POSTGRES=true (Django must use the same DB as Docker)." -ForegroundColor Yellow
    $lines = Get-Content ".env"
    $found = $false
    $lines = foreach ($line in $lines) {
        if ($line -match '^\s*USE_POSTGRES\s*=') {
            $found = $true
            "USE_POSTGRES=true"
        } else {
            $line
        }
    }
    if (-not $found) { $lines = @("USE_POSTGRES=true") + $lines }
    $lines | Set-Content ".env"
}

$env:USE_POSTGRES = "true"

$python = Get-Python
Write-Host "Starting Django dev server (PostgreSQL)..." -ForegroundColor Cyan
Write-Host "Open http://127.0.0.1:8000/rentals/" -ForegroundColor Green
Write-Host "Log in with your username (e.g. Kamo9274), not your email." -ForegroundColor Green
Write-Host ""

& $python manage.py runserver
