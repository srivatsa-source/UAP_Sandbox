@echo off
REM UAP Launcher for Windows
REM Usage: uap.bat [command]
REM Commands: chat, dashboard, test, setup, check

setlocal

REM Try to find Python in the virtual environment first
set "VENV_PYTHON=%~dp0..\.venv\Scripts\python.exe"
if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" "%~dp0run.py" %*
    exit /b %ERRORLEVEL%
)

REM Try py launcher (Windows Python Launcher)
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py "%~dp0run.py" %*
    exit /b %ERRORLEVEL%
)

REM Try python in PATH
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python "%~dp0run.py" %*
    exit /b %ERRORLEVEL%
)

echo ERROR: Python not found!
echo Please install Python or activate your virtual environment.
echo.
echo Try: .\.venv\Scripts\activate
exit /b 1
