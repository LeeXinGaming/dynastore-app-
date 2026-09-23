@echo off
title DYNA-STORE Online Hosting Server
cd /d "%~dp0"

echo =====================================================================
echo           DYNA-STORE ONLINE FILE & .EXE HOSTING SYSTEM
echo =====================================================================
echo.
echo [1/3] Checking Python environment...

set "PYTHON_EXE=python"
where python >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
        set "PYTHON_EXE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
    ) else if exist "C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe" (
        set "PYTHON_EXE=C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe"
    ) else (
        echo [ERROR] Python not found in PATH or standard AppData directories.
        pause
        exit /b 1
    )
)

echo [2/3] Opening Admin Dashboard in browser...
start "" "http://127.0.0.1:8000"

echo [3/3] Starting Server and Cloudflare Tunnel...
echo.
echo * Web Dashboard:   http://127.0.0.1:8000
echo * Cloudflare HTTPS URL will appear below automatically once connected.
echo * Press Ctrl+C to stop the server at any time.
echo ---------------------------------------------------------------------
echo.

"%PYTHON_EXE%" server\hosting_server.py 8000
pause
