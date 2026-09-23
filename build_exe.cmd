@echo off
title Build DYNA-STORE.exe
cd /d "%~dp0"

echo ==============================================================================
echo                BUILD DYNA-STORE STANDALONE .EXE
echo ==============================================================================
echo.

set "PYTHON_EXE=python"
where python >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
        set "PYTHON_EXE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
    ) else if exist "C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe" (
        set "PYTHON_EXE=C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe"
    ) else (
        echo [ERROR] Python not found.
        pause
        exit /b 1
    )
)

"%PYTHON_EXE%" build_exe.py
pause
