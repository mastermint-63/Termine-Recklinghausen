"""Tests für Ablage (Verschieben nach bearbeitet), Vorfilter, Zitat-Schnitt und Alias-Prüfung im Kalender-Eingang.

Ohne Netz und ohne echte Adressen: Fake-IMAP, Domains aus .example.
"""
from datetime import date
from email.message import EmailMessage

import pytest

import hw_import as hw
import kalender_eingang as ke

ALIAS = "sammeladresse@empfang.example"
REDAKTION = {"ralf@redaktion.example"}


# --------------------------------------------------------------------------- Fake-IMAP

class FakeIMAP:
    """Minimaler IMAP-Server: ein Eingang mit {uid: Message-ID oder None}, Zielordner optional vorhanden."""

    def __init__(self, mails: dict, ziel_vorhanden=False, copy_ok=True, store_ok=True, zu_alt=0):
        self.mails = dict(mails)
        self.ziel = {}
        self.ziel_vorhanden = ziel_vorhanden
        self.copy_ok, self.store_ok, self.zu_alt = copy_ok, store_ok, zu_alt
        self.befehle = []
        self.readonly = None

    def login(self, user, pw):
        self.befehle.append("LOGIN")

    def select(self, name, readonly=False):
        self.befehle.append(f"SELECT {name}")
        self.readonly = readonly
        return "OK", [str(len(self.mails)).encode()]

    def list(self, directory='""', pattern="*"):
        self.befehle.append(f"LIST {pattern}")
        if self.ziel_vorhanden and "bearbeitet" in pattern:
            return "OK", [b'() "/" "Kalender-Eingang/bearbeitet"']
        return "OK", [None]

    def create(self, name):
        self.befehle.append(f"CREATE {name}")
        self.ziel_vorhanden = True
        return "OK", [b"done"]

    def subscribe(self, name):
        self.befehle.append(f"SUBSCRIBE {name}")
        return "OK", [b"done"]

    def uid(self, cmd, *args):
        cmd = cmd.upper()
        self.befehle.append(f"UID {cmd} {' '.join(str(a) for a in args if a is not None)}")
        if cmd == "SEARCH":
            if "BEFORE" in args:
                return "OK", [" ".join(str(900 + i) for i in range(self.zu_alt)).encode()]
            assert "UNDELETED" in args
            return "OK", [" ".join(str(u) for u in sorted(self.mails)).encode()]
        if cmd == "FETCH":
            antwort = []
            for u in str(args[0]).split(","):
                mid = self.mails.get(int(u))
                kopf = f"Message-ID: <{mid}>\r\n\r\n".encode() if mid else b"\r\n"
                antwort += [(f"{u} (UID {u} BODY[HEADER.FIELDS (MESSAGE-ID)] {{{len(kopf)}}}".encode(), kopf), b")"]
            return "OK", antwort
        if cmd == "COPY":
            if not self.copy_ok:
                return "NO", [b"copy failed"]
            self.ziel[int(args[0])] = self.mails[int(args[0])]
            return "OK", [f"[COPYUID 1 {args[0]} 77] Completed".encode()]
        if cmd == "STORE":
            return ("OK", [b"done"]) if self.store_ok else ("NO", [b"store failed"])
        if cmd == "EXPUNGE":
            self.mails.pop(int(args[0]), None)
            return "OK", [b"done"]
        raise AssertionError(cmd)

    def close(self):
        self.befehle.append("CLOSE")

    def expunge(self):
        self.befehle.append("EXPUNGE")

    def logout(self):
        self.befehle.append("LOGOUT")


def _raeume(fake, erledigt, dry_run=False):
    return ke.raeume_eingang("u", "p", lambda s: s in erledigt, heute=date(2026, 10, 12),
                             dry_run=dry_run, verbinde=lambda: fake)


# --------------------------------------------------------------------------- Verschieben

def test_verschiebt_nur_erledigte_mails_in_richtiger_reihenfolge():
    fake = FakeIMAP({5: "a@x.example", 6: "b@x.example"}, ziel_vorhanden=True)
    erg = _raeume(fake, {"kalender:a@x.example"})
    assert erg["verschoben"] == ["kalender:a@x.example"]
    assert set(fake.mails) == {6}
    uid_befehle = [b for b in fake.befehle if b.startswith(("UID COPY", "UID STORE", "UID EXPUNGE"))]
    assert uid_befehle[0].startswith("UID COPY 5")
    assert uid_befehle[1].startswith("UID STORE 5 +FLAGS.SILENT")
    assert uid_befehle[2] == "UID EXPUNGE 5"
    assert fake.readonly is False


def test_nie_close_und_nie_nacktes_expunge():
    fake = FakeIMAP({5: "a@x.example"})
    _raeume(fake, {"kalender:a@x.example"})
    assert "CLOSE" not in fake.befehle
    assert "EXPUNGE" not in fake.befehle
    assert fake.befehle[-1] == "LOGOUT"


def test_zielordner_wird_angelegt_wenn_er_fehlt():
    fake = FakeIMAP({5: "a@x.example"})
    _raeume(fake, {"kalender:a@x.example"})
    assert 'CREATE "Kalender-Eingang/bearbeitet"' in fake.befehle


def test_copy_fehler_laesst_mail_unangetastet():
    fake = FakeIMAP({5: "a@x.example"}, ziel_vorhanden=True, copy_ok=False)
    erg = _raeume(fake, {"kalender:a@x.example"})
    assert erg["verschoben"] == [] and erg["fehler"]
    assert not any(b.startswith(("UID STORE", "UID EXPUNGE")) for b in fake.befehle)
    assert 5 in fake.mails


def test_store_fehler_ohne_expunge():
    fake = FakeIMAP({5: "a@x.example"}, ziel_vorhanden=True, store_ok=False)
    erg = _raeume(fake, {"kalender:a@x.example"})
    assert erg["verschoben"] == [] and erg["fehler"]
    assert not any(b.startswith("UID EXPUNGE") for b in fake.befehle)


def test_mail_ohne_message_id_wird_nie_verschoben():
    fake = FakeIMAP({5: None}, ziel_vorhanden=True)
    erg = _raeume(fake, {"kalender:id-5"})
    assert erg["verschoben"] == []
    assert 5 in fake.mails


def test_dry_run_verschiebt_nichts_und_legt_nichts_an():
    fake = FakeIMAP({5: "a@x.example"})
    erg = _raeume(fake, {"kalender:a@x.example"}, dry_run=True)
    assert erg["verschoben"] == ["kalender:a@x.example"]
    assert not any(b.startswith(("CREATE", "UID COPY", "UID STORE", "UID EXPUNGE")) for b in fake.befehle)
    assert fake.readonly is True


def test_nichts_zu_tun_legt_keinen_ordner_an():
    fake = FakeIMAP({5: "a@x.example"})
    erg = _raeume(fake, set())
    assert erg["verschoben"] == []
    assert not any(b.startswith("CREATE") for b in fake.befehle)


def test_zu_alte_mails_werden_gezaehlt():
    fake = FakeIMAP({}, zu_alt=3)
    assert _raeume(fake, set())["zu_alt"] == 3


# --------------------------------------------------------------------------- Vorfilter

def _mail(von="Ralf <ralf@redaktion.example>", to=ALIAS, extra=(), ct=None):
    m = EmailMessage()
    m["From"] = von
    m["To"] = to
    m["Subject"] = "Termin"
    m["Message-ID"] = "<abc@redaktion.example>"
    for k, v in extra:
        m[k] = v
    m.set_content("Am Freitag, 23.10.2026 um 19:00 Uhr Lesung im Altstadtcafé, Recklinghausen.")
    return m


@pytest.mark.parametrize("extra", [
    [("Auto-Submitted", "auto-replied")],
    [("X-Autoreply", "yes")],
    [("Precedence", "auto_reply")],
    [("Precedence", "junk")],
    [("X-Holzwurm-Rueckmeldung", "1")],
])
def test_automatische_mails_werden_erkannt(extra):
    assert ke.ist_automatisch(_mail(extra=extra), {ALIAS})


def test_auto_submitted_no_ist_normale_mail():
    assert ke.ist_automatisch(_mail(extra=[("Auto-Submitted", "no")]), {ALIAS}) is None


def test_normale_mail_ist_nicht_automatisch():
    assert ke.ist_automatisch(_mail(), {ALIAS}) is None


def test_unzustellbar_wird_erkannt():
    assert ke.ist_automatisch(_mail(von="Mail Delivery System <MAILER-DAEMON@relay.example>"), {ALIAS})
    m = EmailMessage()
    m["From"] = "x@relay.example"
    m.set_type("multipart/report")
    assert ke.ist_automatisch(m, {ALIAS})


def test_eigener_absender_wird_erkannt():
    assert ke.ist_automatisch(_mail(von=f"Holzwurm <{ALIAS}>"), {ALIAS})


# --------------------------------------------------------------------------- Zitat-Schnitt

def test_text_ab_marker_wird_abgeschnitten():
    text = f"Noch ein Termin am 30.10.\n\n> {ke.MARKER}\n> Eingetragen:\n> - Sa 24.10. Lesung"
    assert ke.schneide_zitat(text) == "Noch ein Termin am 30.10.\n"


def test_text_ohne_marker_bleibt():
    assert ke.schneide_zitat("Hallo\nTermin") == "Hallo\nTermin"


def test_baue_mail_schneidet_zitat_ab():
    m = _mail()
    m.set_content(f"Neuer Termin am Freitag, 30.10.2026 um 20 Uhr im Ratskeller.\n\n> {ke.MARKER}\n> - Sa 24.10. Alt")
    mail = ke.baue_mail(m, 1, REDAKTION, alias=ALIAS)
    assert "Ratskeller" in mail.text and "Alt" not in mail.text


# --------------------------------------------------------------------------- Alias in To/Cc

def _auth(domain="redaktion.example"):
    return [("Authentication-Results", f"dkim-verifier.icloud.com; dkim=pass header.d={domain}"),
            ("Authentication-Results", f"spf.icloud.com; spf=pass smtp.mailfrom=x@{domain}")]


def _signiert(to=ALIAS, cc=None):
    m = EmailMessage()
    for k, v in _auth():
        m[k] = v
    m["From"] = "Ralf <ralf@redaktion.example>"
    m["To"] = to
    if cc:
        m["Cc"] = cc
    m.set_content("x")
    return m


def test_vertraut_nur_mit_alias_in_to_oder_cc():
    assert ke.vertrauensstufe(_signiert(), REDAKTION, ALIAS)[0] == "vertraut"
    assert ke.vertrauensstufe(_signiert(to="jemand@anders.example", cc=f"H <{ALIAS.upper()}>"),
                              REDAKTION, ALIAS)[0] == "vertraut"
    stufe, grund = ke.vertrauensstufe(_signiert(to="jemand@anders.example"), REDAKTION, ALIAS)
    assert stufe == "redaktion_unauth" and "Alias" in grund


def test_ohne_alias_in_env_nie_vertraut():
    stufe, grund = ke.vertrauensstufe(_signiert(), REDAKTION, "")
    assert stufe == "redaktion_unauth" and "KALENDER_ALIAS" in grund


def test_werte_teile_aus_ohne_schnitt_unveraendert():
    text, _, _ = hw.werte_teile_aus([("text/plain; charset=utf-8", f"A\n{ke.MARKER}\nB".encode())])
    assert "B" in text
