@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title Historische Replay-Auswertung

if not exist ".venv\Scripts\python.exe" (
  echo Python-Umgebung fehlt. Bitte zuerst STARTBOT oder Replay starten.
  pause
  exit /b 1
)
for /f "delims=" %%D in ('powershell -NoProfile -Command "Get-ChildItem -LiteralPath 'runtime\user_data\replay_results' -Directory ^| Sort-Object LastWriteTime -Descending ^| Select-Object -First 1 -ExpandProperty FullName"') do set "LATEST=%%D"
if not defined LATEST (
  echo Noch kein Replay-Run gefunden.
  pause
  exit /b 1
)
echo Werte aus: !LATEST!
.\.venv\Scripts\python.exe runtime\replay_analysis.py "!LATEST!"
if errorlevel 1 exit /b 1
echo.
echo V8 Breakout-/Volumen-/Regime-Diagnose ...
.\.venv\Scripts\python.exe runtime\replay_research_analysis.py "!LATEST!"
echo.
pause
