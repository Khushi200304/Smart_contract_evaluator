#!/usr/bin/env powershell
<#
.SYNOPSIS
    Khushi Backend Startup Script (PowerShell version)
.DESCRIPTION
    Activates venv, checks configuration, and starts FastAPI server
.EXAMPLE
    .\run.ps1
#>

param()

# Enable error handling
$ErrorActionPreference = "Stop"

Write-Host "
===================================" -ForegroundColor Cyan
Write-Host " Khushi Backend Startup" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommandPath
Set-Location $ScriptDir

# Check venv
Write-Host "[1/3] Checking virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Host "[✗] ERROR: Virtual environment not found at .venv\" -ForegroundColor Red
    Write-Host "Please create it: python -m venv .venv" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

try {
    & .\.venv\Scripts\Activate.ps1
    Write-Host "[✓] Virtual environment activated" -ForegroundColor Green
} catch {
    Write-Host "[✗] ERROR: Failed to activate venv" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check .env
Write-Host ""
Write-Host "[2/3] Checking configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "[!] .env file not found, creating from template..." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "[✓] Created .env - PLEASE EDIT WITH YOUR GROQ_API_KEY" -ForegroundColor Green
    } else {
        Write-Host "[✗] ERROR: .env.example not found" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "[✓] .env file exists" -ForegroundColor Green
}

# Create data directories
Write-Host ""
Write-Host "[3/3] Preparing data directories..." -ForegroundColor Yellow
@("data\uploads", "data\chroma") | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
    }
}
Write-Host "[✓] Data directories ready" -ForegroundColor Green

# Start server
Write-Host ""
Write-Host "===================================" -ForegroundColor Cyan
Write-Host " Starting FastAPI Server" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ API Server: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "✓ API Docs:   http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "✓ Frontend:   http://localhost:5173 (run 'npm run dev' in frontend folder)" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Run uvicorn without reload to avoid Windows subprocess issues
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-reload
