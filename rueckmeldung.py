#!/usr/bin/env python3
"""Rückmeldung an die Redaktion: was aus ihren Mails an den Kalender-Eingang geworden ist.

hw_import.py (00:30) merkt in hw_state.db (Tabelle rueckmeldungen) je ausgewerteter Mail vertrauter
Absender vor, was eingetragen, geändert, abgesagt, schon bekannt, zur Prüfung oder nicht übernommen ist.
update.sh (06:30) ruft nach dem Push, vor hw_bericht.py:
  python3 rueckmeldung.py --status live|unveraendert|fehler --bis <Startzeit von update.sh>

Eine Sammelmail je Adresse, fester Text (kein Modell), per iCloud-SMTP vom Alias. Bewusste Ausnahme von
der Regel "E-Mails niemals selbst senden" (Entscheidung FS 12.10.2026, Spec
docs/superpowers/specs/2026-10-12-kalender-eingang-rueckmeldung-design.md).

Env (HW_ENV_FILE): ICLOUD_USER, ICLOUD_APP_PASSWORD, KALENDER_ALIAS, HW_REDAKTION,
optional HW_VORNAMEN ("adresse=Vorname,adresse=Vorname", für die Anrede).
"""

import argparse
import email.policy
import json
import logging
import os
import re
import smtplib
import ssl
import sys
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path

import hw_bericht
import hw_import as hw
import kalender_eingang as ke

HIER = Path(__file__).parent
SMTP_HOST = "smtp.mail.me.com"
SMTP_PORT = 587
BASIS_URL = "https://termine.holzwurm-recklinghausen.de/"
MAX_MAILS_PRO_LAUF = 10
MAX_ZEILEN = 10
MAX_VERSUCHE = 3
VERFALL_TAGE = 7

log = logging.getLogger("rueckmeldung")

_WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
_PRAEFIX = re.compile(r"^\s*(?:(?:re|aw|wg|fwd?|wtr|antw)\s*:\s*)+", re.I)
_MESSAGE_ID = re.compile(r"^[\x21-\x3b\x3d\x3f-\x7e]{1,250}$")
_FELDER = {"uhrzeit": "Uhrzeit", "ort": "Ort", "link": "Link", "datum": "Datum"}


# --------------------------------------------------------------------------- Text

def _tag(iso: str) -> str:
    try:
        d = datetime.strptime(iso, "%Y-%m-%d")
    except (TypeError, ValueError):
        return "?"
    return f"{_WOCHENTAGE[d.weekday()]} {d:%d.%m.}"


def _was(was: str) -> str:
    return re.sub(r"(^|, )([a-z]+)\b", lambda m: m.group(1) + _FELDER.get(m.group(2), m.group(2)), was or "")


def lese_vornamen(text: str) -> dict[str, str]:
    """HW_VORNAMEN "adresse=Vorname,…" -> {adresse (klein): Vorname}. Kaputte Einträge werden übersprungen."""
    namen = {}
    for teil in (text or "").split(","):
        adresse, _, vorname = teil.partition("=")
        adresse, vorname = adresse.strip().lower(), vorname.strip()
        if "@" in adresse and vorname:
            namen[adresse] = vorname
    return namen


def _link(inhalte: list[dict]) -> str:
    """Monatsseite des ersten Termins, mit Sprung auf den Tag, wenn die Seite ihn enthält."""
    import app
    for i in inhalte:
        for e in i.get("eingetragen", []) + i.get("geaendert", []) + i.get("abgesagt", []) + i.get("bekannt", []):
            try:
                d = datetime.strptime(e.get("datum", ""), "%Y-%m-%d")
            except ValueError:
                continue
            datei = app.dateiname_fuer_monat(d.year, d.month)
            if (HIER / datei).exists():
                anker = f"datum-{d:%Y-%m-%d}"
                seite = (HIER / datei).read_text(encoding="utf-8", errors="replace")
                return BASIS_URL + datei + (f"#{anker}" if f'id="{anker}"' in seite else "")
    return BASIS_URL


def baue_text(inhalte: list[dict], vorname: str = "") -> str:
    """Inhalte aller Mails einer Adresse -> Mailtext. Erste Zeile ist der MARKER (Zitat-Schnitt)."""
    def termin(e):
        return f"- {_tag(e.get('datum'))} {hw_bericht.bereinige(e.get('name'), 90)}"

    abschnitte = [
        ("Eingetragen", "eingetragen", termin),
        ("Geändert", "geaendert", lambda e: f"{termin(e)}: {hw_bericht.bereinige(_was(e.get('was')), 80)}"),
        ("Abgesagt", "abgesagt", termin),
        ("Stand schon im Kalender", "bekannt", termin),
        ("Wird noch von Hand geprüft", "pruefen", termin),
        ("Nicht übernommen", "verworfen", lambda e: f"{termin(e)} ({hw_bericht.bereinige(e.get('grund'), 60)})"),
    ]
    mehrere = len(inhalte) > 1
    vorname = hw_bericht.bereinige(vorname, 40)
    zeilen = [ke.MARKER, "", f"Hallo {vorname}," if vorname else "Hallo,", "",
              f"danke für deine Mail{'s' if mehrere else ''} an den Holzwurm-Kalender. "
              f"{'Sie sind' if mehrere else 'Sie ist'} bearbeitet:", ""]
    for titel, schluessel, zeile in abschnitte:
        eintraege = [e for i in inhalte for e in i.get(schluessel, [])]
        if not eintraege:
            continue
        zeilen.append(f"{titel}:")
        zeilen += [zeile(e) for e in eintraege[:MAX_ZEILEN]]
        if len(eintraege) > MAX_ZEILEN:
            zeilen.append(f"... und {len(eintraege) - MAX_ZEILEN} weitere")
    zeilen += ["", f"Zum Kalender: {_link(inhalte)}", "",
               "Neue Termine, Korrekturen und Absagen schickst du einfach wieder an diese Adresse."]
    return "\n".join(zeilen) + "\n"


def betreff_fuer(betreffs: list[str]) -> str:
    if len(betreffs) > 1:
        return "Holzwurm-Kalender: Rückmeldung zu deinen Mails"
    rest = hw_bericht.bereinige(_PRAEFIX.sub("", betreffs[0] if betreffs else ""), 120)
    return f"Re: {rest or 'deine Mail an den Holzwurm-Kalender'}"


def baue_mail(alias: str, adresse: str, zeilen: list[tuple], vorname: str = "") -> EmailMessage:
    """zeilen: [(schluessel, message_id, betreff, inhalt)], aufsteigend nach angelegt."""
    msg = EmailMessage(policy=email.policy.SMTP)  # lehnt CR/LF in Kopfzeilen ab
    msg["From"] = formataddr(("Holzwurm-Kalender", alias))
    msg["To"] = adresse
    msg["Subject"] = betreff_fuer([b for _s, _m, b, _i in zeilen])
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=alias.rsplit("@", 1)[1])
    letzte = zeilen[-1][1] or ""
    if _MESSAGE_ID.match(letzte):
        msg["In-Reply-To"] = f"<{letzte}>"
        msg["References"] = f"<{letzte}>"
    msg["Auto-Submitted"] = "auto-replied"  # RFC 3834: Abwesenheitsnotizen antworten nicht
    msg["X-Auto-Response-Suppress"] = "All"
    msg[ke.KOPF_RUECKMELDUNG] = "1"
    msg.set_content(baue_text([i for _s, _m, _b, i in zeilen], vorname))
    return msg


# --------------------------------------------------------------------------- Senden

def _schliesse(con, schluessel: list[str], gesendet: str, eigene_id: str | None = None):
    with con:
        con.executemany("update rueckmeldungen set gesendet=?, eigene_id=coalesce(?, eigene_id) where schluessel=?",
                        [(gesendet, eigene_id, s) for s in schluessel])


def _verbinde_smtp():
    return smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=60)


def sende_offene(con, bis: str, alias: str, user: str, passwort: str, redaktion: set[str],
                 verbinde=None, jetzt: datetime | None = None, vornamen: dict[str, str] | None = None) -> dict:
    """Offene Rückmeldungen (angelegt vor `bis`) senden -> {"gesendet": n, "fehler": m, "fehlertexte": []}.

    Verbindungs-, Login- und Absenderfehler sind global: Lauf endet, nichts wird hochgezählt.
    Ablehnung des Empfängers zählt `versuche`, ab MAX_VERSUCHE geschlossen ("abgelehnt").
    Vor dem Senden steht "laeuft" in der DB: Bricht die Verbindung währenddessen ab, gilt die Mail
    als gesendet (lieber einmal zu wenig als doppelt).
    """
    jetzt = jetzt or datetime.now()
    erg = {"gesendet": 0, "fehler": 0, "fehlertexte": []}

    def fehler(text):
        log.error("Rückmeldung: %s", text)
        erg["fehler"] += 1
        erg["fehlertexte"].append(text)

    grenze = (jetzt - timedelta(days=VERFALL_TAGE)).isoformat(timespec="seconds")
    with con:
        con.execute("update rueckmeldungen set gesendet='verfallen' where gesendet is null and angelegt < ?", (grenze,))
    zeilen = con.execute("select schluessel, adresse, message_id, betreff, inhalt from rueckmeldungen "
                         "where gesendet is null and angelegt < ? order by angelegt", (bis,)).fetchall()
    gruppen: dict[str, list] = {}
    for s, a, m, b, i in zeilen:
        gruppen.setdefault(a, []).append((s, m, b, json.loads(i)))
    if not gruppen:
        return erg
    if not alias or "@" not in alias:
        fehler("KALENDER_ALIAS fehlt, nichts gesendet")
        return erg

    try:
        smtp = (verbinde or _verbinde_smtp)()
        smtp.starttls(context=ssl.create_default_context())  # Zertifikat und Hostname prüfen
        smtp.login(user, passwort)
    except (OSError, smtplib.SMTPException) as e:
        fehler(f"SMTP-Anmeldung fehlgeschlagen ({type(e).__name__})")
        return erg
    try:
        for adresse, eintraege in list(gruppen.items())[:MAX_MAILS_PRO_LAUF]:
            schluessel = [s for s, _m, _b, _i in eintraege]
            if adresse not in redaktion:
                _schliesse(con, schluessel, "nicht mehr in der Redaktionsliste")
                continue
            msg = baue_mail(alias, adresse, eintraege, (vornamen or {}).get(adresse.lower(), ""))
            _schliesse(con, schluessel, "laeuft", msg["Message-ID"])
            try:
                smtp.send_message(msg, from_addr=alias, to_addrs=[adresse])
            except smtplib.SMTPRecipientsRefused:
                with con:
                    con.executemany("update rueckmeldungen set versuche=versuche+1, "
                                    "gesendet=case when versuche+1>=? then 'abgelehnt' else null end "
                                    "where schluessel=?", [(MAX_VERSUCHE, s) for s in schluessel])
                fehler("Empfänger abgelehnt")
                continue
            except smtplib.SMTPSenderRefused:
                _schliesse(con, schluessel, None)  # wieder offen, nichts hochgezählt
                fehler("iCloud lehnt den Alias als Absender ab")
                break
            except (OSError, smtplib.SMTPException) as e:
                fehler(f"Versand abgebrochen ({type(e).__name__}), Mail gilt als gesendet")
                break
            _schliesse(con, schluessel, jetzt.isoformat(timespec="seconds"))
            erg["gesendet"] += 1
            log.info("Rückmeldung gesendet (%d Mail(s) zusammengefasst)", len(eintraege))
        if len(gruppen) > MAX_MAILS_PRO_LAUF:
            log.warning("Limit von %d Rückmeldungen erreicht, Rest im nächsten Lauf", MAX_MAILS_PRO_LAUF)
    finally:
        try:
            smtp.quit()
        except Exception:
            pass
    return erg


# --------------------------------------------------------------------------- Bericht

def trage_in_bericht_ein(erg: dict, pfad: Path, dry_run: bool = False):
    """Ergebnis in hw_bericht.json für den Signal-Bericht. Ist der schon raus, Fehler selbst melden."""
    if not erg["gesendet"] and not erg["fehler"]:
        return
    try:
        bericht = json.loads(pfad.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        bericht = None
    if bericht is not None and not bericht.get("gesendet"):
        bericht["rueckmeldungen"] = {"gesendet": erg["gesendet"], "fehler": erg["fehler"]}
        if not dry_run:
            _schreibe(pfad, bericht)
        return
    if erg["fehler"] and not dry_run:
        hw_bericht.sende_signal("Holzwurm-Rückmeldung an die Redaktion: " +
                                "; ".join(hw_bericht.bereinige(t, 80) for t in erg["fehlertexte"][:3]))


def _schreibe(pfad: Path, daten: dict):
    tmp = pfad.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, pfad)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", choices=["live", "unveraendert", "fehler"], required=True)
    ap.add_argument("--bis", required=True, help="nur Rückmeldungen, die vor diesem Zeitpunkt (ISO) angelegt wurden")
    ap.add_argument("--dry-run", action="store_true", help="Texte zeigen, nichts senden, nichts markieren")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    con = hw.state_db()
    if args.dry_run:
        zeilen = con.execute("select adresse, message_id, betreff, inhalt from rueckmeldungen "
                             "where gesendet is null and angelegt < ? order by angelegt", (args.bis,)).fetchall()
        gruppen: dict[str, list] = {}
        for a, m, b, i in zeilen:
            gruppen.setdefault(a, []).append(("", m, b, json.loads(i)))
        vornamen = lese_vornamen(hw._env("HW_VORNAMEN"))
        for nr, (adresse, eintraege) in enumerate(gruppen.items(), 1):
            print(f"--- Rückmeldung {nr} ({len(eintraege)} Mail(s)) | {betreff_fuer([b for _s, _m, b, _i in eintraege])}")
            print(baue_text([i for _s, _m, _b, i in eintraege], vornamen.get(adresse.lower(), "")))
        if not gruppen:
            print("(keine offenen Rückmeldungen)")
        return 0
    if args.status == "fehler":
        log.info("Veröffentlichung fehlgeschlagen: Rückmeldungen warten auf den nächsten Lauf")
        return 0
    erg = sende_offene(con, args.bis, hw._env("KALENDER_ALIAS").strip().lower(), hw._env("ICLOUD_USER"),
                       hw._env("ICLOUD_APP_PASSWORD"), ke.lese_redaktion(hw._env("HW_REDAKTION")),
                       vornamen=lese_vornamen(hw._env("HW_VORNAMEN")))
    trage_in_bericht_ein(erg, hw.BERICHT_PFAD)
    return 1 if erg["fehler"] and not erg["gesendet"] else 0


if __name__ == "__main__":
    sys.exit(main())
