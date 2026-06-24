@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Erstelle virtuelle Umgebung...
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
)

".venv\Scripts\python.exe" teleprompter.py %*
