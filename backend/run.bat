@echo off
REM Windows batch file to run the Khushi backend safely
REM Handles venv activation and uvicorn startup

setlocal enabledelayedexpansion

REM Get the script directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo.
echo ===================================
echo  Khushi Backend Startup Script
echo ===================================
echo.

REM Check if .venv exists
if not exist ".venv\" (
    echo ERROR: Virtual environment not found at .venv\
    echo Please run: python -m venv .venv
    pause
    exit /b 1
)

REM Activate venv
echo [1/3] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate venv
    pause
    exit /b 1
)
echo [✓] Virtual environment activated

REM Check .env file
echo.
echo [2/3] Checking .env file...
if not exist ".env" (
    echo WARNING: .env file not found
    echo Copying from .env.example...
    if exist ".env.example" (
        copy .env.example .env
        echo [✓] Created .env from template - EDIT IT WITH YOUR GROQ_API_KEY
    ) else (
        echo ERROR: .env.example not found
        pause
        exit /b 1
    )
) else (
    echo [✓] .env file exists
)

REM Create data directories
echo.
echo [3/3] Creating data directories...
if not exist "data\uploads\" mkdir data\uploads
if not exist "data\chroma\" mkdir data\chroma
echo [✓] Data directories ready

echo.
echo ===================================
echo  Starting FastAPI Server
echo ===================================
echo.
echo Server will be available at: http://127.0.0.1:8000
echo API docs available at:       http://127.0.0.1:8000/docs
echo Press Ctrl+C to stop
echo.

REM Run uvicorn WITHOUT reload (avoids subprocess issues on Windows)
REM Use --no-reload to prevent subprocess activation problems
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-reload

endlocal
pause
