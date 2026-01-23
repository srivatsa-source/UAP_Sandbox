@echo off
REM UAP Global Launcher - Run from anywhere!
REM Place this in a folder that's in your PATH, or run the install command below

setlocal

REM Set the UAP installation directory
set "UAP_HOME=C:\Users\Srinath_veda\Documents\UAP sandbox\uap-protocol"
set "VENV_PYTHON=C:\Users\Srinath_veda\Documents\UAP sandbox\.venv\Scripts\python.exe"

REM Check if UAP_HOME exists
if not exist "%UAP_HOME%\run.py" (
    echo ERROR: UAP not found at %UAP_HOME%
    echo Please update UAP_HOME in this batch file.
    exit /b 1
)

REM Run UAP from anywhere
"%VENV_PYTHON%" "%UAP_HOME%\run.py" %*
