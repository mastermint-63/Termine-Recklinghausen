"""Kalender-Eingang: Mails an die Sammeladresse der Redaktion per IMAP lesen (iCloud).

Eine iCloud-Serverregel verschiebt Mails an den Alias in den Ordner "Kalender-Eingang".
Merkmal ist der Ordner, nicht die Empfängerzeile (iCloud setzt kein Delivered-To).

Strikt lesend: SELECT readonly, BODY.PEEK[] (iCloud liefert bei RFC822 leer).
Keine Flags, kein Verschieben, kein Löschen.

Adressen (Alias, Redaktion) stehen nur in der Env (HW_ENV_FILE), nie im Repo:
  ICLOUD_USER, ICLOUD_APP_PASSWORD   eigenes app-spezifisches Passwort nur für diesen Job
  HW_REDAKTION                       kommagetrennte Absenderadressen der Redaktion
"""

import email
import email.policy
import imaplib
import logging
import re
from datetime import date, datetime, timedelta
from email.utils import getaddresses, parsedate_to_datetime

import hw_import as hw

IMAP_HOST = "imap.mail.me.com"
IMAP_PORT = 993
ORDNER = "Kalender-Eingang"
FENSTER_TAGE = 30
KONTO = "kalender"

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


def vertrauensstufe(msg, redaktion: set[str]) -> tuple[str, str]:
    """-> (stufe, grund). Stufen: "vertraut", "redaktion_unauth", "unbekannt".

    DKIM/DMARC belegen nur die Domain. Zusätzlich darf header.i kein anderes Postfach nennen,
    und keine Signatur darf per l=-Tag nur einen Teil des Texts abdecken.
    """
    adresse = _absender_adresse(msg)
    if not adresse or adresse not in redaktion:
        return "unbekannt", "Absender nicht in der Redaktionsliste"
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


def baue_mail(msg, uid: int, redaktion: set[str]) -> hw.Mail:
    text, bilder, pdfs = hw.werte_teile_aus(mime_teile(msg))
    stufe, grund = vertrauensstufe(msg, redaktion)
    return hw.Mail(konto=KONTO, id=uid, message_id=str(msg.get("Message-ID", "")).strip().strip("<> "),
                   datum=_datum(msg), betreff=" ".join(str(msg.get("Subject", "")).split()),
                   absender=" ".join(str(msg.get("From", "")).split()), text=text, bilder=bilder, pdfs=pdfs,
                   vertrauen=stufe, vertrauen_grund=grund)


def parse(roh: bytes):
    return email.message_from_bytes(roh, policy=email.policy.default)


# --------------------------------------------------------------------------- IMAP

def hole_mails(user: str, passwort: str, redaktion: set[str], heute: date | None = None,
               ordner: str = ORDNER) -> list[tuple[hw.Mail, bool]]:
    """Alle Mails der letzten FENSTER_TAGE Tage -> [(Mail, ist_massenmail)]. Wirft EingangFehler."""
    if not user or not passwort:
        raise EingangFehler("ICLOUD_USER/ICLOUD_APP_PASSWORD nicht gesetzt")
    seit = (heute or date.today()) - timedelta(days=FENSTER_TAGE)
    try:
        conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=60)
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
        typ, daten = conn.uid("SEARCH", None, "SINCE", seit.strftime("%d-%b-%Y"))
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
            ergebnis.append((baue_mail(msg, int(uid), redaktion), ist_massenmail(msg)))
        return ergebnis
    except (imaplib.IMAP4.error, OSError) as e:
        raise EingangFehler(f"IMAP-Fehler ({type(e).__name__})") from None
    finally:
        try:
            conn.logout()
        except Exception:
            pass
