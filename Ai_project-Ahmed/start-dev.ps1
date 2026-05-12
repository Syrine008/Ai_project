# Run from PowerShell:  cd ...\Ai_project-Ahmed  ;  .\start-dev.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "npm not found. Install Node.js LTS from https://nodejs.org/ then reopen this terminal." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path ".env")) {
    Set-Content -Path ".env" -Encoding utf8 -Value "VITE_API_BASE_URL=http://127.0.0.1:8000"
    Write-Host "Created .env with VITE_API_BASE_URL" -ForegroundColor Green
}

Write-Host "Installing dependencies..." -ForegroundColor Cyan
npm install

Write-Host "Starting dev server (Ctrl+C to stop). Open the printed URL in your browser." -ForegroundColor Cyan
npm run dev
