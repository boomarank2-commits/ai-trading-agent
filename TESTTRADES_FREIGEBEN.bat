@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Testbot - neue Test-Trades freigeben

if exist "%~dp0runtime\user_data\DRYRUN_STOP_ENTRIES" (
    del /f /q "%~dp0runtime\user_data\DRYRUN_STOP_ENTRIES"
    if errorlevel 1 (
        echo FEHLER: Die Test-Entry-Sperre konnte nicht entfernt werden.
        pause
        exit /b 1
    )
)

echo ================================================================
echo Neue TEST-Trades sind wieder freigegeben.
echo ================================================================
echo Der Echtgeld-Kill-Switch STOP_ENTRIES wurde NICHT veraendert.
pause
exit /b 0
