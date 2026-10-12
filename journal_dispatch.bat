@echo off
cd /d "%~dp0"
call venv\Scripts\python.exe scripts\journal_dispatch.py >> journal_dispatch.log 2>&1
