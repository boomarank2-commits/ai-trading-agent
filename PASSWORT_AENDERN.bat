@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Testbot - FreqUI Passwort aendern

set "PASSWORD_FILE=%~dp0runtime\user_data\.testbot-ui-password"

echo ================================================================
echo   FreqUI - LOKALES PASSWORT AENDERN
echo ================================================================
echo.
echo Benutzer bleibt: testbot
echo Das neue Passwort wird nur auf diesem Rechner gespeichert.
echo Es wird NICHT zu GitHub hochgeladen.
echo.
echo WICHTIG: Ein bereits laufender Bot benutzt sein bisheriges Passwort.
echo Das neue Passwort wird erst nach sauberem Bot-Neustart aktiv.
echo.

set "NEWPASS="
set /p "NEWPASS=Neues Passwort eingeben: "
if not defined NEWPASS (
    echo.
    echo Kein Passwort eingegeben. Es wurde nichts geaendert.
    pause
    exit /b 1
)

set "TESTBOT_NEW_PASSWORD=%NEWPASS%"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$path=$env:PASSWORD_FILE; $value=$env:TESTBOT_NEW_PASSWORD; $dir=[IO.Path]::GetDirectoryName($path); [IO.Directory]::CreateDirectory($dir) ^| Out-Null; [IO.File]::WriteAllText($path,$value,[Text.UTF8Encoding]::new($false))"
if errorlevel 1 (
    echo.
    echo FEHLER: Das neue Passwort konnte nicht gespeichert werden.
    pause
    exit /b 1
)

set "TESTBOT_NEW_PASSWORD="
echo.
echo Passwort lokal gespeichert.
echo.
echo Jetzt:
echo   1. Falls der Bot laeuft: im Bot-Fenster Strg+C druecken.
echo   2. STARTBOT.bat erneut starten.
echo   3. In FreqUI Benutzer testbot und das neue Passwort verwenden.
echo.
echo Wenn dieses eigene Passwort spaeter verloren geht, ist der einfache
echo Reset-Weg ein frischer Download/Klon des Bots in einen neuen Ordner.
echo Dort gilt wieder das dokumentierte Erstpasswort.
echo.
pause
