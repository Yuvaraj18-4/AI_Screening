# ShortList - Single Command Start Script
# Runs backend FastAPI serving both API and built React SPA frontend

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "Starting ShortList on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
if (Test-Path ".\backend\.venv\Scripts\uvicorn.exe") {
    & .\backend\.venv\Scripts\uvicorn.exe app.main:app --app-dir backend --host 127.0.0.1 --port 8000
} else {
    & py -3.11 -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
}
