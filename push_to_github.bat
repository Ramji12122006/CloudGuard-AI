@echo off
title Push CloudGuard AI to GitHub
echo ==========================================================
echo  CloudGuard AI - Deploying to GitHub
echo  Repository: https://github.com/Ramji12122006/CloudGuard-AI
echo ==========================================================
echo.

cd /d "%~dp0"

where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed or not in PATH.
    echo Please install Git from https://git-scm.com/
    pause
    exit /b 1
)

if not exist ".git" (
    echo [1/5] Initializing local Git repository...
    git init
)

echo [2/5] Staging files...
git add .

echo [3/5] Creating commit...
git commit -m "feat: complete CloudGuard AI cloud cost optimization platform"

echo [4/5] Setting branch to main...
git branch -M main

echo [5/5] Configuring remote origin...
git remote remove origin >nul 2>nul
git remote add origin https://github.com/Ramji12122006/CloudGuard-AI.git

echo.
echo Pushing to GitHub...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ==========================================================
    echo  SUCCESS! Successfully pushed to:
    echo  https://github.com/Ramji12122006/CloudGuard-AI
    echo ==========================================================
) else (
    echo.
    echo [NOTE] If remote has conflicting commits or initial README/License, run:
    echo   git push -u origin main --force
)

echo.
pause
