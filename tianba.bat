@echo off
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" -u "%~dp0_start.py" %*
