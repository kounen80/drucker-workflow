@echo off
REM ================================================================
REM  Druckworkflow - Cleaning / Reset
REM
REM  Loescht ALLE PDFs und Logs aus dem Workflow und setzt den
REM  Zaehler auf 0. Das Hauptskript, der Beispiel-Ordner und der
REM  Installation-Ordner bleiben unangetastet.
REM ================================================================

title Druckworkflow - Cleaning
color 0E

echo.
echo ================================================================
echo   DRUCKWORKFLOW - CLEANING
echo ================================================================
echo.
echo Folgende Inhalte werden GELOESCHT:
echo.
echo   - C:\Druckworkflow\01_Eingang\*.pdf
echo   - C:\Druckworkflow\02_InArbeit\*.*
echo   - C:\Druckworkflow\04_Erledigt\*.pdf
echo   - C:\Druckworkflow\99_Fehler\*.pdf
echo   - C:\Druckworkflow\TEST_Antrag\*.pdf
echo   - C:\Druckworkflow\TEST_Broschuere\*.pdf
echo   - C:\Druckworkflow\logs\*.log
echo   - C:\Druckworkflow\counter.txt   (wird auf 0 zurueckgesetzt)
echo.
echo Folgendes BLEIBT erhalten:
echo.
echo   - druckworkflow.py             (Hauptskript)
echo   - Installation\                (Setup-Dateien)
echo   - Beispiel\                    (Beispiel-PDFs)
echo   - vergleich\                   (Analyse-Skripte)
echo.
echo ================================================================
echo.

set /p CONFIRM=Wirklich alles loeschen? (j/n):

if /i not "%CONFIRM%"=="j" (
    echo.
    echo Abgebrochen. Es wurde NICHTS geloescht.
    echo.
    pause
    exit /b 0
)

echo.
echo Loesche ...
echo.

REM Eingang
if exist "C:\Druckworkflow\01_Eingang\" del /q "C:\Druckworkflow\01_Eingang\*.pdf" 2>nul
echo   [ok] 01_Eingang geleert

REM InArbeit - alles raus
if exist "C:\Druckworkflow\02_InArbeit\" del /q "C:\Druckworkflow\02_InArbeit\*.*" 2>nul
echo   [ok] 02_InArbeit geleert

REM Erledigt
if exist "C:\Druckworkflow\04_Erledigt\" del /q "C:\Druckworkflow\04_Erledigt\*.pdf" 2>nul
echo   [ok] 04_Erledigt geleert

REM Fehler
if exist "C:\Druckworkflow\99_Fehler\" del /q "C:\Druckworkflow\99_Fehler\*.pdf" 2>nul
echo   [ok] 99_Fehler geleert

REM TEST-Druckordner
if exist "C:\Druckworkflow\TEST_Antrag\" del /q "C:\Druckworkflow\TEST_Antrag\*.pdf" 2>nul
echo   [ok] TEST_Antrag geleert

if exist "C:\Druckworkflow\TEST_Broschuere\" del /q "C:\Druckworkflow\TEST_Broschuere\*.pdf" 2>nul
echo   [ok] TEST_Broschuere geleert

REM Logs
if exist "C:\Druckworkflow\logs\" del /q "C:\Druckworkflow\logs\*.log" 2>nul
echo   [ok] logs geleert

REM Zaehler auf 0 zuruecksetzen
echo 0> "C:\Druckworkflow\counter.txt"
echo   [ok] counter.txt auf 0 gesetzt

echo.
echo ================================================================
echo   Cleaning fertig. Workflow ist im Ausgangszustand.
echo ================================================================
echo.
pause
