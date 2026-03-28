@echo off
echo ============================================
echo  Atlas Vox GPU Service - Windows Service Setup
echo ============================================
echo.
echo This creates a Windows Task Scheduler entry that auto-starts
echo the GPU service on login.
echo.

set "SCRIPT_DIR=%~dp0"
set "GPU_DIR=%SCRIPT_DIR%.."
set "VENV_PYTHON=%GPU_DIR%\.venv\Scripts\python.exe"

:: Check if venv exists
if not exist "%VENV_PYTHON%" (
    echo ERROR: Virtual environment not found. Run install.bat first.
    pause
    exit /b 1
)

:: Create the scheduled task
schtasks /create /tn "AtlasVoxGPUService" /tr "\"%VENV_PYTHON%\" -m uvicorn app.main:app --host 0.0.0.0 --port 8200" /sc onlogon /rl highest /f
if %errorlevel% equ 0 (
    echo.
    echo Task created: AtlasVoxGPUService
    echo The GPU service will auto-start on login.
    echo.
    echo To start now: scripts\start.bat
    echo To remove:    schtasks /delete /tn AtlasVoxGPUService /f
) else (
    echo.
    echo Failed to create scheduled task. Try running as Administrator.
)
pause
