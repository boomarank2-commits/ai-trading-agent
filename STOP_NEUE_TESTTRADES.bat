@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Testbot - neue Test-Trades stoppen

if not exist "%~dp0runtime\user_data" mkdir "%~dp0runtime\user_data"
type nul > "%~dp0runtime\user_data\DRYRUN_STOP_ENTRIES"
if errorlevel 1 (
    echo FEHLER: Die Test-Entry-Sperre konnte nicht erstellt werden.
    pause
    exit /b 1
)

echo ================================================================
echo Neue TEST-Trades sind jetzt gesperrt.
echo ================================================================
echo Bereits offene simulierte Positionen werden weiterhin verwaltet.
echo Der Echtgeld-Kill-Switch STOP_ENTRIES wurde NICHT veraendert.
echo.
echo Mit TESTTRADES_FREIGEBEN.bat koennen neue Test-Trades wieder
echo freigegeben werden.
pause
exit /b 0
