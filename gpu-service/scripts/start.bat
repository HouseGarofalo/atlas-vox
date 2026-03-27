@echo off
echo Starting Atlas Vox GPU Service...
cd /d "%~dp0\.."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8200 --reload
