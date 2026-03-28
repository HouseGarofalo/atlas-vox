@echo off
echo ============================================
echo  Atlas Vox GPU Service - Installation
echo ============================================
echo.

cd /d "%~dp0\.."

echo Creating virtual environment...
python -m venv .venv
call .venv\Scripts\activate

echo Installing base dependencies...
pip install --quiet fastapi uvicorn pydantic pydantic-settings structlog httpx python-multipart soundfile numpy

echo Installing PyTorch with CUDA...
pip install --quiet torch torchaudio --index-url https://download.pytorch.org/whl/cu128

echo Installing TTS providers...
pip install --quiet chatterbox-tts f5-tts 2>nul
echo   (Fish Speech, OpenVoice, Orpheus require manual installation - see README.md)

echo.
echo Installation complete! Start with: scripts\start.bat
pause
