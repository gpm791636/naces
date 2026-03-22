@echo off
cd /d "%~dp0"
set ONE_RUN=true
python monitor.py
pause
