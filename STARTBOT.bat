@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title DaviddTech Testbot - 250 USDT DRY-RUN

echo ================================================================
echo   TESTBOT: Binance-Marktdaten, aber ausschliesslich Testgeld
echo   250 virtuelle USDT ^| BTC/ETH/SOL ^| KEIN ECHTGELD
echo ================================================================
echo.
echo Vorhandene Test-Trades und die bestehende Dry-run-Datenbank
echo werden fortgesetzt. Es werden KEINE echten Orders aufgegeben.
echo Bei dieser selten handelnden Strategie koennen auch 24 Stunden ohne
echo einen einzigen Trade ein normales Ergebnis sein.
echo.
echo Bitte mit Strg+C beenden: Dann werden Daten sauber gespeichert und
echo der Abschlussbericht erzeugt. Direktes Schliessen des Fensters kann
echo den Abschlussbericht ueberspringen; TESTBOT_AUSWERTUNG.bat holt ihn nach.
echo.

where uv.exe >nul 2>nul
if errorlevel 1 (
    echo FEHLER: Das einmalig benoetigte Programm uv wurde nicht gefunden.
    echo.
    echo Installation mit Windows-Paketverwaltung:
    echo   winget install --id=astral-sh.uv -e
    echo.
    echo Offizielle Anleitung:
    echo   https://docs.astral.sh/uv/getting-started/installation/
    echo.
    echo Danach dieses Fenster schliessen und STARTBOT.bat erneut doppelklicken.
    pause
    exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0runtime\scripts\start-testbot-24x7.ps1"
set "BOT_EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%BOT_EXIT_CODE%"=="0" (
    echo Der Testbot wurde mit einem Fehler beendet. Fehlercode: %BOT_EXIT_CODE%
) else (
    echo Der Testbot wurde beendet. Die automatische Auswertung ist fertig.
)
echo Dieses Fenster kann jetzt geschlossen werden.
pause
exit /b %BOT_EXIT_CODE%
