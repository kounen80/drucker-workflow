# -*- coding: utf-8 -*-
"""
Druckworkflow - Automatische PDF-Aufteilung in Antrag und Broschuere
Ueberwacht einen Eingangsordner und legt aufbereitete PDFs in bestehende
Hot-Folder eines Konica-Minolta/Fiery-Drucksystems.
"""

import os
import re
import sys
import time
import shutil
import logging
import traceback
import urllib.request
from pathlib import Path

import io
import fitz  # PyMuPDF
from PIL import Image

# ============================================================
# KONFIGURATION - hier alles anpassen
# ============================================================

BASE   = r"C:\Druckworkflow"
INPUT  = r"C:\Druckworkflow\01_Eingang"
WORK   = r"C:\Druckworkflow\02_InArbeit"
DONE   = r"C:\Druckworkflow\04_Erledigt"
ERROR  = r"C:\Druckworkflow\99_Fehler"
LOGDIR = r"C:\Druckworkflow\logs"

# Bestehende Hot-Folder des Fiery-Druckers - PRO PC unterschiedlich.
# Diese Pfade stehen NICHT hier im Code, sondern in config_lokal.py, weil sie
# auf jedem Rechner anders sind (Test vs. echter Fiery). config_lokal.py ist
# per .gitignore vom Auto-Update ausgenommen - so setzt ein Update die echten
# Druckordner nie versehentlich auf TEST zurueck.
# Fehlt die Datei, wird beim ersten Start eine Vorlage mit TEST-Pfaden angelegt.
_CONFIG_LOKAL = Path(__file__).resolve().parent / "config_lokal.py"

_CONFIG_TEMPLATE = '''# -*- coding: utf-8 -*-
# Lokale Konfiguration DIESES PCs.
# Wird NICHT zu GitHub gesynct und vom Auto-Update nicht angetastet.
# Hier die Druckordner dieses Rechners eintragen.

# TEST-Modus (Ausgabe in lokale Ordner, nichts geht an den Drucker):
ANTRAG_DRUCKORDNER     = r"C:\\Druckworkflow\\TEST_Antrag"
BROSCHUERE_DRUCKORDNER = r"C:\\Druckworkflow\\TEST_Broschuere"

# ECHT-Betrieb: die beiden TEST-Zeilen oben auskommentieren (# davor), diese
# beiden aktivieren (# entfernen) und an die echten Fiery-Hot-Folder anpassen:
# ANTRAG_DRUCKORDNER     = r"\\\\SERVER\\Druck\\Antrag_A4_Duplex"
# BROSCHUERE_DRUCKORDNER = r"\\\\SERVER\\Druck\\Broschuere_A3"
'''

if not _CONFIG_LOKAL.exists():
    _CONFIG_LOKAL.write_text(_CONFIG_TEMPLATE, encoding="utf-8")

try:
    sys.path.insert(0, str(_CONFIG_LOKAL.parent))
    from config_lokal import ANTRAG_DRUCKORDNER, BROSCHUERE_DRUCKORDNER
except Exception:
    # Fallback, falls config_lokal.py fehlt/fehlerhaft ist: sicherer TEST-Modus.
    ANTRAG_DRUCKORDNER     = r"C:\Druckworkflow\TEST_Antrag"
    BROSCHUERE_DRUCKORDNER = r"C:\Druckworkflow\TEST_Broschuere"

# ── Auto-Update von GitHub ──────────────────────────────────────────────────
# Beim Start die neueste druckworkflow.py von GitHub holen (Repo ist public,
# daher kein Login noetig) und sich bei Aenderung mit der neuen Version neu
# starten. config_lokal.py bleibt dabei unberuehrt. Bei fehlendem Internet
# laeuft der Druckbetrieb mit der vorhandenen Version weiter.
SELF_UPDATE    = True
GITHUB_RAW_URL = "https://raw.githubusercontent.com/kounen80/drucker-workflow/main/druckworkflow.py"

# Seitenbereich (menschliche Zaehlung: Seite 1 = erste Seite)
# ANTRAG_END_PAGE wird dynamisch berechnet (2 oder 3 Antragsseiten moeglich).
ANTRAG_START_PAGE = 2
# Fallback-Antragslaenge falls die Auto-Erkennung nicht greift:
ANTRAG_PAGES_FALLBACK = 2

# Antrag als 300-dpi-JPEG neu einbetten.
# Loest Transparenz-/Formularfeld-Probleme beim Fiery-RIP - alles wird flach
# als Bild gerendert, der Drucker hat keinen Interpretationsspielraum mehr.
# Nachteil: Text im Antrag ist dann nicht mehr durchsuchbar/markierbar.
# JPEG statt FlateDecode/ICCBased, weil der Fiery sonst denselben Job mehrmals
# durch sein Color-Management schickt -> Mehrfachdruck.
RASTERIZE_ANTRAG = True
ANTRAG_DPI       = 300
ANTRAG_JPG_QUALITY = 92

# BROSCHUERE_REMOVE_PAGES und die Seitenreihenfolge werden dynamisch aus der
# erkannten Antragslaenge abgeleitet. Keine statische Konfiguration noetig.

# Graustufen-Option fuer die Broschuere
# True = ab GRAYSCALE_FROM_PAGE werden alle Seiten in Graustufen umgewandelt.
# Anwendung NACH dem Vertauschen, also bezogen auf die Endreihenfolge.
CONVERT_BROSCHUERE_TO_GRAYSCALE = True
GRAYSCALE_FROM_PAGE = 4
GRAYSCALE_DPI = 180
GRAYSCALE_JPG_QUALITY = 82

# Farb-Seiten (Anschreiben + Leistungen) als CMYK-JPEG einbetten (via Pillow).
# Pillow konvertiert RGB->CMYK korrekt (PyMuPDF csCMYK invertiert die Werte).
# CMYK-Ausgabe: der Fiery muss nicht konvertieren -> kraeftiges Gruen bleibt erhalten.
RASTERIZE_COLOR_PAGES = True
COLOR_DPI = 250
COLOR_JPG_QUALITY = 92

# Stabilitaetspruefung
STABILITY_CHECKS    = 3
STABILITY_INTERVAL  = 1.0

MOVE_TO_PRINTFOLDER = False

# Logo von einer anderen Seite auf Seite 1 (Anschreiben) der Broschuere kopieren.
# Erscheint NUR in der Broschuere (der Antrag enthaelt Seite 1 ohnehin nicht).
# Wird NACH der Graustufen-Konvertierung eingefuegt - bleibt also farbig.
ADD_LOGO_TO_PAGE1 = True
# LOGO_SOURCE_PAGE wird dynamisch berechnet: antrag_pages * 2 + 2
# (2-seitiger Antrag -> Seite 6, 3-seitiger Antrag -> Seite 8)
LOGO_SOURCE_RECT  = (390, 60, 540, 110)        # Quellbereich in PDF-Punkten (x0,y0,x1,y1)
LOGO_TARGET_RECT  = (390, 270, 560, 320)       # Zielbereich auf Seite 1
LOGO_DPI          = 300

# Fortlaufende Nummerierung der Ausgabedateien
ANTRAG_PREFIX     = "antrag"
BROSCHUERE_PREFIX = "broschuere"
COUNTER_DIGITS    = 3   # 3 -> 001, 002, ... 999; 4 -> 0001, ...
# Statusdatei haelt den naechsten Zaehlerstand. So bleiben die Nummern auch
# fortlaufend, wenn alte Dateien aus dem Druckordner geloescht werden.
COUNTER_FILE = Path(BASE) / "counter.txt"

# ============================================================
# Setup
# ============================================================

for d in (BASE, INPUT, WORK, DONE, ERROR, LOGDIR):
    Path(d).mkdir(parents=True, exist_ok=True)

# Druckordner ebenfalls anlegen, falls lokal. Bei UNC-Pfaden zur Fiery-Freigabe
# kann das je nach Rechten fehlschlagen - das ist ok, check_target meldet das
# spaeter, wenn der Ordner wirklich nicht erreichbar ist.
for d in (ANTRAG_DRUCKORDNER, BROSCHUERE_DRUCKORDNER):
    try:
        Path(d).mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

logfile = Path(LOGDIR) / f"druckworkflow_{time.strftime('%Y-%m')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(logfile, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("druckworkflow")


# ============================================================
# Hilfsfunktionen
# ============================================================

def safe_name(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return name.strip(" .") or "datei"


def next_counter() -> int:
    """Liest den naechsten Zaehlerstand aus COUNTER_FILE und erhoeht ihn.
    Beide Ausgaben (Antrag + Broschuere) eines Auftrags bekommen dieselbe Nummer."""
    try:
        current = int(COUNTER_FILE.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        # Initial: hoechste vorhandene Nummer in den Druckordnern suchen
        current = max(
            highest_in_folder(ANTRAG_DRUCKORDNER, ANTRAG_PREFIX),
            highest_in_folder(BROSCHUERE_DRUCKORDNER, BROSCHUERE_PREFIX),
            0,
        )
    nxt = current + 1
    COUNTER_FILE.write_text(str(nxt), encoding="utf-8")
    return nxt


def highest_in_folder(folder: str, prefix: str) -> int:
    p = Path(folder)
    if not p.exists():
        return 0
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)\.pdf$", re.IGNORECASE)
    highest = 0
    for f in p.glob(f"{prefix}*.pdf"):
        m = pattern.match(f.name)
        if m:
            highest = max(highest, int(m.group(1)))
    return highest


def wait_until_stable(path: Path) -> bool:
    last = -1
    stable = 0
    for _ in range(120):
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return False
        if size == last and size > 0:
            stable += 1
            if stable >= STABILITY_CHECKS:
                try:
                    with open(path, "rb"):
                        pass
                    return True
                except OSError:
                    stable = 0
        else:
            stable = 0
            last = size
        time.sleep(STABILITY_INTERVAL)
    return False


def check_target(folder: str) -> None:
    p = Path(folder)
    if not p.exists():
        raise FileNotFoundError(f"Druckordner nicht erreichbar: {folder}")
    if not p.is_dir():
        raise NotADirectoryError(f"Druckordner ist kein Verzeichnis: {folder}")


def deliver(src: Path, target_folder: str) -> Path:
    # copyfile statt copy2: keine Metadaten uebernehmen.
    # Die Datei im Hot-Folder bekommt damit frische ACLs und eine aktuelle
    # mtime - sonst kann der Fiery-Dienst sie u.U. nicht in seinen
    # Manuscript-Ordner verschieben, druckt sie aber trotzdem - Endlosschleife.
    check_target(target_folder)
    dst_final = Path(target_folder) / src.name
    dst_temp  = Path(target_folder) / (src.name + ".part")
    shutil.copyfile(src, dst_temp)
    if dst_final.exists():
        dst_final.unlink()
    dst_temp.rename(dst_final)
    if MOVE_TO_PRINTFOLDER:
        src.unlink(missing_ok=True)
    return dst_final


# ============================================================
# Antragslängen-Erkennung
# ============================================================

def _pages_similar(pix_a, pix_b, threshold: float = 0.95) -> bool:
    if (pix_a.width, pix_a.height) != (pix_b.width, pix_b.height):
        return False
    n = len(pix_a.samples)
    if n == 0:
        return False
    matches = sum(1 for a, b in zip(pix_a.samples, pix_b.samples) if abs(a - b) < 15)
    return (matches / n) >= threshold



def detect_antrag_pages(doc) -> int:
    """Prueft ob der Antrag 2 oder 3 Seiten hat.
    Seite 2 und Seite 4 werden bei 36 DPI verglichen.
    Sind sie identisch, beginnt die Antrag-Kopie auf Seite 4 (2-seitiger Antrag).
    Sonst ist der Antrag 3 Seiten lang."""
    if doc.page_count < 5:
        log.info("Antrag-Erkennung: PDF hat weniger als 5 Seiten -> Fallback %s Seiten",
                 ANTRAG_PAGES_FALLBACK)
        return ANTRAG_PAGES_FALLBACK
    pix2 = doc[1].get_pixmap(dpi=36, colorspace=fitz.csGRAY)
    pix4 = doc[3].get_pixmap(dpi=36, colorspace=fitz.csGRAY)
    if _pages_similar(pix2, pix4):
        log.info("Antrag-Erkennung: 2 Seiten (Seite 4 entspricht Seite 2)")
        return 2
    log.info("Antrag-Erkennung: 3 Seiten (Seite 4 unterscheidet sich von Seite 2)")
    return 3


# ============================================================
# PDF-Verarbeitung
# ============================================================

def build_antrag(src_pdf: Path, out_pdf: Path, antrag_pages: int) -> None:
    start_idx = ANTRAG_START_PAGE - 1
    end_idx   = ANTRAG_START_PAGE + antrag_pages - 2  # dynamisch aus erkannter Laenge
    with fitz.open(src_pdf) as doc:
        out = fitz.open()
        if RASTERIZE_ANTRAG:
            for i in range(start_idx, end_idx + 1):
                page = doc[i]
                pix = page.get_pixmap(dpi=ANTRAG_DPI)
                jpg_bytes = pix.tobytes("jpg", jpg_quality=ANTRAG_JPG_QUALITY)
                rect = page.rect
                np_page = out.new_page(width=rect.width, height=rect.height)
                np_page.insert_image(rect, stream=jpg_bytes)
        else:
            out.insert_pdf(doc, from_page=start_idx, to_page=end_idx)
        out.set_metadata({"producer": "Druckworkflow", "creator": "Druckworkflow"})
        out.save(out_pdf, garbage=4, deflate=True)
        out.close()


def build_broschuere(src_pdf: Path, out_pdf: Path, antrag_pages: int) -> None:
    # Antrag-Seiten (Original) aus der Broschuere entfernen
    remove_idx = {p - 1 for p in range(2, 2 + antrag_pages)}
    with fitz.open(src_pdf) as doc:
        keep = [i for i in range(doc.page_count) if i not in remove_idx]
        if not keep:
            raise ValueError("Broschuere haette keine Seiten - Abbruch.")

        out = fitz.open()
        for i in keep:
            out.insert_pdf(doc, from_page=i, to_page=i)

        # Seitenreihenfolge: Anschreiben -> Leistungen (+Ueberlauf?) -> Antrag-Kopie -> Rest
        # Die 2 Standard-Leistungsseiten liegen in out immer an Index antrag_pages+1/+2.
        # Danach kann eine Ueberlaufseite folgen (< 100 Woerter), entweder direkt oder
        # eine Position verspaetet (wenn eine andere Seite dazwischen liegt).
        n = out.page_count
        leist1 = antrag_pages + 1
        leist2 = antrag_pages + 2
        leist_indices = [leist1, leist2]

        for candidate in [leist2 + 1, leist2 + 2]:
            if candidate < n:
                text = out[candidate].get_text().strip()
                wc = len(text.split()) if text else 0
                if 0 < wc < 100:
                    leist_indices.append(candidate)
                    log.info("Ueberlaufseite Leistung erkannt (out-Index %s, %s Woerter)",
                             candidate, wc)
                    break

        leistungen_pages = len(leist_indices)
        taken = {0} | set(range(1, antrag_pages + 1)) | set(leist_indices)
        rest  = [i for i in range(n) if i not in taken]
        order = [0] + leist_indices + list(range(1, antrag_pages + 1)) + rest
        out.select(order)

        if CONVERT_BROSCHUERE_TO_GRAYSCALE or RASTERIZE_COLOR_PAGES:
            # Graustufen beginnen nach Anschreiben + Leistungsseiten
            gs_start_idx = leistungen_pages + 1
            new = fitz.open()
            for i, page in enumerate(out):
                if i >= gs_start_idx and CONVERT_BROSCHUERE_TO_GRAYSCALE:
                    pix = page.get_pixmap(dpi=GRAYSCALE_DPI,
                                          colorspace=fitz.csGRAY)
                    jpg_bytes = pix.tobytes("jpg", jpg_quality=GRAYSCALE_JPG_QUALITY)
                    rect = page.rect
                    np_page = new.new_page(width=rect.width, height=rect.height)
                    np_page.insert_image(rect, stream=jpg_bytes)
                elif i < gs_start_idx and RASTERIZE_COLOR_PAGES:
                    pix = page.get_pixmap(dpi=COLOR_DPI)
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    buf = io.BytesIO()
                    img.convert("CMYK").save(buf, format="JPEG", quality=COLOR_JPG_QUALITY)
                    jpg_bytes = buf.getvalue()
                    rect = page.rect
                    np_page = new.new_page(width=rect.width, height=rect.height)
                    np_page.insert_image(rect, stream=jpg_bytes)
                else:
                    new.insert_pdf(out, from_page=i, to_page=i)
            out.close()
            out = new

        # Logo von Quellseite holen und auf Seite 1 platzieren.
        # Bewusst NACH dem Graustufen-Schritt - so bleibt das Logo farbig.
        # Quellseite = erste Leistungsseite im Original: antrag_pages * 2 + 2
        if ADD_LOGO_TO_PAGE1:
            logo_source_page = antrag_pages * 2 + 2
            if logo_source_page > doc.page_count:
                log.warning(
                    "Logo-Quellseite %s existiert nicht (PDF hat %s Seiten) - "
                    "Logo wird uebersprungen.",
                    logo_source_page, doc.page_count,
                )
            elif out.page_count < 1:
                log.warning("Broschuere hat keine Seite 1 - Logo wird uebersprungen.")
            else:
                src_page = doc[logo_source_page - 1]
                src_rect = fitz.Rect(*LOGO_SOURCE_RECT)
                pix = src_page.get_pixmap(clip=src_rect, dpi=LOGO_DPI)
                target_rect = fitz.Rect(*LOGO_TARGET_RECT)
                out[0].insert_image(target_rect, pixmap=pix,
                                    keep_proportion=True)

        out.save(out_pdf, garbage=4, deflate=True)
        out.close()


def process(pdf_path: Path) -> None:
    log.info("Neue Datei: %s", pdf_path.name)

    if not wait_until_stable(pdf_path):
        raise RuntimeError("Datei wurde nicht stabil kopiert.")

    work_pdf = Path(WORK) / pdf_path.name
    if work_pdf.exists():
        work_pdf.unlink()
    shutil.move(str(pdf_path), str(work_pdf))

    try:
        with fitz.open(work_pdf) as doc:
            n = doc.page_count
            antrag_pages = detect_antrag_pages(doc)
        if n < 3:
            raise ValueError(f"PDF hat nur {n} Seite(n), mindestens 3 noetig.")

        check_target(ANTRAG_DRUCKORDNER)
        check_target(BROSCHUERE_DRUCKORDNER)

        nr = next_counter()
        num = str(nr).zfill(COUNTER_DIGITS)
        antrag_name = f"{ANTRAG_PREFIX}{num}.pdf"
        bro_name    = f"{BROSCHUERE_PREFIX}{num}.pdf"
        log.info("Auftragsnummer: %s", num)

        antrag_tmp = Path(WORK) / antrag_name
        bro_tmp    = Path(WORK) / bro_name

        log.info("Erzeuge Antrag-PDF: %s", antrag_name)
        build_antrag(work_pdf, antrag_tmp, antrag_pages)

        log.info("Erzeuge Broschueren-PDF: %s", bro_name)
        build_broschuere(work_pdf, bro_tmp, antrag_pages)

        log.info("Liefere Antrag -> %s", ANTRAG_DRUCKORDNER)
        deliver(antrag_tmp, ANTRAG_DRUCKORDNER)

        log.info("Liefere Broschuere -> %s", BROSCHUERE_DRUCKORDNER)
        deliver(bro_tmp, BROSCHUERE_DRUCKORDNER)

        antrag_tmp.unlink(missing_ok=True)
        bro_tmp.unlink(missing_ok=True)

        ts = time.strftime("%Y%m%d_%H%M%S")
        done_path = Path(DONE) / f"{work_pdf.stem}_{ts}.pdf"
        shutil.move(str(work_pdf), str(done_path))
        log.info("Fertig. Original -> %s", done_path)

    except Exception as e:
        log.error("Fehler bei %s: %s", work_pdf.name, e)
        log.error(traceback.format_exc())
        try:
            ts = time.strftime("%Y%m%d_%H%M%S")
            err_path = Path(ERROR) / f"{work_pdf.stem}_{ts}.pdf"
            shutil.move(str(work_pdf), str(err_path))
            log.error("Original verschoben nach %s", err_path)
        except Exception as move_err:
            log.error("Konnte Datei nicht in Fehlerordner verschieben: %s",
                      move_err)


# ============================================================
# Eingangs-Schleife (Polling, deterministische Reihenfolge)
# ============================================================

FILENAME_TIMESTAMP_RE = re.compile(r"(\d{8}_\d{6})")


def input_sort_key(p: Path):
    """Sortierschluessel fuer Eingangsdateien.
    Reihenfolge der Priorisierung:
      1. Wenn der Dateiname einen Zeitstempel YYYYMMDD_HHMMSS enthaelt
         (typisch fuer offers_HASH_20260510_110352.pdf), nimm diesen.
         So bleibt die Reihenfolge auch beim Massen-Einfuegen stabil,
         weil sie nicht von Windows-mtimes abhaengt.
      2. Sonst Datei-mtime (= Zeitpunkt der Erzeugung in 01_Eingang).
      3. Dateiname als Tiebreaker bei identischen Werten.
    """
    m = FILENAME_TIMESTAMP_RE.search(p.stem)
    if m:
        try:
            ts = time.mktime(time.strptime(m.group(1), "%Y%m%d_%H%M%S"))
            return (ts, p.name.lower())
        except ValueError:
            pass
    return (p.stat().st_mtime, p.name.lower())


def next_input_file():
    """Aelteste PDF im Eingang oder None. Reihenfolge per input_sort_key:
    Zeitstempel-im-Dateinamen > mtime > Dateiname."""
    pdfs = [p for p in Path(INPUT).glob("*.pdf")]
    if not pdfs:
        return None
    pdfs.sort(key=input_sort_key)
    return pdfs[0]


def self_update() -> None:
    """Holt die neueste druckworkflow.py von GitHub und startet sich bei
    Aenderung mit der neuen Version neu. Netzwerkfehler werden ignoriert -
    der Druckbetrieb laeuft dann mit der vorhandenen Version weiter.
    config_lokal.py wird nie angefasst (steht in einer eigenen Datei)."""
    if not SELF_UPDATE:
        return
    # Endlosschleife verhindern: direkt nach einem Selbst-Update einmal aussetzen.
    if os.environ.get("DRUCKWORKFLOW_UPDATED") == "1":
        os.environ.pop("DRUCKWORKFLOW_UPDATED", None)
        return

    target = Path(__file__).resolve()
    try:
        req = urllib.request.Request(GITHUB_RAW_URL,
                                     headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            remote = resp.read()
    except Exception as e:
        log.warning("Update-Pruefung uebersprungen (kein GitHub-Zugriff): %s", e)
        return

    def _norm(b: bytes) -> bytes:
        # Zeilenenden vereinheitlichen, damit reine CRLF/LF-Unterschiede kein
        # sinnloses Update ausloesen.
        return b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")

    try:
        local = target.read_bytes()
    except OSError as e:
        log.warning("Eigene Datei nicht lesbar - Update uebersprungen: %s", e)
        return

    if _norm(remote) == _norm(local):
        log.info("Auto-Update: bereits aktuell.")
        return

    ts = time.strftime("%Y%m%d_%H%M%S")
    backup = target.with_name(f"druckworkflow_backup_{ts}.py")
    try:
        shutil.copy2(target, backup)
        target.write_bytes(remote)
    except OSError as e:
        log.error("Auto-Update fehlgeschlagen (Schreibfehler): %s", e)
        return

    log.info("Auto-Update: neue Version installiert (Backup: %s). Neustart ...",
             backup.name)
    os.environ["DRUCKWORKFLOW_UPDATED"] = "1"
    try:
        os.execv(sys.executable, [sys.executable, str(target)] + sys.argv[1:])
    except OSError as e:
        log.error("Neustart nach Update fehlgeschlagen: %s - bitte manuell neu "
                  "starten.", e)
        sys.exit(1)


def _print_bereit() -> None:
    """Gibt den Bereit-/Beenden-Hinweis aus. Wird nach jedem abgearbeiteten
    Stapel erneut gezeigt, damit der Strg+C-Hinweis immer als Letztes steht
    und nicht von neuen Druckmeldungen nach oben verdraengt wird."""
    print()
    print("=" * 60)
    print("  BEREIT - Druckworkflow laeuft.")
    print("  Neue Dateien werden automatisch verarbeitet.")
    print("  Zum Beenden: Strg+C druecken.")
    print("=" * 60)
    print()


def _warte_auf_taste(prompt: str) -> None:
    """Wartet auf EINEN beliebigen Tastendruck - nicht nur auf Return."""
    print(prompt, end="", flush=True)
    try:
        import msvcrt
        msvcrt.getch()
        print()
    except Exception:
        # Fallback ausserhalb von Windows: auf Enter warten.
        try:
            input()
        except EOFError:
            pass


def main():
    self_update()
    log.info("=" * 60)
    log.info("Druckworkflow gestartet. Eingang: %s", INPUT)
    log.info("Antrag-Hotfolder:     %s", ANTRAG_DRUCKORDNER)
    log.info("Broschuere-Hotfolder: %s", BROSCHUERE_DRUCKORDNER)
    log.info("Graustufen-Broschuere: %s (ab Seite %s)",
             CONVERT_BROSCHUERE_TO_GRAYSCALE, GRAYSCALE_FROM_PAGE)
    log.info("Verarbeitungs-Reihenfolge: aelteste Datei zuerst.")
    log.info("Ueberwachung laeuft. Mit Strg+C beenden.")

    try:
        # Vorhandene Dateien im Eingang zuerst abarbeiten
        while True:
            f = next_input_file()
            if f is None:
                break
            try:
                process(f)
            except Exception as e:
                log.error("Unerwarteter Fehler: %s", e)
                log.error(traceback.format_exc())

        _print_bereit()

        while True:
            f = next_input_file()
            if f is not None:
                try:
                    process(f)
                except Exception as e:
                    log.error("Unerwarteter Fehler: %s", e)
                    log.error(traceback.format_exc())
                # Wenn nichts mehr ansteht, den Hinweis erneut ausgeben, damit
                # der Strg+C-Hinweis immer als letztes sichtbar bleibt.
                if next_input_file() is None:
                    _print_bereit()
            else:
                time.sleep(2)
    except KeyboardInterrupt:
        print()
        print("=" * 60)
        print("  Druckworkflow beendet.")
        print("=" * 60)
        print()
        _warte_auf_taste("  Druecken Sie eine beliebige Taste zum Schliessen ...")


if __name__ == "__main__":
    main()
