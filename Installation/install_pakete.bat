@echo off
REM ================================================================
REM  Installiert die noetigen Python-Pakete fuer den Druckworkflow
REM ================================================================

echo.
echo Pruefe Python-Installation ...
py --version
if errorlevel 1 (
    echo.
    echo FEHLER: Python wurde nicht gefunden.
    echo Bitte erst Python von https://www.python.org/downloads/
    echo installieren und beim Installer den Haken
    echo "Add python.exe to PATH" setzen.
    echo.
    pause
    exit /b 1
)

echo.
echo Aktualisiere pip ...
py -m pip install --upgrade pip

echo.
echo Installiere PyMuPDF ...
py -m pip install pymupdf

if errorlevel 1 (
    echo.
    echo FEHLER bei der Paket-Installation.
    pause
    exit /b 1
)

echo.
echo Installiere Pillow ...
py -m pip install pillow

if errorlevel 1 (
    echo.
    echo FEHLER bei der Paket-Installation.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo   Pakete erfolgreich installiert.
echo ================================================================
echo.
pause
