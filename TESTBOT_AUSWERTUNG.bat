@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title DaviddTech Testbot - Auswertung

echo Erzeuge eine Gesamtauswertung der persistenten Test-Datenbank ...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0runtime\scripts\export-dryrun-report.ps1"
set "REPORT_EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%REPORT_EXIT_CODE%"=="0" (
    echo Die Dry-run-Auswertung ist fehlgeschlagen. Fehlercode: %REPORT_EXIT_CODE%
) else (
    echo Die Dry-run-Auswertung wurde erzeugt.
)

if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Python-Umgebung fehlt. Bitte STARTBOT.bat einmal starten.
    set "BACKTEST_EXIT_CODE=1"
) else (
    echo.
    echo Werte alle erhaltenen alten und neuen UI-Backtests gemeinsam aus ...
    set "PYTHONDONTWRITEBYTECODE=1"
    "%~dp0.venv\Scripts\python.exe" "%~dp0runtime\backtest_history_analysis.py"
    set "BACKTEST_EXIT_CODE=!ERRORLEVEL!"
)

if not "%REPORT_EXIT_CODE%"=="0" (
    pause
    exit /b %REPORT_EXIT_CODE%
)
if not "%BACKTEST_EXIT_CODE%"=="0" (
    pause
    exit /b %BACKTEST_EXIT_CODE%
)

echo.
echo Backtest-Gesamtauswertung:
echo runtime\user_data\backtest_results\ui\GESAMTAUSWERTUNG.md
pause
exit /b 0
