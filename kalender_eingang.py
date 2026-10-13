"""Kalender-Eingang: Mails an die Sammeladresse der Redaktion per IMAP lesen (iCloud).

Eine iCloud-Serverregel verschiebt Mails an den Alias in den Ordner "Kalender-Eingang".
Merkmal ist der Ordner, nicht die Empfängerzeile (iCloud setzt kein Delivered-To).

Lesen: SELECT readonly, BODY.PEEK[] (iCloud liefert bei RFC822 leer), keine Flags.
Ablage: raeume_eingang() verschiebt ausgewertete Mails nach "Kalender-Eingang/bearbeitet"
(UID COPY, UID STORE \\Deleted, UID EXPUNGE je Mail; iCloud kennt kein MOVE). Spec:
docs/superpowers/specs/2026-10-12-kalender-eingang-rueckmeldung-design.md

Adressen (Alias, Redaktion) stehen nur in der Env (HW_ENV_FILE), nie im Repo:
  ICLOUD_USER, ICLOUD_APP_PASSWORD   eigenes app-spezifisches Passwort nur für diesen Job
  KALENDER_ALIAS                     die Sammeladresse (Pflicht für "vertraut", Absender der Rückmeldung)
  HW_REDAKTION                       kommagetrennte Absenderadressen der Redaktion
"""

import email
import email.policy
import imaplib
import logging
import re
import ssl
from datetime import date, datetime, timedelta
from email.utils import getaddresses, parsedate_to_datetime

import hw_import as hw

IMAP_HOST = "imap.mail.me.com"
IMAP_PORT = 993
ORDNER = "Kalender-Eingang"
ZIELORDNER = "Kalender-Eingang/bearbeitet"
FENSTER_TAGE = 30
KONTO = "kalender"
# Erste Zeile jeder Rückmeldung (rueckmeldung.py). Ab hier wird der Text eingehender Mails abgeschnitten,
# damit zitierte Rückmeldungen und das darunter zitierte Original nicht erneut ausgewertet werden.
MARKER = "Automatische Rückmeldung des Holzwurm-Kalenders"
KOPF_RUECKMELDUNG = "X-Holzwurm-Rueckmeldung"

# iCloud schreibt seine Prüfergebnisse unter diesen Kennungen (geprüft 11.10.2026)
_ICLOUD_DKIM = "dkim-verifier.icloud.com"
_ICLOUD_DMARC = "dmarc.icloud.com"
_ICLOUD_SPF = "spf.icloud.com"

log = logging.getLogger("hw_import.kalender")


class EingangFehler(Exception):
    """Login oder Ordnerzugriff fehlgeschlagen; der Import läuft mit den anderen Quellen weiter."""


# --------------------------------------------------------------------------- Absender und Vertrauen

def lese_redaktion(roh: str | None) -> set[str]:
    return {a.strip().lower() for a in (roh or "").split(",") if a.strip()}


def _absender_adresse(msg) -> str | None:
    """Genau eine Absenderadresse, sonst None (mehrere From-Header/-Adressen gelten als unbekannt)."""
    froms = msg.get_all("From") or []
    if len(froms) != 1:
        return None
    adressen = [a for _n, a in getaddresses([str(froms[0])]) if a]
    if len(adressen) != 1 or "@" not in adressen[0]:
        return None
    return adressen[0].strip().lower()


def _icloud_ergebnisse(msg) -> dict[str, str]:
    """Prüfergebnisse von iCloud -> {"dkim": "pass header.d=...", "dmarc": "..."}.

    iCloud setzt seinen Block oberhalb der Absender-Header und schließt ihn mit dem SPF-Ergebnis.
    Gewertet wird je Prüfart nur der erste Eintrag bis einschließlich des ersten SPF-Eintrags.
    Ein Absender kann so keinen eigenen "dkim=pass"-Header unterschieben: Er stünde darunter.
    Fehlt die SPF-Zeile, ist die Grenze unklar: dann wird nichts gewertet.
    """
    ergebnisse: dict[str, str] = {}
    for wert in msg.get_all("Authentication-Results") or []:
        wert = " ".join(str(wert).split())
        kennung, _, rest = wert.partition(";")
        kennung = kennung.strip().lower()
        if kennung == _ICLOUD_DKIM:
            ergebnisse.setdefault("dkim", rest.strip())
        elif kennung == _ICLOUD_DMARC:
            ergebnisse.setdefault("dmarc", rest.strip())
        elif kennung == _ICLOUD_SPF:
            return ergebnisse
    return {}


def _passt_zur_domain(ergebnis: str, methode: str, schluessel: str, domain: str) -> bool:
    """'dkim=pass header.d=gmx.de' -> True, wenn header.d die Absenderdomain ist (oder deren Elterndomain)."""
    if not re.match(rf"{methode}=pass\b", ergebnis or "", re.I):
        return False
    m = re.search(rf"\b{re.escape(schluessel)}=([^\s;]+)", ergebnis, re.I)
    if not m:
        return False
    d = m.group(1).lower().strip(".")
    return domain == d or domain.endswith("." + d) and d.count(".") >= 1


def _hat_laengenbegrenzung(msg) -> bool:
    """DKIM-Signatur mit l=-Tag: signiert nur den Anfang des Texts, Angehängtes wäre ungeprüft."""
    return any(re.search(r"(?:^|;)\s*l\s*=\s*\d+", " ".join(str(v).split()))
               for v in msg.get_all("DKIM-Signature") or [])


def _fremdes_postfach(dkim_ergebnis: str, adresse: str) -> bool:
    """header.i nennt ein anderes Postfach als From (z.B. fremdes Konto derselben Freemail-Domain)."""
    m = re.search(r"\bheader\.i=([^\s;]+)", dkim_ergebnis or "", re.I)
    if not m or "@" not in m.group(1):
        return False
    lokal = m.group(1).split("@", 1)[0]
    return bool(lokal) and m.group(1).lower() != adresse


def _an_alias(msg, alias: str) -> bool:
    empfaenger = getaddresses([str(v) for k in ("To", "Cc") for v in msg.get_all(k) or []])
    return any(a.strip().lower() == alias for _n, a in empfaenger)


def vertrauensstufe(msg, redaktion: set[str], alias: str) -> tuple[str, str]:
    """-> (stufe, grund). Stufen: "vertraut", "redaktion_unauth", "unbekannt".

    DKIM/DMARC belegen nur die Domain. Zusätzlich darf header.i kein anderes Postfach nennen,
    und keine Signatur darf per l=-Tag nur einen Teil des Texts abdecken. Der Alias muss in To/Cc
    stehen: Eine alte, signierte Mail eines Redaktionsmitglieds, an den Alias weitergeschickt
    (DKIM-Replay), gilt sonst als vertraut.
    """
    adresse = _absender_adresse(msg)
    if not adresse or adresse not in redaktion:
        return "unbekannt", "Absender nicht in der Redaktionsliste"
    alias = (alias or "").strip().lower()
    if not alias:
        return "redaktion_unauth", "KALENDER_ALIAS fehlt in der Env"
    if not _an_alias(msg, alias):
        return "redaktion_unauth", "Alias steht nicht in To/Cc (weitergeleitete oder Bcc-Mail)"
    domain = adresse.rsplit("@", 1)[1]
    if _hat_laengenbegrenzung(msg):
        return "redaktion_unauth", "DKIM-Signatur deckt nur einen Teil der Mail ab (l=-Tag)"
    ergebnisse = _icloud_ergebnisse(msg)
    if _fremdes_postfach(ergebnisse.get("dkim", ""), adresse):
        return "redaktion_unauth", "DKIM-Signatur gehört zu einem anderen Postfach als der Absender"
    if _passt_zur_domain(ergebnisse.get("dkim", ""), "dkim", "header.d", domain):
        return "vertraut", "Redaktion, DKIM bestanden"
    if _passt_zur_domain(ergebnisse.get("dmarc", ""), "dmarc", "header.from", domain):
        return "vertraut", "Redaktion, DMARC bestanden"
    return "redaktion_unauth", "Absender nicht authentifiziert (kein DKIM/DMARC-Pass)"


def ist_massenmail(msg) -> bool:
    return bool(msg.get("List-Id") or msg.get("List-Unsubscribe"))


_AUTO_PRECEDENCE = {"auto_reply", "bulk", "junk", "list"}


def ist_automatisch(msg, eigene: set[str]) -> str | None:
    """Grund, wenn die Mail automatisch erzeugt ist (Abwesenheitsnotiz, Unzustellbar, eigene Rückmeldung).

    Solche Mails gehen nicht ans Modell und werden nie beantwortet (Schleifenschutz).
    `eigene`: Alias und Login-Adresse in Kleinschreibung.
    """
    if msg.get_content_type() == "multipart/report":
        return "Zustellbericht"
    adresse = _absender_adresse(msg) or ""
    if adresse.split("@", 1)[0] in ("mailer-daemon", "postmaster"):
        return "Zustellbericht"
    if adresse and adresse in eigene:
        return "eigene Adresse als Absender"
    if msg.get(KOPF_RUECKMELDUNG):
        return "eigene Rückmeldung"
    auto = str(msg.get("Auto-Submitted", "")).strip().lower()
    if auto and auto != "no":
        return "Auto-Submitted"
    if msg.get("X-Autoreply") or msg.get("X-Autorespond"):
        return "Abwesenheitsnotiz"
    if str(msg.get("Precedence", "")).strip().lower() in _AUTO_PRECEDENCE:
        return "Precedence"
    return None


def schneide_zitat(text: str) -> str:
    """Text ab der ersten Zeile mit MARKER abschneiden (zitierte Rückmeldung samt Original darunter)."""
    zeilen = text.split("\n")
    for i, z in enumerate(zeilen):
        if MARKER in " ".join(z.split()):
            return "\n".join(zeilen[:i])
    return text


# --------------------------------------------------------------------------- MIME

def mime_teile(msg) -> list[tuple[str, bytes]]:
    """MIME-Mail -> [(contentType, body)], gleiche Struktur wie die eM-Client-Teile."""
    teile = []
    for teil in msg.walk():
        if teil.is_multipart():
            continue
        ct = teil.get_content_type()
        charset = teil.get_content_charset()
        body = teil.get_payload(decode=True)
        if body is None:
            continue
        teile.append((f"{ct}; charset={charset}" if charset else ct, body))
    return teile


def _datum(msg) -> datetime:
    try:
        d = parsedate_to_datetime(str(msg.get("Date", "")))
        return d.astimezone().replace(tzinfo=None) if d.tzinfo else d
    except (TypeError, ValueError):
        return datetime.now()


def _message_id(msg) -> str:
    return str(msg.get("Message-ID", "")).strip().strip("<> ")


def schluessel(msg, uid: int) -> str:
    """State-Schlüssel wie Mail.schluessel, ohne die Anhänge zu zerlegen."""
    return f"{KONTO}:{_message_id(msg) or 'id-' + str(uid)}"


def baue_mail(msg, uid: int, redaktion: set[str], alias: str = "", mit_inhalt: bool = True) -> hw.Mail:
    text, bilder, pdfs = (hw.werte_teile_aus(mime_teile(msg), schnitt=schneide_zitat) if mit_inhalt
                          else ("", [], []))
    stufe, grund = vertrauensstufe(msg, redaktion, alias)
    return hw.Mail(konto=KONTO, id=uid, message_id=_message_id(msg),
                   datum=_datum(msg), betreff=" ".join(str(msg.get("Subject", "")).split()),
                   absender=" ".join(str(msg.get("From", "")).split()), text=text, bilder=bilder, pdfs=pdfs,
                   vertrauen=stufe, vertrauen_grund=grund)


def parse(roh: bytes):
    return email.message_from_bytes(roh, policy=email.policy.default)


# --------------------------------------------------------------------------- IMAP

def _imap_datum(d: date) -> str:
    """IMAP-Datum mit englischem Monatsnamen, unabhängig von der Locale."""
    return f"{d.day:02d}-{_MONATE[d.month - 1]}-{d.year}"


_MONATE = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _verbinde():
    try:
        return imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=ssl.create_default_context(), timeout=60)
    except OSError as e:
        raise EingangFehler(f"IMAP nicht erreichbar ({type(e).__name__})") from None


def hole_mails(user: str, passwort: str, heute: date | None = None,
               ordner: str = ORDNER) -> list[tuple[int, object, bool]]:
    """Alle Mails der letzten FENSTER_TAGE Tage -> [(uid, msg, ist_massenmail)]. Wirft EingangFehler.

    Die Anhänge werden hier noch nicht zerlegt (baue_mail()), damit bereits verarbeitete Mails,
    Massenmails und unbekannte Absender über dem Limit keine Umwandlungen (sips) auslösen.
    """
    if not user or not passwort:
        raise EingangFehler("ICLOUD_USER/ICLOUD_APP_PASSWORD nicht gesetzt")
    seit = (heute or date.today()) - timedelta(days=FENSTER_TAGE)
    try:
        conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=ssl.create_default_context(), timeout=60)
    except OSError as e:
        raise EingangFehler(f"IMAP nicht erreichbar ({type(e).__name__})") from None
    try:
        try:
            conn.login(user, passwort)
        except imaplib.IMAP4.error:
            raise EingangFehler("IMAP-Login abgelehnt") from None
        typ, _ = conn.select(f'"{ordner}"', readonly=True)
        if typ != "OK":
            raise EingangFehler(f"Ordner {ordner!r} nicht gefunden")
        typ, daten = conn.uid("SEARCH", None, "UNDELETED", "SINCE", _imap_datum(seit))
        if typ != "OK":
            raise EingangFehler("IMAP-Suche fehlgeschlagen")
        ergebnis = []
        for uid in (daten[0] or b"").split():
            typ, teile = conn.uid("FETCH", uid, "(BODY.PEEK[])")
            roh = next((t[1] for t in teile or [] if isinstance(t, tuple) and len(t) > 1), None)
            if typ != "OK" or not roh:
                log.error("Kalender-Eingang: Mail UID %s nicht lesbar", uid.decode())
                continue
            msg = parse(roh)
            ergebnis.append((int(uid), msg, ist_massenmail(msg)))
        return ergebnis
    except (imaplib.IMAP4.error, OSError) as e:
        raise EingangFehler(f"IMAP-Fehler ({type(e).__name__})") from None
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def _uids(daten) -> list[bytes]:
    return (daten[0] or b"").split() if daten else []


def _message_ids(conn, uids: list[bytes]) -> dict[int, str]:
    """UID -> Message-ID (ohne <>), nur Kopfzeile, ohne \\Seen zu setzen."""
    if not uids:
        return {}
    typ, teile = conn.uid("FETCH", b",".join(uids).decode(), "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])")
    if typ != "OK":
        raise EingangFehler("IMAP-Abruf der Kopfzeilen fehlgeschlagen")
    ergebnis = {}
    for t in teile or []:
        if not isinstance(t, tuple) or len(t) < 2:
            continue
        m = re.search(rb"UID (\d+)", t[0])
        if m:
            ergebnis[int(m.group(1))] = _message_id(parse(t[1]))
    return ergebnis


def _ziel_anlegen(conn):
    typ, daten = conn.list('""', f'"{ZIELORDNER}"')
    if typ == "OK" and any(d for d in daten or []):
        return
    typ, _ = conn.create(f'"{ZIELORDNER}"')
    if typ != "OK":
        raise EingangFehler(f"Ordner {ZIELORDNER!r} nicht anlegbar")
    conn.subscribe(f'"{ZIELORDNER}"')


def raeume_eingang(user: str, passwort: str, ist_erledigt, heute: date | None = None,
                   dry_run: bool = False, verbinde=None) -> dict:
    """Ausgewertete Mails nach ZIELORDNER verschieben -> {"verschoben": [schluessel], "zu_alt": n, "fehler": []}.

    Die Mails werden in DIESER Sitzung neu ermittelt (keine UIDs aus dem Lesedurchgang, die zwischen
    zwei Sitzungen ungültig werden könnten). Verschoben wird, wessen Schlüssel ist_erledigt() bestätigt;
    Mails ohne Message-ID nie (ihr Schlüssel hinge an der UID).

    Je Mail: UID COPY, nur bei OK UID STORE +FLAGS.SILENT (\\Deleted), nur bei OK UID EXPUNGE <uid>.
    Nie close() und nie nacktes expunge(): Beides entfernt ALLE \\Deleted-Mails im Ordner, auch fremde.
    Wirft EingangFehler bei Login/Ordner; Fehler einzelner Mails landen in "fehler".
    """
    if not user or not passwort:
        raise EingangFehler("ICLOUD_USER/ICLOUD_APP_PASSWORD nicht gesetzt")
    heute = heute or date.today()
    seit = heute - timedelta(days=FENSTER_TAGE)
    ergebnis = {"verschoben": [], "zu_alt": 0, "fehler": []}
    conn = (verbinde or _verbinde)()
    try:
        try:
            conn.login(user, passwort)
        except imaplib.IMAP4.error:
            raise EingangFehler("IMAP-Login abgelehnt") from None
        typ, _ = conn.select(f'"{ORDNER}"', readonly=dry_run)
        if typ != "OK":
            raise EingangFehler(f"Ordner {ORDNER!r} nicht gefunden")
        typ, daten = conn.uid("SEARCH", None, "UNDELETED", "BEFORE", _imap_datum(seit))
        ergebnis["zu_alt"] = len(_uids(daten)) if typ == "OK" else 0
        typ, daten = conn.uid("SEARCH", None, "UNDELETED", "SINCE", _imap_datum(seit))
        if typ != "OK":
            raise EingangFehler("IMAP-Suche fehlgeschlagen")
        faellig = [(uid, f"{KONTO}:{mid}") for uid, mid in sorted(_message_ids(conn, _uids(daten)).items())
                   if mid and ist_erledigt(f"{KONTO}:{mid}")]
        if dry_run or not faellig:
            ergebnis["verschoben"] = [s for _u, s in faellig] if dry_run else []
            return ergebnis
        _ziel_anlegen(conn)
        for uid, schl in faellig:
            typ, daten = conn.uid("COPY", str(uid), f'"{ZIELORDNER}"')
            if typ != "OK":
                ergebnis["fehler"].append(f"Kopieren fehlgeschlagen (UID {uid})")
                continue
            log.info("Kalender-Eingang: UID %s kopiert %s", uid, (daten[0] or b"")[:60] if daten else b"")
            typ, _ = conn.uid("STORE", str(uid), "+FLAGS.SILENT", r"(\Deleted)")
            if typ != "OK":
                ergebnis["fehler"].append(f"Markieren fehlgeschlagen (UID {uid}), Kopie liegt schon in bearbeitet")
                continue
            typ, _ = conn.uid("EXPUNGE", str(uid))
            if typ != "OK":
                ergebnis["fehler"].append(f"Entfernen fehlgeschlagen (UID {uid}), Kopie liegt schon in bearbeitet")
                continue
            ergebnis["verschoben"].append(schl)
        return ergebnis
    except (imaplib.IMAP4.error, OSError) as e:
        raise EingangFehler(f"IMAP-Fehler ({type(e).__name__})") from None
    finally:
        try:
            conn.logout()
        except Exception:
            pass
