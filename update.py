# -*- coding: utf-8 -*-
"""
Druckworkflow Updater
Laedt die neueste Version von GitHub und ersetzt die lokale druckworkflow.py.
Ein Backup der aktuellen Version wird automatisch angelegt.
"""

import urllib.request
import shutil
import sys
from pathlib import Path
from datetime import datetime

GITHUB_URL = (
    "https://raw.githubusercontent.com/kounen80/drucker-workflow/main/druckworkflow.py"
)

def main():
    script_dir = Path(__file__).parent
    target = script_dir / "druckworkflow.py"

    if not target.exists():
        print(f"FEHLER: {target} nicht gefunden.")
        sys.exit(1)

    # Backup anlegen
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = script_dir / f"druckworkflow_backup_{ts}.py"
    shutil.copy2(target, backup)
    print(f"Backup angelegt: {backup.name}")

    # Download
    print(f"Lade neueste Version von GitHub ...")
    try:
        tmp = target.with_suffix(".tmp")
        urllib.request.urlretrieve(GITHUB_URL, tmp)
        tmp.replace(target)
        print("Update erfolgreich. druckworkflow.py wurde aktualisiert.")
    except Exception as e:
        print(f"FEHLER beim Download: {e}")
        print("Stelle Backup wieder her ...")
        shutil.copy2(backup, target)
        sys.exit(1)

if __name__ == "__main__":
    main()
