@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONDONTWRITEBYTECODE=1"
title Historische Binance-Daten fuer V8 Replay

echo ================================================================
echo  HISTORISCHE DATEN - Binance Spot - BTC / ETH / SOL
echo  Nur oeffentliche Marktdaten. Keine Orders, keine Echtgeldfunktion.
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
set /p "INPUT=Zeitraum 1, 3, 4 oder 6 Jahre [6]: "
if not "%INPUT%"=="" set "YEARS=%INPUT%"
if not "%YEARS%"=="1" if not "%YEARS%"=="3" if not "%YEARS%"=="4" if not "%YEARS%"=="6" (
  echo Ungueltiger Zeitraum.
  pause
  exit /b 1
)

echo.
echo Synchronisiere gelockte Python/Freqtrade-Umgebung ...
uv sync --frozen --all-extras --python 3.12
if errorlevel 1 goto :fail

echo.
echo Lade/ergaenze %YEARS% Jahre plus Warmup und pruefe alle Kerzen ...
.\.venv\Scripts\python.exe runtime\replay_prepare_data.py --years %YEARS%
if errorlevel 1 goto :fail

echo.
echo Historische Daten sind vorbereitet und auf Luecken/Duplikate geprueft.
pause
exit /b 0

:fail
echo.
echo FEHLER: Historische Daten wurden nicht vollstaendig vorbereitet.
pause
exit /b 1
