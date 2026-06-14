@echo off
cd /d "%~dp0"
echo Starting CrossGate Graphic Exporter...
uv run src/main.py
pause
