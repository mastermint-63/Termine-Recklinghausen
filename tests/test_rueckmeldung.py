"""Tests für rueckmeldung.py: Sammelmail je Adresse, Kopfzeilen, Fehlerbehandlung, Text.

Ohne Netz und ohne echte Adressen: Fake-SMTP, Domains aus .example.
"""
import json
import smtplib
from datetime import datetime, timedelta

import pytest

import hw_import as hw
import kalender_eingang as ke
import rueckmeldung as rm

ALIAS = "sammeladresse@empfang.example"
RALF = "ralf@redaktion.example"
JETZT = datetime(2026, 10, 13, 6, 30)
BIS = JETZT.isoformat(timespec="seconds")


class FakeSMTP:
    def __init__(self, fehler=None, login_fehler=None):
        self.gesendet, self.fehler, self.login_fehler = [], fehler, login_fehler

    def starttls(self, context=None):
        assert context is not None and context.check_hostname
        pass

    def login(self, u, p):
        if self.login_fehler:
            raise self.login_fehler

    def send_message(self, msg, from_addr=None, to_addrs=None):
        if self.fehler:
            raise self.fehler
        self.gesendet.append((msg, from_addr, to_addrs))

    def quit(self):
        pass


def _db(tmp_path, eintraege):
    """eintraege: [(schluessel, adresse, message_id, betreff, inhalt, angelegt)]"""
    con = hw.state_db(tmp_path / "s.db")
    with con:
        con.executemany("insert into rueckmeldungen (schluessel, adresse, message_id, betreff, inhalt, angelegt) "
                        "values (?,?,?,?,?,?)", [(s, a, m, b, json.dumps(i), t) for s, a, m, b, i, t in eintraege])
    return con


def _eintrag(n=1, adresse=RALF, angelegt="2026-10-13T00:31:00", betreff="AW: Lesung", inhalt=None):
    return (f"kalender:m{n}@redaktion.example", adresse, f"m{n}@redaktion.example", betreff,
            inhalt or {"eingetragen": [{"datum": "2026-10-23", "name": f"Lesung {n}"}]}, angelegt)


def _sende(con, smtp, **kw):
    return rm.sende_offene(con, bis=kw.pop("bis", BIS), alias=ALIAS, user="u", passwort="p",
                           redaktion=kw.pop("redaktion", {RALF}), verbinde=lambda: smtp, jetzt=JETZT, **kw)


def _status(con):
    return {s: (g, v) for s, g, v in con.execute("select schluessel, gesendet, versuche from rueckmeldungen")}


# --------------------------------------------------------------------------- Senden

def test_eine_sammelmail_je_adresse(tmp_path):
    con = _db(tmp_path, [_eintrag(1), _eintrag(2, angelegt="2026-10-13T00:32:00"),
                         _eintrag(3, adresse="erich@redaktion.example")])
    smtp = FakeSMTP()
    erg = _sende(con, smtp, redaktion={RALF, "erich@redaktion.example"})
    assert erg == {"gesendet": 2, "fehler": 0, "fehlertexte": []}
    an_ralf = next(m for m, _f, to in smtp.gesendet if to == [RALF])
    text = an_ralf.get_content()
    assert "Lesung 1" in text and "Lesung 2" in text and "deine Mails" in text
    assert an_ralf["In-Reply-To"] == "<m2@redaktion.example>"  # jüngste Mail
    assert an_ralf["Subject"] == "Holzwurm-Kalender: Rückmeldung zu deinen Mails"
    assert all(g and g[0].startswith("2026-10-13") for g in _status(con).values())


def test_kopfzeilen_und_betreff(tmp_path):
    con = _db(tmp_path, [_eintrag(1, betreff="AW: Re: WG: Lesung im Café")])
    smtp = FakeSMTP()
    _sende(con, smtp)
    msg, von, an = smtp.gesendet[0]
    assert von == ALIAS and an == [RALF]
    assert msg["Subject"] == "Re: Lesung im Café"
    assert msg["Auto-Submitted"] == "auto-replied"
    assert msg["X-Auto-Response-Suppress"] == "All"
    assert msg[ke.KOPF_RUECKMELDUNG] == "1"
    assert ALIAS in msg["From"] and "Holzwurm-Kalender" in msg["From"]
    assert msg["Message-ID"].endswith("@empfang.example>")
    eigene = con.execute("select eigene_id from rueckmeldungen").fetchone()[0]
    assert eigene == msg["Message-ID"]
    assert msg.get_content().startswith(ke.MARKER)


def test_kaputte_message_id_ohne_in_reply_to(tmp_path):
    e = list(_eintrag(1))
    e[2] = "a b\r\nBcc: x@evil.example"
    con = _db(tmp_path, [tuple(e)])
    smtp = FakeSMTP()
    _sende(con, smtp)
    assert smtp.gesendet[0][0]["In-Reply-To"] is None


def test_zeilenumbruch_im_betreff_wird_entschaerft(tmp_path):
    con = _db(tmp_path, [_eintrag(1, betreff="Lesung\r\nBcc: x@evil.example")])
    smtp = FakeSMTP()
    _sende(con, smtp)
    msg = smtp.gesendet[0][0]
    assert msg["Bcc"] is None and "\n" not in msg["Subject"]


def test_nur_eintraege_vor_bis(tmp_path):
    con = _db(tmp_path, [_eintrag(1, angelegt="2026-10-13T06:35:00")])
    smtp = FakeSMTP()
    assert _sende(con, smtp)["gesendet"] == 0 and not smtp.gesendet


def test_verfallene_werden_geschlossen(tmp_path):
    alt = (JETZT - timedelta(days=8)).isoformat(timespec="seconds")
    con = _db(tmp_path, [_eintrag(1, angelegt=alt)])
    smtp = FakeSMTP()
    _sende(con, smtp)
    assert not smtp.gesendet and _status(con)["kalender:m1@redaktion.example"][0] == "verfallen"


def test_adresse_nicht_mehr_in_redaktion(tmp_path):
    con = _db(tmp_path, [_eintrag(1)])
    smtp = FakeSMTP()
    _sende(con, smtp, redaktion={"erich@redaktion.example"})
    assert not smtp.gesendet
    assert _status(con)["kalender:m1@redaktion.example"][0] == "nicht mehr in der Redaktionsliste"


def test_limit_pro_lauf(tmp_path):
    adressen = {f"r{i}@redaktion.example" for i in range(12)}
    con = _db(tmp_path, [_eintrag(i, adresse=a) for i, a in enumerate(sorted(adressen))])
    smtp = FakeSMTP()
    assert _sende(con, smtp, redaktion=adressen)["gesendet"] == rm.MAX_MAILS_PRO_LAUF == 10


def test_loginfehler_erhoeht_versuche_nicht(tmp_path):
    con = _db(tmp_path, [_eintrag(1)])
    smtp = FakeSMTP(login_fehler=smtplib.SMTPAuthenticationError(535, b"nope"))
    erg = _sende(con, smtp)
    assert erg["fehler"] == 1 and erg["gesendet"] == 0
    assert _status(con)["kalender:m1@redaktion.example"] == (None, 0)


def test_empfaenger_abgelehnt_zaehlt_versuche_und_schliesst_nach_drei(tmp_path):
    con = _db(tmp_path, [_eintrag(1)])
    smtp = FakeSMTP(fehler=smtplib.SMTPRecipientsRefused({RALF: (550, b"no such user")}))
    for _ in range(2):
        _sende(con, smtp)
    assert _status(con)["kalender:m1@redaktion.example"] == (None, 2)
    _sende(con, smtp)
    assert _status(con)["kalender:m1@redaktion.example"] == ("abgelehnt", 3)


def test_absender_abgelehnt_ist_globaler_fehler(tmp_path):
    con = _db(tmp_path, [_eintrag(1), _eintrag(2, adresse="erich@redaktion.example")])
    smtp = FakeSMTP(fehler=smtplib.SMTPSenderRefused(553, b"alias not allowed", ALIAS))
    erg = _sende(con, smtp, redaktion={RALF, "erich@redaktion.example"})
    assert erg["fehler"] == 1
    assert all(v == (None, 0) for v in _status(con).values())


def test_abbruch_waehrend_des_sendens_gilt_als_gesendet(tmp_path):
    con = _db(tmp_path, [_eintrag(1)])
    smtp = FakeSMTP(fehler=smtplib.SMTPServerDisconnected("weg"))
    erg = _sende(con, smtp)
    assert erg["fehler"] == 1
    assert _status(con)["kalender:m1@redaktion.example"][0] == "laeuft"
    assert _sende(con, FakeSMTP())["gesendet"] == 0  # nicht noch einmal


# --------------------------------------------------------------------------- Text

def test_text_abschnitte_und_link(tmp_path, monkeypatch):
    monkeypatch.setattr(rm, "HIER", tmp_path)
    (tmp_path / "termine_re_2026_10.html").write_text("x")
    inhalt = {"eingetragen": [{"datum": "2026-10-24", "name": "Lesung"}],
              "geaendert": [{"datum": "2026-10-23", "name": "Konzert", "was": "uhrzeit 19:30"}],
              "abgesagt": [], "bekannt": [{"datum": "2026-10-25", "name": "Markt"}],
              "pruefen": [{"datum": "2026-10-26", "name": "Fest"}],
              "verworfen": [{"datum": "2026-01-01", "name": "Alt", "grund": "liegt in der Vergangenheit"}]}
    text = rm.baue_text([inhalt])
    assert text.startswith(ke.MARKER)
    assert "Eingetragen:\n- Sa 24.10. Lesung" in text
    assert "Geändert:\n- Fr 23.10. Konzert: Uhrzeit 19:30" in text
    assert "Abgesagt" not in text
    assert "Stand schon im Kalender:\n- So 25.10. Markt" in text
    assert "Wird noch von Hand geprüft:\n- Mo 26.10. Fest" in text
    assert "- Do 01.01. Alt (liegt in der Vergangenheit)" in text
    assert "termine_re_2026_10.html" in text and "deine Mail " in text


def test_link_faellt_auf_startseite_zurueck(tmp_path, monkeypatch):
    monkeypatch.setattr(rm, "HIER", tmp_path)
    text = rm.baue_text([{"eingetragen": [{"datum": "2027-12-24", "name": "X"}]}])
    assert "https://termine.holzwurm-recklinghausen.de/\n" in text


def test_titel_werden_bereinigt():
    text = rm.baue_text([{"eingetragen": [{"datum": "2026-10-24", "name": "Lesung‮ – mit\nUmbruch"}]}])
    assert "‮" not in text and "–" not in text and "Lesung - mit Umbruch" in text


@pytest.mark.parametrize("betreff,erwartet", [
    ("AW: Re: Termin", "Re: Termin"), ("Fwd: WG: X", "Re: X"), ("", "Re: deine Mail an den Holzwurm-Kalender"),
])
def test_betreff(betreff, erwartet):
    assert rm.betreff_fuer([betreff]) == erwartet


# --------------------------------------------------------------------------- Anrede, Tageslink, Schluss (13.10.2026)

def test_anrede_mit_vorname():
    inhalt = {"eingetragen": [{"datum": "2026-10-24", "name": "Lesung"}]}
    assert "\nHallo Erich,\n" in rm.baue_text([inhalt], vorname="Erich")
    assert "\nHallo,\n" in rm.baue_text([inhalt])
    assert "\nHallo Er ich,\n" in rm.baue_text([inhalt], vorname="Er\nich")  # kein Zeilenumbruch im Namen


def test_lese_vornamen():
    assert rm.lese_vornamen("a@x.example=Erich, B@Y.example = Ralf ,kaputt,=leer,c@z.example=") == \
        {"a@x.example": "Erich", "b@y.example": "Ralf"}
    assert rm.lese_vornamen("") == {}


def test_link_springt_zum_tag(tmp_path, monkeypatch):
    monkeypatch.setattr(rm, "HIER", tmp_path)
    (tmp_path / "termine_re_2026_10.html").write_text('<div class="datum-gruppe" id="datum-2026-10-24">')
    text = rm.baue_text([{"eingetragen": [{"datum": "2026-10-24", "name": "Lesung"}]}])
    assert "termine_re_2026_10.html#datum-2026-10-24\n" in text


def test_link_ohne_tag_auf_der_seite_nur_monat(tmp_path, monkeypatch):
    monkeypatch.setattr(rm, "HIER", tmp_path)
    (tmp_path / "termine_re_2026_10.html").write_text("x")
    text = rm.baue_text([{"eingetragen": [{"datum": "2026-10-24", "name": "Lesung"}]}])
    assert "termine_re_2026_10.html\n" in text


def test_link_auch_bei_absage(tmp_path, monkeypatch):
    monkeypatch.setattr(rm, "HIER", tmp_path)
    (tmp_path / "termine_re_2026_10.html").write_text('id="datum-2026-10-23"')
    text = rm.baue_text([{"abgesagt": [{"datum": "2026-10-23", "name": "Konzert"}]}])
    assert "termine_re_2026_10.html#datum-2026-10-23\n" in text


def test_schlusssatz_laedt_zu_neuen_mails_ein():
    text = rm.baue_text([{"eingetragen": [{"datum": "2026-10-24", "name": "Lesung"}]}])
    assert "nicht direkt" not in text
    assert "Neue Termine, Korrekturen und Absagen schickst du einfach wieder an diese Adresse." in text


def test_sammelmail_nutzt_vorname(tmp_path):
    con = _db(tmp_path, [_eintrag(1)])
    smtp = FakeSMTP()
    _sende(con, smtp, vornamen={RALF: "Ralf"})
    assert "\nHallo Ralf,\n" in smtp.gesendet[0][0].get_content()
