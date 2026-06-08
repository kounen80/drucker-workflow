# Druckworkflow

Python-Skript, das eingehende PDFs in **Antrag** (A4 Farbe) und **Broschuere** (A3 Booklet, Graustufen ab Seite 4 + Logo) aufteilt und in die Hot-Folder des Konica/Fiery-Druckers ablegt.

## Schnellstart auf neuem Rechner

```powershell
# 1. Repo clonen (nach C:\Druckworkflow)
git clone https://github.com/kounen80/drucker-workflow.git C:\Druckworkflow

# 2. Python-Pakete installieren
cd C:\Druckworkflow
.\Installation\install_pakete.bat

# 3. Testlauf starten
.\Installation\start_druckworkflow.bat
```

Setzt Python 3 voraus (mit "Add to PATH" beim Installer). Komplette Schritt-fuer-Schritt-Anleitung inkl. Fiery-Hot-Folder-Setup, Autostart und Troubleshooting: **`Installation/INSTALLATION.txt`**.

## Git-Workflow zwischen mehreren Rechnern

```powershell
# Vor dem Arbeiten: neuesten Stand holen
git pull

# Nach Aenderungen: hochladen
git add -A
git commit -m "Kurze Beschreibung"
git push
```

## Auto-Update von GitHub

Beim Start holt sich `druckworkflow.py` automatisch die neueste Version von GitHub (das Repo ist public, kein Login noetig) und startet sich bei einer Aenderung mit der neuen Version neu. Ein Backup wird vorher angelegt. Es genuegt also **ein `git push`** auf einem Rechner — alle anderen PCs sind beim naechsten Start aktuell. Ohne Internet laeuft der Druckbetrieb mit der vorhandenen Version weiter.

Die PC-spezifischen Druckordner stehen in `config_lokal.py` (pro Rechner, nicht im Repo). Diese Datei wird vom Auto-Update **nie** ueberschrieben — der ECHT-Betrieb eines PCs bleibt also erhalten. Vorlage: `config_lokal.example.py`. Abschalten per `SELF_UPDATE = False` in `druckworkflow.py`.

## Was nicht im Repo liegt

Per `.gitignore` ausgeschlossen: echte PDFs (`*.pdf`), Arbeitsordner (`01_Eingang`, `02_InArbeit`, `04_Erledigt`, `99_Fehler`), `logs/`, `counter.txt`. Werden beim ersten Start lokal angelegt.

## Dateien

- `druckworkflow.py` — Hauptskript, oben Konfiguration (Seiten, DPI, Logo-Koordinaten, Pfade)
- `cleaning_starten.bat` — setzt alle Arbeitsordner zurueck
- `Installation/` — Setup-Skripte (`install_pakete.bat`, `start_druckworkflow.bat`) und ausfuehrliche Anleitung
