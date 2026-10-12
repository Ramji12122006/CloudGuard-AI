# CloudGuard AI - One-Click GitHub Push Script
# Target Repository: https://github.com/Ramji12122006/CloudGuard-AI

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " CloudGuard AI — Deploying to GitHub" -ForegroundColor Cyan
Write-Host " Repository: https://github.com/Ramji12122006/CloudGuard-AI" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$targetRepo = "https://github.com/Ramji12122006/CloudGuard-AI.git"

# Verify git installation
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Git is not installed or not found in PATH." -ForegroundColor Red
    Write-Host "Please install Git for Windows from https://git-scm.com/ and retry." -ForegroundColor Yellow
    Exit 1
}

# 1. Initialize git if not already a repository
if (-not (Test-Path ".git")) {
    Write-Host "[1/5] Initializing local Git repository..." -ForegroundColor Green
    git init
} else {
    Write-Host "[1/5] Existing Git repository detected." -ForegroundColor Green
}

# 2. Add all project files
Write-Host "[2/5] Staging files for commit..." -ForegroundColor Green
git add .

# 3. Create initial commit
Write-Host "[3/5] Creating commit..." -ForegroundColor Green
git commit -m "feat: complete CloudGuard AI cloud cost optimization platform" -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "No new changes to commit or commit already up to date." -ForegroundColor Yellow
}

# 4. Set default branch to main
Write-Host "[4/5] Setting branch to main..." -ForegroundColor Green
git branch -M main

# 5. Configure remote origin
Write-Host "[5/5] Configuring remote origin..." -ForegroundColor Green
$existingRemote = git remote get-url origin 2>$null
if ($existingRemote) {
    git remote set-url origin $targetRepo
} else {
    git remote add origin $targetRepo
}

# 6. Push to GitHub
Write-Host ""
Write-Host "Pushing code to https://github.com/Ramji12122006/CloudGuard-AI ..." -ForegroundColor Cyan
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host " SUCCESS! CloudGuard AI is now live on GitHub:" -ForegroundColor Green
    Write-Host " https://github.com/Ramji12122006/CloudGuard-AI" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[NOTICE] If the remote repository already contains existing files (e.g. README/License)," -ForegroundColor Yellow
    Write-Host "you can force push or pull existing files using:" -ForegroundColor Yellow
    Write-Host "  git push -u origin main --force" -ForegroundColor White
}
