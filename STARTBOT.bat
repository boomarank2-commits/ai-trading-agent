@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title HIXTON-V2 Testbot - 250 USDT DRY-RUN

echo ================================================================
echo   HIXTON-V2 GUARDED: ausschliesslich Forschung und Testgeld
echo   250 virtuelle USDT ^| 10 Coins ^| maximal 3 x 80 USDT ^| KEIN ECHTGELD
echo ================================================================
echo.
echo Dieser Branch verwendet fuer alle zehn Coins dieselbe Hixton-V2-Logik.
echo Der gekaufte Motor bleibt unveraendert: VIDYA 10/20 + SMA 15, ATR 200 x 2.
echo Long-Signal: originales Hixton-Flip-Up auf geschlossener 15m-Kerze,
echo aber nur wenn der abgeschlossene 1h-Kontext ueber einer steigenden Hixton-VIDYA liegt.
echo Exit: frueher bei Rueckfall unter die 15m-VIDYA; das originale rote
echo Hixton-Flip-Down am unteren Band bleibt als harter Fallback erhalten.
echo Es gibt keine alten V12.33 Coin-Sonderrouten und kein Pyramiding.
echo Das gemeinsame Portfolio darf maximal drei 80-USDT-Positionen bzw. 240 USDT binden.
echo Der Backtest-Bereich kann alle zehn Coins einzeln mit je 250-USDT-Testwallet pruefen
echo und danach automatisch den gemeinsamen chronologischen 3x80-Portfolio-Lauf rechnen.
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

powershell.exe -NoLogo -NoProfile -File "%~dp0runtime\scripts\cleanup-stale-testbot.ps1"
if errorlevel 1 (
    echo.
    echo SICHERHEITSSTOPP: Eine alte oder fremde Runtime konnte nicht sicher bereinigt werden.
    echo Der Testbot wird nicht gestartet.
    pause
    exit /b 1
)

set "LOCAL_UI_PASSWORD_FILE=%~dp0runtime\user_data\.testbot-ui-password"
set "FREQTRADE__API_SERVER__USERNAME=testbot"
call :ensure_ui_password
if errorlevel 1 exit /b 1
if "%FIRST_LOGIN_HELP%"=="1" (
    echo.
    echo ERSTE ANMELDUNG: Aus Sicherheitsgruenden wird das zufaellig erzeugte
    echo Erstpasswort nicht im Fenster angezeigt.
    echo Bitte jetzt PASSWORT_AENDERN.bat ausfuehren, ein eigenes lokales
    echo Passwort setzen und STARTBOT.bat danach erneut starten.
    start "" "%~dp0LOGIN_HILFE.html"
    pause
    exit /b 0
)

set /p FREQTRADE__API_SERVER__PASSWORD=<"%LOCAL_UI_PASSWORD_FILE%"
if not defined FREQTRADE__API_SERVER__PASSWORD (
    echo.
    echo SICHERHEITSSTOPP: Das lokale FreqUI-Passwort ist leer oder nicht lesbar.
    echo Mit PASSWORT_AENDERN.bat kann ein neues Passwort gesetzt werden.
    pause
    exit /b 1
)
set "FREQTRADE__API_SERVER__JWT_SECRET_KEY=DaviddTech-Local-Testbot-JWT-Secret-%FREQTRADE__API_SERVER__PASSWORD%"
set "FREQTRADE__API_SERVER__WS_TOKEN=DaviddTech-Local-Testbot-WebSocket-Token-%FREQTRADE__API_SERVER__PASSWORD%"

echo FreqUI wird nach dem Botstart automatisch im Browser geoeffnet.
echo Adresse  : http://127.0.0.1:8080
echo Bot Name : HIXTON-V2 Guarded
echo Benutzer : testbot
echo Passwort : wird aus der lokalen Passwortdatei geladen und nicht angezeigt
echo Aendern   : PASSWORT_AENDERN.bat ^(wird nach Bot-Neustart aktiv^)
echo.

powershell.exe -NoLogo -NoProfile -File "%~dp0runtime\scripts\run-testbot-supervised.ps1"
set "BOT_EXIT_CODE=%ERRORLEVEL%"

powershell.exe -NoLogo -NoProfile -File "%~dp0runtime\scripts\cleanup-stale-testbot.ps1"
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

:ensure_ui_password
set "FIRST_LOGIN_HELP=0"
if not exist "%LOCAL_UI_PASSWORD_FILE%" goto :create_ui_password
set "EXISTING_UI_PASSWORD="
set /p EXISTING_UI_PASSWORD=<"%LOCAL_UI_PASSWORD_FILE%"
if not defined EXISTING_UI_PASSWORD goto :create_ui_password
if "%EXISTING_UI_PASSWORD%"=="AAAAAAAAAAAAAAAAAAAAAAAA" goto :create_ui_password
exit /b 0

:create_ui_password
set "TESTBOT_PASSWORD_FILE=%LOCAL_UI_PASSWORD_FILE%"
powershell.exe -NoLogo -NoProfile -Command "$ErrorActionPreference='Stop'; $path=$env:TESTBOT_PASSWORD_FILE; $bytes=New-Object byte[] 18; $rng=[Security.Cryptography.RandomNumberGenerator]::Create(); try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }; $value=[Convert]::ToBase64String($bytes).Replace('+','-').Replace('/','_').TrimEnd('='); [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($path)); [IO.File]::WriteAllText($path,$value,[Text.UTF8Encoding]::new($false))"
set "TESTBOT_PASSWORD_FILE="
if errorlevel 1 (
    echo.
    echo SICHERHEITSSTOPP: Das lokale FreqUI-Passwort konnte nicht erzeugt werden.
    echo Der Testbot wird nicht gestartet.
    pause
    exit /b 1
)
set "FIRST_LOGIN_HELP=1"
exit /b 0

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
