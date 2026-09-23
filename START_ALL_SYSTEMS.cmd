@echo off
title DYNA-STORE Complete System Manager
cd /d "%~dp0"

echo ==============================================================================
echo                 DYNA-STORE COMPLETE SYSTEM LAUNCHER
echo ==============================================================================
echo.
echo [1/4] Detecting Python runtime...

set "PYTHON_EXE=python"
where python >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
        set "PYTHON_EXE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
    ) else if exist "C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe" (
        set "PYTHON_EXE=C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe"
    ) else (
        echo [ERROR] Python not found. Please install Python or add it to PATH.
        pause
        exit /b 1
    )
)

echo [2/4] Starting Online Hosting Server + Cloudflare Tunnel...
start "DYNA-STORE Server & Cloudflare Tunnel" "%PYTHON_EXE%" server\hosting_server.py 8000

echo [3/4] Opening Web Admin Dashboard...
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8000"

echo [4/4] Launching DYNA-STORE Application (.exe)...
if exist "dist\DYNA-STORE.exe" (
    start "" "dist\DYNA-STORE.exe"
) else (
    echo [INFO] dist\DYNA-STORE.exe not found, running quickplay.py directly...
    start "" "%PYTHON_EXE%" quickplay.py
)

echo.
echo ==============================================================================
echo                        ALL SYSTEMS ARE NOW RUNNING!
echo ==============================================================================
echo.
echo  * Hosting Server:        http://127.0.0.1:8000
echo  * Web Admin Dashboard:   http://127.0.0.1:8000
echo  * Cloudflare Tunnel:     Auto-connecting (check browser dashboard for URL)
echo  * DYNA-STORE App:        Active on desktop
echo.
echo Check server\server_info.json or the Web Dashboard for your live public HTTPS link.
echo Keep this window open or minimize it.
echo ==============================================================================
echo.
pause
