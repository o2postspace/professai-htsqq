@echo off
chcp 65001 >nul 2>&1
title ProfessAI - Stock Analysis Dashboard
cd /d "%~dp0"

echo.
echo   ==========================================
echo        ProfessAI - Stock Dashboard
echo   ==========================================
echo.
echo   Starting...
echo.

python run.py

if %errorlevel% neq 0 (
    echo.
    echo   [ERROR] Python not found!
    echo   Please install Python 3.12 from python.org
    echo.
    pause
)
