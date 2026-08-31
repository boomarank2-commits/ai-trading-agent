@echo off
setlocal EnableExtensions
cd /d "%~dp0"

cls
echo ================================================================
echo   HIXTON V6 ROUTE C - SHARED-PORTFOLIO REPLAY
 echo ================================================================
echo.
echo Reproduziert zuerst den bekannten V1-Shared-Lauf mit 637 Trades.
echo Danach werden exakt die bereits analysierten Route-C-Exits eingesetzt.
echo 250 USDT Wallet, max. 3 gleichzeitige Trades, 80 USDT Einsatzanforderung.
echo Kein neuer Signal-Screen, kein frischer OOS-Beweis, kein Tradingcode.
echo Am Ende wird automatisch eine ZIP-Datei erzeugt.
echo.

if not exist ".venv\Scripts\python.exe" (
  echo FEHLER: .venv\Scripts\python.exe fehlt.
  pause
  exit /b 1
)

set "CAUSAL=research\reports\hixton_v1_causal"
set "SEQ=research\reports\hixton_v6_sequence"
for %%F in (
  "%CAUSAL%\all_v1_trade_features.csv"
  "%CAUSAL%\analysis_manifest.json"
  "%CAUSAL%\dead_trend\dead_trend_checkpoint_snapshots.csv"
  "%CAUSAL%\dead_trend\dead_trend_manifest.json"
  "%SEQ%\sequence_trade_decisions.csv"
  "%SEQ%\sequence_manifest.json"
) do (
  if not exist "%%~F" (
    echo FEHLER: Erforderliches Analyse-Artefakt fehlt: %%~F
    pause
    exit /b 1
  )
)

echo [1/2] Kalibrierter Shared-Portfolio Replay ...
".venv\Scripts\python.exe" research\hixton_v6_route_c_portfolio_replay.py
if errorlevel 1 (
  echo.
  echo FEHLER: Portfolio-Replay wurde abgebrochen. Siehe Ausgabe oben.
  pause
  exit /b 1
)

echo.
echo [2/2] Report automatisch als ZIP verpacken ...
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmssfff"') do set "STAMP=%%I"
set "ZIP=HIXTON_V6_ROUTEC_PORTFOLIO_REPLAY_%STAMP%.zip"
if exist "%ZIP%" (
  echo FEHLER: ZIP existiert bereits und wird nicht ueberschrieben: %ZIP%
  pause
  exit /b 1
)

powershell -NoProfile -Command "Compress-Archive -Path 'research\reports\hixton_v6_route_c_portfolio\*','research\HIXTON_V6_ROUTEC_FREEZE_20260901.json' -DestinationPath '%ZIP%'"
if errorlevel 1 (
  echo FEHLER: ZIP konnte nicht erzeugt werden.
  pause
  exit /b 1
)

echo.
echo ================================================================
echo   REPLAY ABGESCHLOSSEN
 echo ================================================================
echo Reportordner:
echo   research\reports\hixton_v6_route_c_portfolio
echo.
echo ZIP ZUM HOCHLADEN:
echo   %CD%\%ZIP%
echo.
echo WICHTIG: Dieser Replay prueft Kapital-/Slot-Effekte auf bekannter Historie.
echo Er ist kein frischer OOS-Test und keine V6-Freigabe.
echo.
pause
endlocal
