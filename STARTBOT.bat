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
echo SICHERHEIT: Dieses Fenster ist der Lebensanker des Bots.
echo Strg+C beendet den Bot kontrolliert und erzeugt den Abschlussbericht.
echo Wird dieses Fenster direkt geschlossen oder der Supervisor beendet,
echo beendet Windows automatisch auch den gesamten Bot-Prozessbaum.
echo Ein unsichtbar weiterlaufender Bot ist damit nicht zulaessig.
echo.

call :ensure_uv
if errorlevel 1 exit /b 1

rem FreqUI-Zugang: Auf einem frischen Download gilt das dokumentierte
rem Erstpasswort. Ein mit PASSWORT_AENDERN.bat gesetztes Passwort bleibt
rem ausschliesslich lokal und ueberschreibt nur den API-Server-Zugang.
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
echo Bot Name : Testbot
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

rem Der Supervisor setzt vor dem Botstart ein Windows Job Object mit
rem JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE. Dadurch koennen Freqtrade/Python-
rem Prozesse und der lokale Browser-Starthelfer das sichtbare STARTBOT-Fenster
rem nicht mehr ueberleben.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0runtime\scripts\run-testbot-supervised.ps1"
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

rem WinGet aktualisiert den PATH eines bereits laufenden Fensters nicht immer sofort.
rem Die bekannten benutzerspezifischen Installationsorte werden deshalb direkt ergaenzt.
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe" set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"
if exist "%USERPROFILE%\.local\bin\uv.exe" set "PATH=%USERPROFILE%\.local\bin;%PATH%"

where uv.exe >nul 2>nul
if not errorlevel 1 (
    echo uv wurde erfolgreich eingerichtet.
    echo.
    exit /b 0
)

rem Falls WinGet keinen Link angelegt hat, suche die installierte uv.exe im WinGet-Paketordner.
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
