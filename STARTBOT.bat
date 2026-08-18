@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title DaviddTech Testbot - 250 USDT DRY-RUN

echo ================================================================
echo   TESTBOT V12.6: Binance-Marktdaten, aber ausschliesslich Testgeld
echo   250 virtuelle USDT ^| BTC/ETH/SOL ^| KEIN ECHTGELD
echo ================================================================
echo.
echo V12.6 behaelt den profitablen langsamen Donchian-Kern aus V12.5.
echo Zusaetzlich testet jeder Coin einen eigenen streng gefilterten Fast-Donchian:
echo BTC ca. 12 Tage ^| ETH ca. 14 Tage ^| SOL ca. 10 Tage. Keine Coin-Kopplung.
echo Gewinner werden nicht durch fruehe Gewinn- oder Break-even-Exits abgeschnitten.
echo Nur ein frueh gescheiterter Breakout, der Struktur-/Regime-Exit oder der
echo feste -5,5%% Hard-Stop beendet eine Position. Es werden KEINE echten Orders aufgegeben.
echo.
echo SICHERHEIT: Dieses Fenster und das Testbot-UI sind Lebensanker.
echo Strg+C beendet den Bot kontrolliert und erzeugt den Abschlussbericht.
echo Wird dieses Fenster direkt geschlossen, der Supervisor beendet oder das
echo ueberwachte Testbot-UI geschlossen, beendet Windows automatisch auch den
echo gesamten Bot-Prozessbaum. Ein unsichtbar weiterlaufender Bot ist damit
echo nicht zulaessig.
echo.

call :ensure_uv
if errorlevel 1 exit /b 1

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0runtime\scripts\cleanup-stale-testbot.ps1"
if errorlevel 1 (
    echo.
    echo SICHERHEITSSTOPP: Eine alte oder fremde Runtime konnte nicht sicher bereinigt werden.
    echo Der Testbot wird nicht gestartet.
    pause
    exit /b 1
)

set "LOCAL_UI_PASSWORD_FILE=%~dp0runtime\user_data\.testbot-ui-password"
set "FREQTRADE__API_SERVER__USERNAME=testbot"
set "FREQTRADE__API_SERVER__PASSWORD=PaperOnly-250-USDT!"
set "FIRST_LOGIN_HELP=1"
if exist "%LOCAL_UI_PASSWORD_FILE%" (
    set /p FREQTRADE__API_SERVER__PASSWORD=<"%LOCAL_UI_PASSWORD_FILE%"
    set "FIRST_LOGIN_HELP=0"
)

echo FreqUI wird nach dem Botstart automatisch im Browser geoeffnet.
echo Adresse  : http://127.0.0.1:8080
echo Bot Name : Testbot V12.6
echo Benutzer : testbot
if "%FIRST_LOGIN_HELP%"=="1" (
    echo Passwort : PaperOnly-250-USDT!
    echo.
    echo ERSTE ANMELDUNG: Die Login-Hilfe wird zusaetzlich geoeffnet.
    echo Nach erfolgreichem Login kann mit PASSWORT_AENDERN.bat ein eigenes
    echo lokales Passwort gesetzt werden. Es wird erst nach Bot-Neustart aktiv.
    start "" "%~dp0LOGIN_HILFE.html"
) else (
    echo Passwort : eigenes lokales Passwort ist aktiv
    echo Aendern   : PASSWORT_AENDERN.bat ^(wird nach Bot-Neustart aktiv^)
)
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0runtime\scripts\run-testbot-supervised.ps1"
set "BOT_EXIT_CODE=%ERRORLEVEL%"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0runtime\scripts\cleanup-stale-testbot.ps1"
if errorlevel 1 (
    echo SICHERHEITSWARNUNG: Nach dem Botende ist Port 8080 nicht sicher frei.
    set "BOT_EXIT_CODE=1"
)

echo.
if not "%BOT_EXIT_CODE%"=="0" (
    echo Der Testbot wurde mit einem Fehler beendet. Fehlercode: %BOT_EXIT_CODE%
) else (
    echo Der Testbot wurde beendet. Die automatische Auswertung ist fertig.
)
echo Dieses Fenster kann jetzt geschlossen werden.
pause
exit /b %BOT_EXIT_CODE%

:ensure_uv
where uv.exe >nul 2>nul
if not errorlevel 1 exit /b 0

echo Das einmalig benoetigte Programm uv wurde nicht gefunden.
echo STARTBOT installiert uv jetzt automatisch ueber Windows WinGet.
echo.
where winget.exe >nul 2>nul
if errorlevel 1 (
    echo FEHLER: Windows WinGet wurde auf diesem Rechner nicht gefunden.
    echo Bitte den Microsoft App Installer installieren bzw. aktualisieren
    echo und STARTBOT.bat danach erneut doppelklicken.
    echo.
    pause
    exit /b 1
)

echo Installiere uv. Dieser Schritt ist nur beim ersten Mal notwendig ...
winget install --id=astral-sh.uv -e --accept-source-agreements --accept-package-agreements
echo.
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe" set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"
if exist "%USERPROFILE%\.local\bin\uv.exe" set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv.exe >nul 2>nul
if not errorlevel 1 (
    echo uv wurde erfolgreich eingerichtet.
    echo.
    exit /b 0
)
for /f "delims=" %%I in ('where /r "%LOCALAPPDATA%\Microsoft\WinGet\Packages" uv.exe 2^>nul') do (
    set "UV_FOUND_DIR=%%~dpI"
    goto :uv_location_found
)
goto :uv_not_found

:uv_location_found
set "PATH=%UV_FOUND_DIR%;%PATH%"
where uv.exe >nul 2>nul
if not errorlevel 1 (
    echo uv wurde erfolgreich eingerichtet.
    echo.
    exit /b 0
)

:uv_not_found
echo FEHLER: uv konnte nach der automatischen Installation nicht gefunden werden.
echo Bitte STARTBOT.bat einmal schliessen und erneut doppelklicken.
echo Falls der Fehler bleibt, uv manuell installieren mit:
echo   winget install --id=astral-sh.uv -e
echo.
pause
exit /b 1

endlocal