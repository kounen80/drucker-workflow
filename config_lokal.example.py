# -*- coding: utf-8 -*-
# VORLAGE fuer die lokale PC-Konfiguration.
#
# Das Skript legt beim ersten Start automatisch eine config_lokal.py mit
# TEST-Pfaden an. Diese Datei hier ist nur zur Ansicht im Repo - sie zeigt,
# welche Werte pro PC eingetragen werden.
#
# config_lokal.py wird NICHT zu GitHub gesynct (.gitignore) und vom
# Auto-Update nicht angetastet. So bleibt der ECHT-Betrieb eines PCs erhalten,
# auch wenn eine neue druckworkflow.py von GitHub gezogen wird.

# TEST-Modus (Ausgabe in lokale Ordner, nichts geht an den Drucker):
ANTRAG_DRUCKORDNER     = r"C:\Druckworkflow\TEST_Antrag"
BROSCHUERE_DRUCKORDNER = r"C:\Druckworkflow\TEST_Broschuere"

# ECHT-Betrieb: die beiden TEST-Zeilen oben auskommentieren (# davor), diese
# beiden aktivieren (# entfernen) und an die echten Fiery-Hot-Folder anpassen:
# ANTRAG_DRUCKORDNER     = r"\\SERVER\Druck\Antrag_A4_Duplex"
# BROSCHUERE_DRUCKORDNER = r"\\SERVER\Druck\Broschuere_A3"
