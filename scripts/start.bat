@echo off
chcp 936 >nul 2>nul
title API Testing Platform
cls
echo.
echo   API Testing Platform
echo.
echo.

cd /d "%~dp0.."

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% found
echo.

echo [Checking dependencies...]
pip show flask >nul 2>&1
if %errorlevel% neq 0 (
    echo [Installing dependencies, this may take a few minutes...]
    pip install -r requirements.txt -q
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies. Run manually: pip install -r requirements.txt
        pause
        exit /b 1
    )
)
echo [OK] Dependencies ready
echo.

echo [Initializing database...]
python -c "from app.models import init_db; init_db()"
if %errorlevel% neq 0 (
    echo [ERROR] Database initialization failed
    pause
    exit /b 1
)
echo [OK] Database ready
echo.

echo ========================================
echo   API Testing Platform Started!
echo ========================================
echo.
echo   URL: http://127.0.0.1:5000
echo.
echo   Account: admin / admin123
echo.
echo   Starting service, do not close this window...
echo.

ping -n 3 127.0.0.1 >nul 2>&1
start http://127.0.0.1:5000

python scripts/run.py

echo.
echo [Service stopped]
pause
