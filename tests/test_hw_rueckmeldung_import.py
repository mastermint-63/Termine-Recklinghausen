"""Tests für den Import-Teil der Rückmeldung: Bericht pro Mail, Kurzgründe, State-Reihenfolge, Vormerken.

Ohne Netz und ohne echte Adressen: Modell, IMAP und Kalenderseiten werden ersetzt, Domains aus .example.
"""
import json
import sys
from datetime import date, timedelta
from email.message import EmailMessage

import pytest

import hw_import as hw
import kalender_eingang as ke

ALIAS = "sammeladresse@empfang.example"
HEUTE = date.today()
IN_10 = (HEUTE + timedelta(days=10)).isoformat()


# --------------------------------------------------------------------------- Kurzgründe

@pytest.mark.parametrize("roh,kurz", [
    ("Termin liegt in der Vergangenheit", "liegt in der Vergangenheit"),
    ("steht schon im Kalender", "steht schon im Kalender"),
    ("korrektur: Angaben stehen bereits so im Kalender", "steht schon so im Kalender"),
    ("absage: bereits als abgesagt eingetragen", "steht schon so im Kalender"),
    ("ausgeschlossene Gruppierung (AfD-Filter)", "wird nach den Regeln des Kalenders nicht aufgenommen"),
    ("kein gültiges Datum ('<script>')", "Angaben reichen nicht aus"),
    ("", "Angaben reichen nicht aus"),
])
def test_kurzgrund_nur_aus_fester_liste(roh, kurz):
    assert hw.kurzgrund(roh) == kurz


# --------------------------------------------------------------------------- Bericht pro Mail

def _mail(vertrauen="vertraut", konto="kalender"):
    return hw.Mail(konto=konto, id=1, message_id="m1@redaktion.example", datum=hw.datetime.now(),
                   betreff="Termine", absender="Ralf <ralf@redaktion.example>",
                   text="Am Freitag Lesung im Altstadtcafé, Recklinghausen, 19 Uhr", vertrauen=vertrauen)


def _termin(name="Lesung", datum=IN_10, **kw):
    t = {"name": name, "datum": datum, "uhrzeit": "19:00", "ort": "Altstadtcafé", "eindeutig": True,
         "in_recklinghausen": True, "beleg": "Lesung im Altstadtcafé"}
    t.update(kw)
    return t


@pytest.fixture
def ohne_kalender(monkeypatch):
    monkeypatch.setattr(hw, "ist_dublette_im_kalender", lambda e: False)
    monkeypatch.setattr(hw, "finde_konflikt", lambda e: None)
    monkeypatch.setattr(hw, "wochentag_passt", lambda b, d: True)


def test_verarbeite_mail_liefert_bericht_pro_mail(monkeypatch, ohne_kalender):
    monkeypatch.setattr(hw, "analysiere", lambda c, m, h: {"termine": [
        _termin(), _termin("Alt", "2020-01-01"), _termin("Doppelt")]})
    eintraege = [{"name": "Doppelt", "datum": IN_10}]
    bericht = hw.neuer_bericht()
    res = hw.verarbeite_mail(None, _mail(), HEUTE, False, eintraege, [], bericht)
    eigen = res["bericht"]
    assert [e["name"] for e in eigen["eingetragen"]] == ["Lesung"]
    assert [e["name"] for e in eigen["bekannt"]] == ["Doppelt"]
    assert eigen["verworfen"][0]["name"] == "Alt"
    # Gesamtbericht bekommt dieselben Einträge, aber keinen neuen Schlüssel
    assert [e["name"] for e in bericht["eingetragen"]] == ["Lesung"]
    assert "bekannt" not in bericht


def test_rueckmeldung_inhalt_mit_kurzgruenden():
    eigen = {"eingetragen": [{"datum": IN_10, "name": "Lesung"}], "geaendert": [], "abgesagt": [],
             "bekannt": [], "pruefen": [{"datum": IN_10, "name": "X", "grund": "Beleg-Zitat nicht im Mailtext"}],
             "verworfen": [{"datum": "2020-01-01", "name": "Alt", "grund": "Termin liegt in der Vergangenheit"}]}
    inhalt = hw.rueckmeldung_inhalt(eigen)
    assert inhalt["pruefen"] == [{"datum": IN_10, "name": "X"}]
    assert inhalt["verworfen"][0]["grund"] == "liegt in der Vergangenheit"


def test_rueckmeldung_inhalt_leer_ist_none():
    assert hw.rueckmeldung_inhalt({"eingetragen": [], "verworfen": []}) is None


# --------------------------------------------------------------------------- State

def test_schreibe_state_ueberschreibt_rueckmeldung_nicht(tmp_path):
    con = hw.state_db(tmp_path / "s.db")
    m = _mail()
    hw.schreibe_state(con, [(m, "{}")], [(m, "ralf@redaktion.example", {"eingetragen": [1]})])
    con.execute("update rueckmeldungen set gesendet='2026-10-12T06:31:00'")
    con.commit()
    hw.schreibe_state(con, [(m, "{}")], [(m, "ralf@redaktion.example", {"eingetragen": [2]})])
    zeile = con.execute("select inhalt, gesendet from rueckmeldungen").fetchone()
    assert json.loads(zeile[0]) == {"eingetragen": [1]} and zeile[1]
    assert hw.ist_verarbeitet(con, m.schluessel)


# --------------------------------------------------------------------------- main() mit Kalender-Eingang

def _imap_mail(von="Ralf <ralf@redaktion.example>", mid="<m1@redaktion.example>", extra=()):
    m = EmailMessage()
    m["Authentication-Results"] = "dkim-verifier.icloud.com; dkim=pass header.d=redaktion.example"
    m["Authentication-Results"] = "spf.icloud.com; spf=pass smtp.mailfrom=x@redaktion.example"
    m["From"] = von
    m["To"] = ALIAS
    m["Subject"] = "Termin"
    m["Date"] = "Mon, 12 Oct 2026 10:00:00 +0200"
    m["Message-ID"] = mid
    for k, v in extra:
        m[k] = v
    m.set_content("Am Freitag Lesung im Altstadtcafé, Recklinghausen, 19 Uhr")
    return m


@pytest.fixture
def lauf(tmp_path, monkeypatch, ohne_kalender):
    for name, datei in [("JSON_PFAD", "m.json"), ("KORREKTUREN_PFAD", "k.json"), ("PRUEFLISTE_MD", "p.md"),
                        ("BERICHT_PFAD", "b.json"), ("STATE_PFAD", "s.db"), ("NEUE_QUELLEN_MD", "n.md")]:
        monkeypatch.setattr(hw, name, tmp_path / datei)
    env = {"ANTHROPIC_API_KEY": "test", "ICLOUD_USER": "login@icloud.example", "ICLOUD_APP_PASSWORD": "x",
           "HW_REDAKTION": "ralf@redaktion.example", "KALENDER_ALIAS": ALIAS}
    monkeypatch.setattr(hw, "_env", lambda n: env.get(n, ""))
    monkeypatch.setattr(hw, "finde_verwaiste_korrekturen", lambda k, h: [])
    analysiert, geraeumt = [], []
    monkeypatch.setattr(hw, "analysiere", lambda c, m, h: analysiert.append(m.schluessel) or {"termine": [_termin()]})

    def raeume(user, pw, ist_erledigt, heute=None, dry_run=False, verbinde=None):
        geraeumt.append(ist_erledigt("kalender:m1@redaktion.example"))
        return {"verschoben": [], "zu_alt": 0, "fehler": []}
    monkeypatch.setattr(ke, "raeume_eingang", raeume)

    def starte(mails, *argv):
        monkeypatch.setattr(hw, "hole_kalender_mails", lambda heute, bericht, uid=None, ordner=ke.ORDNER:
                            [(i + 1, m, ke.ist_massenmail(m)) for i, m in enumerate(mails)])
        monkeypatch.setattr(sys, "argv", ["hw_import.py", "--nur-kalender", *argv])
        rc = hw.main()
        return rc, hw.state_db()
    return starte, analysiert, geraeumt


def test_vertraute_mail_wird_vorgemerkt_und_dann_geraeumt(lauf):
    starte, analysiert, geraeumt = lauf
    rc, con = starte([_imap_mail()])
    assert rc == 0 and analysiert == ["kalender:m1@redaktion.example"]
    zeile = con.execute("select adresse, message_id, inhalt from rueckmeldungen").fetchone()
    assert zeile[0] == "ralf@redaktion.example" and zeile[1] == "m1@redaktion.example"
    assert json.loads(zeile[2])["eingetragen"][0]["name"] == "Lesung"
    assert geraeumt == [True]  # beim Räumen ist die Mail schon als verarbeitet markiert


def test_absturz_vor_dem_speichern_markiert_nichts(lauf, monkeypatch):
    starte, _a, geraeumt = lauf

    def kaputt(_e):
        raise OSError("Platte voll")
    monkeypatch.setattr(hw, "speichere_json", kaputt)
    with pytest.raises(OSError):
        starte([_imap_mail()])
    con = hw.state_db()
    assert not hw.ist_verarbeitet(con, "kalender:m1@redaktion.example")
    assert con.execute("select count(*) from rueckmeldungen").fetchone()[0] == 0
    assert geraeumt == []


def test_automatische_mail_geht_nicht_ans_modell(lauf):
    starte, analysiert, _g = lauf
    _rc, con = starte([_imap_mail(extra=[("Auto-Submitted", "auto-replied")])])
    assert analysiert == []
    assert con.execute("select ergebnis from verarbeitet").fetchone()[0] == "automatisch"
    assert con.execute("select count(*) from rueckmeldungen").fetchone()[0] == 0


def test_unbekannter_absender_bekommt_keine_rueckmeldung(lauf):
    starte, analysiert, _g = lauf
    _rc, con = starte([_imap_mail(von="Wer <wer@anders.example>")])
    assert analysiert and con.execute("select count(*) from rueckmeldungen").fetchone()[0] == 0


def test_force_merkt_nicht_vor(lauf):
    starte, analysiert, _g = lauf
    _rc, con = starte([_imap_mail()], "--force")
    assert analysiert and con.execute("select count(*) from rueckmeldungen").fetchone()[0] == 0


def test_dry_run_schreibt_nichts_und_raeumt_nicht(lauf):
    starte, analysiert, geraeumt = lauf
    _rc, con = starte([_imap_mail()], "--dry-run")
    assert analysiert and geraeumt == []
    assert con.execute("select count(*) from verarbeitet").fetchone()[0] == 0


def test_gleiche_mail_doppelt_im_eingang_nur_einmal(lauf):
    starte, analysiert, _g = lauf
    starte([_imap_mail(), _imap_mail()])
    assert analysiert == ["kalender:m1@redaktion.example"]
