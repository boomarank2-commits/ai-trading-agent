@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Testbot - FreqUI Passwort aendern

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

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0runtime\scripts\manage-testbot-ui-auth.ps1" -Mode ChangePassword
if errorlevel 1 (
    echo.
    echo FEHLER: Das neue Passwort konnte nicht gespeichert werden.
    pause
    exit /b 1
)

echo.
echo Passwort lokal gespeichert.
echo.
echo Jetzt:
echo   1. Falls der Bot laeuft: im Bot-Fenster Strg+C druecken.
echo   2. STARTBOT.bat erneut starten.
echo   3. In FreqUI Benutzer testbot und das neue Passwort verwenden.
echo.
echo Wenn das Passwort spaeter verloren geht, kann PASSWORT_AENDERN.bat
echo unter demselben Windows-Benutzer erneut ausgefuehrt werden.
echo.
pause
