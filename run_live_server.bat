@echo off
title CloudGuard AI - Live Server
color 0B
echo ======================================================================
echo           CloudGuard AI - Intelligent Cloud Cost Platform
echo                          STARTING LIVE SERVER
echo ======================================================================
echo.

cd /d "%~dp0"

:: 1. Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your Windows PATH.
    echo Please install Python 3.13 or 3.11+ from https://www.python.org/
    echo Make sure to check the box "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Check if virtual environment exists, if not create and install dependencies
if not exist "venv\Scripts\activate.bat" (
    echo [1/3] Virtual environment not found. Performing one-time setup...
    echo       Creating virtual environment (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    
    echo [2/3] Installing dependencies from requirements.txt...
    call venv\Scripts\activate.bat
    pip install --upgrade pip
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo       Setup complete!
) else (
    echo [1/2] Activating virtual environment (venv)...
    call venv\Scripts\activate.bat
)

:: 3. Launch Streamlit Live Server
echo.
echo [2/2] Launching CloudGuard AI Live Server...
echo ======================================================================
echo   URL:           http://localhost:8501
echo   Mode:          Live Reload (auto-updates when files are saved)
echo   To Stop:       Press Ctrl + C in this terminal window
echo ======================================================================
echo.

streamlit run app.py --server.port=8501 --server.runOnSave=true

if %errorlevel% neq 0 (
    echo.
    echo [NOTICE] Streamlit server exited.
)

pause
