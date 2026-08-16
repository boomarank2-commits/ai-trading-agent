@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Historischer Backtest - aktueller Testbot

echo ================================================================
echo   HISTORISCHER BACKTEST - AKTUELLER TESTBOT
echo ================================================================
echo.
echo Dieser Start verwendet KEINE zweite Strategie.
echo Er startet den normalen Testbot mit seiner Backtest-Oberflaeche.
echo Dort werden fuer den aktuell ausgecheckten Bot dieselben Strategie-
echo dateien gehasht und mit historischen Binance-Daten simuliert.
echo.
echo WICHTIG: Der klassische Backtest ist NICHT der Full-System-Replay.
echo Fuer den Zeitmaschinen-Modus bitte HISTORISCHER_LIVE_REPLAY.bat nutzen.
echo.
pause
call "%~dp0STARTBOT.bat"
exit /b %ERRORLEVEL%
