@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title DaviddTech Testbot - Auswertung

echo Erzeuge eine Gesamtauswertung der persistenten Test-Datenbank ...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0runtime\scripts\export-dryrun-report.ps1"
set "REPORT_EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%REPORT_EXIT_CODE%"=="0" (
    echo Die Auswertung ist fehlgeschlagen. Fehlercode: %REPORT_EXIT_CODE%
) else (
    echo Die Auswertung wurde erzeugt.
)
pause
exit /b %REPORT_EXIT_CODE%
