#!/usr/bin/env python3
"""Bericht des HW-Imports per Signal an FS, aufgerufen von update.sh nach dem Push.

hw_import.py (00:30) schreibt hw_bericht.json, update.sh (06:30) veröffentlicht und ruft danach:
  python3 hw_bericht.py --status live|unveraendert|fehler [--grund "Push fehlgeschlagen!"]

Keine KI, keine Mailtexte: nur Titel und Datum, bereinigt und gekürzt (Prompt-Injection-Schutz).
Kein Versand, wenn nichts passiert ist. Nach erfolgreichem Versand wird der Bericht als gesendet
markiert, damit er nicht doppelt kommt. Versand über `hermes send --to signal` wie mail_meldung.py.
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).parent
BERICHT_PFAD = HIER / "hw_bericht.json"
MAX_ZEILEN = 10

log = logging.getLogger("hw_bericht")

_STEUER = re.compile(r"[\x00-\x1f\x7f​-‏‪-‮⁦-⁩]")


def bereinige(text, limit: int) -> str:
    """Steuerzeichen und Richtungsumschalter raus, Whitespace glätten, kürzen, lange Striche ersetzen."""
    t = _STEUER.sub(" ", str(text or ""))
    t = " ".join(t.split()).replace("–", "-").replace("—", "-")
    return t if len(t) <= limit else t[: limit - 1].rstrip() + "…"


def _tag(iso: str) -> str:
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d.%m.")
    except (TypeError, ValueError):
        return "?"


def _abschnitt(titel: str, eintraege: list, zeile, zusatz: str = "") -> list[str]:
    if not eintraege:
        return []
    zeilen = [f"{titel} ({len(eintraege)}){zusatz}:"]
    zeilen += [zeile(e) for e in eintraege[:MAX_ZEILEN]]
    if len(eintraege) > MAX_ZEILEN:
        zeilen.append(f"... und {len(eintraege) - MAX_ZEILEN} weitere")
    return zeilen


def baue_nachricht(bericht: dict, status: str, grund: str = "") -> str | None:
    teile = ("eingetragen", "geaendert", "abgesagt", "pruefen", "neue_seiten", "quellfehler", "verwaist",
             "ohne_ergebnis", "fehler")
    if not any(bericht.get(k) for k in teile):
        return None
    try:
        erstellt = datetime.fromisoformat(bericht.get("erstellt", "")).strftime("%d.%m.")
    except ValueError:
        erstellt = ""
    zeilen = [f"Holzwurm-Import {erstellt}".strip()]
    if status == "live":
        zeilen.append("Ist live.")
    elif status == "fehler":
        zeilen.append(f"Achtung, NICHT live: {bereinige(grund, 80) or 'Fehler bei der Veröffentlichung'}")

    def termin(e):
        return f"- {_tag(e.get('datum'))} {bereinige(e.get('name'), 70)}"

    zeilen += _abschnitt("Eingetragen", bericht.get("eingetragen", []), termin)
    zeilen += _abschnitt("Geändert", bericht.get("geaendert", []),
                         lambda e: f"{termin(e)}: {bereinige(e.get('was'), 40)}")
    zeilen += _abschnitt("Abgesagt", bericht.get("abgesagt", []), termin)
    zeilen += _abschnitt("Zur Prüfung", bericht.get("pruefen", []),
                         lambda e: f"{termin(e)} ({bereinige(e.get('grund'), 60)})", ", hw_pruefliste.md")
    zeilen += _abschnitt("Neue Terminseiten", bericht.get("neue_seiten", []), lambda e: f"- {bereinige(e, 80)}")
    zeilen += _abschnitt("Quellen prüfen", bericht.get("quellfehler", []), lambda e: f"- {bereinige(e, 120)}")
    zeilen += _abschnitt("Korrektur greift nicht mehr", bericht.get("verwaist", []), termin)
    zeilen += _abschnitt("Ohne Ergebnis, Mail von Hand ansehen", bericht.get("ohne_ergebnis", []),
                         lambda e: f"- {bereinige(e, 80)}")
    zeilen += _abschnitt("Fehler", bericht.get("fehler", []), lambda e: f"- {bereinige(e, 100)}")
    return "\n".join(zeilen)


def _hermes() -> str:
    if os.environ.get("HW_HERMES_BIN"):
        return os.environ["HW_HERMES_BIN"]
    lokal = Path.home() / ".local/bin/hermes"  # launchd kennt ~/.local/bin nicht im PATH
    return str(lokal) if lokal.exists() else "hermes"


def sende_signal(text: str) -> bool:
    try:
        r = subprocess.run([_hermes(), "send", "--to", "signal", text], capture_output=True, text=True, timeout=120)
    except Exception as e:
        log.error("Signal-Versand fehlgeschlagen: %s", type(e).__name__)
        return False
    if r.returncode != 0:
        log.error("Signal-Versand Exit %s", r.returncode)
        return False
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", choices=["live", "unveraendert", "fehler"], required=True)
    ap.add_argument("--grund", default="", help="Kurzer Fehlertext bei --status fehler")
    ap.add_argument("--pfad", default=str(BERICHT_PFAD))
    ap.add_argument("--dry-run", action="store_true", help="Text ausgeben, nicht senden, nicht markieren")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    pfad = Path(args.pfad)
    try:
        bericht = json.loads(pfad.read_text(encoding="utf-8"))
    except FileNotFoundError:
        log.info("Kein HW-Bericht vorhanden")
        return 0
    except ValueError:
        log.error("HW-Bericht nicht lesbar")
        return 1
    if bericht.get("gesendet"):
        log.info("HW-Bericht bereits gesendet (%s)", bericht["gesendet"])
        return 0
    text = baue_nachricht(bericht, args.status, args.grund)
    if args.dry_run:
        print(text or "(nichts zu melden)")
        return 0
    if text and not sende_signal(text):
        return 1
    bericht["gesendet"] = datetime.now().isoformat(timespec="seconds") if text else "nichts zu melden"
    tmp = pfad.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(bericht, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, pfad)
    log.info("HW-Bericht %s", "per Signal gesendet" if text else "leer, nichts gesendet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
