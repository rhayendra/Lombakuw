@echo off
title Ayo Lomba Server
cd /d "%~dp0"
echo Menjalankan server Ayo Lomba di http://127.0.0.1:5000 ...
".venv\Scripts\python.exe" app.py
pause
