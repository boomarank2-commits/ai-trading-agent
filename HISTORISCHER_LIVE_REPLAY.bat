@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title V8 Historischer Live-Replay - 250 USDT

echo ================================================================
echo  V8 HISTORISCHER LIVE-REPLAY / TIME MACHINE
echo  Gemeinsame 250 USDT fuer BTC + ETH + SOL
echo  KEIN ECHTGELD - KEINE BOERSENORDER - KEINE LIVE-CREDENTIALS
echo ================================================================
echo.
where uv.exe >nul 2>nul
if errorlevel 1 (
  echo FEHLER: uv wurde nicht gefunden.
  echo Bitte zuerst STARTBOT.bat einmal starten oder uv installieren.
  pause
  exit /b 1
)

set "YEARS=6"
set /p "INPUT=Replay-Zeitraum 1, 3, 4 oder 6 Jahre [6]: "
if not "%INPUT%"=="" set "YEARS=%INPUT%"
if not "%YEARS%"=="1" if not "%YEARS%"=="3" if not "%YEARS%"=="4" if not "%YEARS%"=="6" (
  echo Ungueltiger Zeitraum.
  pause
  exit /b 1
)

echo.
uv sync --frozen --all-extras --python 3.12
if errorlevel 1 goto :fail

echo.
echo Der Replay nutzt ausschliesslich vorhandene, validierte lokale Binance-Daten.
echo Falls Daten fehlen, zuerst HISTORISCHE_DATEN_LADEN.bat ausfuehren.
echo.
.\.venv\Scripts\python.exe runtime\historical_live_replay.py --years %YEARS%
if errorlevel 1 goto :fail

echo.
echo Replay abgeschlossen. Die Run-Dateien liegen unter:
echo runtime\user_data\replay_results\
echo.
echo Starte Auswertung des neuesten Runs ...
for /f "delims=" %%D in ('powershell -NoProfile -Command "Get-ChildItem -LiteralPath 'runtime\user_data\replay_results' -Directory ^| Sort-Object LastWriteTime -Descending ^| Select-Object -First 1 -ExpandProperty FullName"') do set "LATEST=%%D"
if defined LATEST (
  .\.venv\Scripts\python.exe runtime\replay_analysis.py "!LATEST!"
  if not errorlevel 1 .\.venv\Scripts\python.exe runtime\replay_research_analysis.py "!LATEST!"
)
echo.
pause
exit /b 0

:fail
echo.
echo FEHLER: Replay wurde sicher beendet. Vorhandene Checkpoints/Logs bleiben erhalten.
pause
exit /b 1
