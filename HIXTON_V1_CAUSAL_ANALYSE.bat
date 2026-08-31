@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title HIXTON V1 Ursachenanalyse - Cohort Lock V3

echo ================================================================
echo   HIXTON V1 CAUSAL ANALYSE V3 - KOHORTEN-LOCK
echo ================================================================
echo.
echo Schritt 1: Exakt den vollstaendigen 6328-Trade Diagnose-Batch laden.
echo            Gemischte oder unvollstaendige Runs werden hart abgelehnt.
echo            Fat-Tails werden segmentlokal ohne Holdout-Leakage bewertet.
echo Schritt 2: 1m/15m/1h-Candle-Pfade fuer Dead-Trend-Exits analysieren.
echo            Aktivierung erst nach bestaetigtem 1m-Fee-Break-even-Close.
echo            Hypothetischer Exit am folgenden Candle-Open, nicht am Signal-Close.
echo            Gewinner- und Fat-Tail-Gewinnmasse besitzt harte Schutzgrenzen.
echo Es werden keine Strategie-Signale geaendert und keine Orders erzeugt.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo FEHLER: .venv fehlt. Bitte zuerst das Projekt wie gewohnt mit uv einrichten.
    pause
    exit /b 1
)

if not exist "runtime\user_data\backtest_results\hixton" (
    echo FEHLER: Hixton-Backtest-Ergebnisse fehlen.
    pause
    exit /b 1
)

if not exist "runtime\user_data\data\binance\BTC_USDT-1m.feather" (
    echo FEHLER: Lokale Binance-1m-Daten fehlen. Dead-Trend-Analyse kann nicht kausal laufen.
    pause
    exit /b 1
)

echo [1/2] V1 Trade-Level Ursachenanalyse V3 - Cohort Lock ...
".venv\Scripts\python.exe" research\hixton_v1_causal_analysis_v3.py
if errorlevel 1 goto :failed

echo.
echo [2/2] Dead-Trend Candle-Pfad-Analyse V3 - Cohort Lock ...
".venv\Scripts\python.exe" research\hixton_v1_dead_trend_analysis_v3.py
if errorlevel 1 goto :failed

echo.
echo ================================================================
echo   ANALYSE ABGESCHLOSSEN - NUR KOHORTENREINE ERGEBNISSE
echo ================================================================
echo Ergebnisse:
echo   research\reports\hixton_v1_causal\V1_CAUSAL_ANALYSIS.md
echo   research\reports\hixton_v1_causal\analysis_manifest.json
echo   research\reports\hixton_v1_causal\entry_filter_candidates.csv
echo   research\reports\hixton_v1_causal\dead_trend\dead_trend_candidates_pre_holdout.csv
echo   research\reports\hixton_v1_causal\dead_trend\dead_trend_manifest.json
echo.
echo WICHTIG: Noch keine V6-Regel automatisch in die Strategie uebernehmen.
echo Nur Kandidaten aus diesem V3-Lauf duerfen weiter bewertet werden.
pause
exit /b 0

:failed
echo.
echo FEHLER: Die Ursachenanalyse wurde abgebrochen. Siehe Ausgabe oben.
echo Das ist absichtlich fail-closed: gemischte oder falsche Runs werden nicht analysiert.
pause
exit /b 1
