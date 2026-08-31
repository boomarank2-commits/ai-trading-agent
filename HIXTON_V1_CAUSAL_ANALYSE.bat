@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title HIXTON V1 Ursachenanalyse

echo ================================================================
echo   HIXTON V1 CAUSAL ANALYSE - KEIN NEUER BACKTEST
echo ================================================================
echo.
echo Schritt 1: 6328 V1-Trades klassifizieren und Entry-Merkmale screenen.
echo Schritt 2: 1m/15m/1h-Candle-Pfade fuer Dead-Trend-Exits analysieren.
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

echo [1/2] V1 Trade-Level Ursachenanalyse ...
".venv\Scripts\python.exe" research\hixton_v1_causal_analysis.py
if errorlevel 1 goto :failed

echo.
echo [2/2] Dead-Trend Candle-Pfad-Analyse ...
".venv\Scripts\python.exe" research\hixton_v1_dead_trend_analysis.py
if errorlevel 1 goto :failed

echo.
echo ================================================================
echo   ANALYSE ABGESCHLOSSEN
echo ================================================================
echo Ergebnisse:
echo   research\reports\hixton_v1_causal\V1_CAUSAL_ANALYSIS.md
echo   research\reports\hixton_v1_causal\entry_filter_candidates.csv
echo   research\reports\hixton_v1_causal\dead_trend\dead_trend_candidates_pre_holdout.csv
echo.
echo WICHTIG: Noch keine V6-Regel automatisch in die Strategie uebernehmen.
echo Zuerst die Discovery/Validation- und Holdout-Ergebnisse pruefen.
pause
exit /b 0

:failed
echo.
echo FEHLER: Die Ursachenanalyse wurde abgebrochen. Siehe Ausgabe oben.
pause
exit /b 1
