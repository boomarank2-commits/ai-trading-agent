@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title V8 Paper-Replay-Paritaet

if not exist ".venv\Scripts\python.exe" (
  echo Python-Umgebung fehlt.
  pause
  exit /b 1
)
for /f "delims=" %%F in ('powershell -NoProfile -Command "Get-ChildItem -LiteralPath 'runtime\user_data\paper_telemetry' -Filter '*.jsonl' -File ^| Sort-Object LastWriteTime -Descending ^| Select-Object -First 1 -ExpandProperty FullName"') do set "PAPER=%%F"
for /f "delims=" %%D in ('powershell -NoProfile -Command "Get-ChildItem -LiteralPath 'runtime\user_data\replay_results' -Directory ^| Sort-Object LastWriteTime -Descending ^| Select-Object -First 1 -ExpandProperty FullName"') do set "REPLAY=%%D"
if not defined PAPER (
  echo Keine Paper-Telemetrie gefunden. STARTBOT muss mit diesem Stand mindestens eine Zeit lang gelaufen sein.
  pause
  exit /b 1
)
if not defined REPLAY (
  echo Kein Replay-Run gefunden.
  pause
  exit /b 1
)
echo Paper : !PAPER!
echo Replay: !REPLAY!\decisions.jsonl
.\.venv\Scripts\python.exe runtime\replay_parity.py --paper "!PAPER!" --replay "!REPLAY!\decisions.jsonl" --output "!REPLAY!\paper_replay_parity.json"
echo.
if errorlevel 1 (
  echo PARITAET NICHT BEWIESEN. Details stehen in paper_replay_parity.json.
) else (
  echo Signal-Paritaet fuer den ueberlappenden Zeitraum bestaetigt.
)
pause
