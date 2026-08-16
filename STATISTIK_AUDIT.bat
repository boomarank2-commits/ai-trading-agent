@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Research Statistik Audit - PBO und DSR

echo ================================================================
echo   RESEARCH STATISTIK-AUDIT - KEIN TRADING
echo ================================================================
echo.
echo Dieses Werkzeug wertet eine CSV mit periodischen Returns mehrerer
echo vorregistrierter Varianten aus. Es sendet KEINE Orders und veraendert
echo KEINE Strategie. Fuer PBO/DSR muessen auch gescheiterte Trials enthalten sein.
echo.
set /p INPUT=Pfad zur Return-Matrix CSV: 
if "%INPUT%"=="" exit /b 1
set /p SELECTED=Spaltenname des vorab ausgewaehlten Kandidaten: 
if "%SELECTED%"=="" exit /b 1
set "OUTPUT=%~dp0research\audit_outputs\statistical_audit.json"
if not exist "%~dp0research\audit_outputs" mkdir "%~dp0research\audit_outputs"

where uv.exe >nul 2>nul
if errorlevel 1 (
    echo FEHLER: uv wurde nicht gefunden. Bitte zuerst STARTBOT.bat einmal starten.
    pause
    exit /b 1
)

uv sync --frozen --all-extras --python 3.12
if errorlevel 1 exit /b 1

.\.venv\Scripts\python.exe runtime\statistical_audit.py "%INPUT%" --selected "%SELECTED%" --output "%OUTPUT%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
    echo Audit gespeichert: %OUTPUT%
) else (
    echo Audit fehlgeschlagen. Fehlercode: %RC%
)
pause
exit /b %RC%
