@echo off
REM ================================================================
REM  Startet den Druckworkflow im Vordergrund.
REM  Beenden mit Strg+C in diesem Fenster.
REM ================================================================

title Druckworkflow

if not exist "C:\Druckworkflow\druckworkflow.py" (
    echo.
    echo FEHLER: C:\Druckworkflow\druckworkflow.py nicht gefunden.
    echo Bitte den Ordner Druckworkflow nach C:\Druckworkflow kopieren.
    echo.
    pause
    exit /b 1
)

py "C:\Druckworkflow\druckworkflow.py"

echo.
echo Druckworkflow wurde beendet.
pause
