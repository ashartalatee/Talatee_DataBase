@echo off
cd /d "%~dp0"
call venv\Scripts\python.exe scripts\kompas_refresh.py >> kompas_refresh.log 2>&1
