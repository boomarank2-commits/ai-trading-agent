@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title DaviddTech Testbot - 250 USDT DRY-RUN

echo ================================================================
echo   TESTBOT V12.12: Binance-Marktdaten, aber ausschliesslich Testgeld
echo   250 virtuelle USDT ^| BTC/ETH/SOL/XRP/BNB/DOGE ^| KEIN ECHTGELD
echo ================================================================
echo.
echo V12.12 behaelt alle Signal- und Exit-Schwellen von V12.9 unveraendert.
echo BTC/ETH testen zusaetzlich einen separat markierten Trend-Reclaim nach
echo einem 15m-Pullback innerhalb bestaetigter 1h/4h-Aufwaertstrends.
echo SOL/XRP/BNB/DOGE nutzen nur den breiteren Donchian-Kern.
echo Eine pair-lokale Verlustserien-Sperre pausiert nach zwei schwachen Trades
echo innerhalb von 14 Tagen fuer drei Tage. Gewinner bleiben uncapped.
echo Forschungsziel: >1 USDT/Tag ist ein Stretch-Ziel, keine Backtest-Zwangsvorgabe.
echo Der feste -5,5%% Hard-Stop bleibt als letzte Sicherheitsgrenze bestehen.
echo Es werden KEINE echten Orders aufgegeben.
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
set "FIRST_LOGIN_HELP=1"
if not exist "%LOCAL_UI_PASSWORD_FILE%" (
    set "TESTBOT_PASSWORD_FILE=%LOCAL_UI_PASSWORD_FILE%"
    powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$path=$env:TESTBOT_PASSWORD_FILE; $bytes=New-Object byte[] 18; [Security.Cryptography.RandomNumberGenerator]::Fill($bytes); $value=[Convert]::ToBase64String($bytes).Replace('+','-').Replace('/','_').TrimEnd('='); [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($path)) ^| Out-Null; [IO.File]::WriteAllText($path,$value,[Text.UTF8Encoding]::new($false))"
    set "TESTBOT_PASSWORD_FILE="
    if errorlevel 1 (
        echo.
        echo SICHERHEITSSTOPP: Das lokale FreqUI-Passwort konnte nicht erzeugt werden.
        echo Der Testbot wird nicht gestartet.
        pause
        exit /b 1
    )
) else (
    set "FIRST_LOGIN_HELP=0"
)
set /p FREQTRADE__API_SERVER__PASSWORD=<"%LOCAL_UI_PASSWORD_FILE%"
if not defined FREQTRADE__API_SERVER__PASSWORD (
    echo.
    echo SICHERHEITSSTOPP: Das lokale FreqUI-Passwort ist leer oder nicht lesbar.
    echo Mit PASSWORT_AENDERN.bat kann ein neues Passwort gesetzt werden.
    pause
    exit /b 1
)
set "FREQTRADE__API_SERVER__JWT_SECRET_KEY=%FREQTRADE__API_SERVER__PASSWORD%-jwt"
set "FREQTRADE__API_SERVER__WS_TOKEN=%FREQTRADE__API_SERVER__PASSWORD%-ws"

echo FreqUI wird nach dem Botstart automatisch im Browser geoeffnet.
echo Adresse  : http://127.0.0.1:8080
echo Bot Name : Testbot V12.12
echo Benutzer : testbot
if "%FIRST_LOGIN_HELP%"=="1" (
    echo Passwort : %FREQTRADE__API_SERVER__PASSWORD%
    echo.
    echo ERSTE ANMELDUNG: Dieses zufaellig erzeugte Passwort gilt nur lokal.
    echo Die Login-Hilfe wird zusaetzlich geoeffnet.
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
