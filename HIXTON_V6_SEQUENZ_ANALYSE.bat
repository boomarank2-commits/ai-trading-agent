@echo off
setlocal EnableExtensions
cd /d "%~dp0"

cls
echo ================================================================
echo   HIXTON V6 SEQUENZANALYSE - EXPLORATIV, KEIN TRADINGCODE
echo ================================================================
echo.
echo Nutzt ausschliesslich den sauberen V3-Kohortenreport mit 6328 Trades.
echo Testet drei vorregistrierte Sequenz-Routen in vier Walk-Forward-Fenstern.
echo Der alte Holdout ist verbraucht; ein Treffer ist nur Kandidat fuer frische OOS-Daten.
echo Am Ende wird automatisch eine ZIP-Datei erzeugt.
echo.

if not exist ".venv\Scripts\python.exe" (
  echo FEHLER: .venv\Scripts\python.exe fehlt.
  echo Bitte zuerst die Repo-Umgebung mit uv sync --frozen --all-extras --python 3.12 herstellen.
  pause
  exit /b 1
)

set "CAUSAL=research\reports\hixton_v1_causal"
set "SNAPS=%CAUSAL%\dead_trend\dead_trend_checkpoint_snapshots.csv"
set "TRADES=%CAUSAL%\all_v1_trade_features.csv"
set "CMAN=%CAUSAL%\analysis_manifest.json"
set "DMAN=%CAUSAL%\dead_trend\dead_trend_manifest.json"

for %%F in ("%SNAPS%" "%TRADES%" "%CMAN%" "%DMAN%") do (
  if not exist "%%~F" (
    echo FEHLER: Erforderliches V3-Artefakt fehlt: %%~F
    echo Bitte zuerst HIXTON_V1_CAUSAL_ANALYSE.bat erfolgreich ausfuehren.
    pause
    exit /b 1
  )
)

echo [1/2] Walk-Forward Sequenzanalyse ...
".venv\Scripts\python.exe" research\hixton_v6_sequence_analysis.py
if errorlevel 1 (
  echo.
  echo FEHLER: Sequenzanalyse wurde abgebrochen. Siehe Ausgabe oben.
  pause
  exit /b 1
)

echo.
echo [2/2] Report automatisch als ZIP verpacken ...
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmssfff"') do set "STAMP=%%I"
set "ZIP=HIXTON_V6_SEQUENZ_ANALYSE_%STAMP%.zip"
if exist "%ZIP%" (
  echo FEHLER: ZIP existiert bereits und wird aus Sicherheitsgruenden nicht ueberschrieben: %ZIP%
  pause
  exit /b 1
)

powershell -NoProfile -Command "Compress-Archive -Path 'research\reports\hixton_v6_sequence\*' -DestinationPath '%ZIP%'"
if errorlevel 1 (
  echo FEHLER: ZIP konnte nicht erzeugt werden.
  pause
  exit /b 1
)

echo.
echo ================================================================
echo   ANALYSE ABGESCHLOSSEN
echo ================================================================
echo Reportordner:
echo   research\reports\hixton_v6_sequence
echo.
echo ZIP ZUM HOCHLADEN:
echo   %CD%\%ZIP%
echo.
echo WICHTIG: candidate_for_fresh_oos=1 ist noch KEINE V6-Freigabe.
echo Die Route muss danach unveraendert auf wirklich neuen Daten geprueft werden.
echo.
pause
endlocal
