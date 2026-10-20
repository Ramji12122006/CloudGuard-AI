# CloudGuard AI - PowerShell Live Server Launcher
# Usage: .\run_live_server.ps1

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "          CloudGuard AI - Intelligent Cloud Cost Platform" -ForegroundColor Cyan
Write-Host "                         STARTING LIVE SERVER" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 1. Verify Python installation
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python was not found in your PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.13 or 3.11+ from https://www.python.org/ (enable 'Add to PATH')." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    Exit 1
}

# 2. Check virtual environment
$VenvActivate = Join-Path $ScriptDir "venv\Scripts\Activate.ps1"
if (-not (Test-Path $VenvActivate)) {
    Write-Host "[1/3] Setting up Python virtual environment (one-time setup)..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Could not create virtual environment." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        Exit 1
    }
    
    Write-Host "[2/3] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
    & ".\venv\Scripts\python.exe" -m pip install --upgrade pip
    & ".\venv\Scripts\python.exe" -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to install dependencies." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        Exit 1
    }
    Write-Host "      Dependencies installed successfully!" -ForegroundColor Green
} else {
    Write-Host "[1/2] Virtual environment verified." -ForegroundColor Green
}

# Activate virtual environment
& $VenvActivate

# 3. Launch Streamlit server with live reloading
Write-Host ""
Write-Host "[2/2] Starting Streamlit Live Server..." -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  URL:           http://localhost:8501" -ForegroundColor Yellow
Write-Host "  Live Reload:   Enabled (changes auto-refresh on save)" -ForegroundColor Yellow
Write-Host "  To Stop:       Press Ctrl + C in this window" -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Run streamlit
streamlit run app.py --server.port=8501 --server.runOnSave=true
