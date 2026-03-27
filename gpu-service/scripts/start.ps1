# Atlas Vox GPU Service — PowerShell launcher
# Usage: .\scripts\start.ps1 [-Port 8200] [-Host "0.0.0.0"] [-NoReload]

param(
    [string]$Host = "0.0.0.0",
    [int]$Port = 8200,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"
Push-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "Starting Atlas Vox GPU Service on ${Host}:${Port}..." -ForegroundColor Cyan

$args = @(
    "-m", "uvicorn",
    "app.main:app",
    "--host", $Host,
    "--port", $Port
)

if (-not $NoReload) {
    $args += "--reload"
}

try {
    python @args
} finally {
    Pop-Location
}
