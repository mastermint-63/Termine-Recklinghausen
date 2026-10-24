"""Zwei Fehler aus der Rückmeldung an Erich (24.10.2026):

1. Mehrtägige Termine: "23. bis 25.10. Grillstand der Tafel" kam am 24.10. an, das Modell meldete nur den ersten Tag,
   der Import verwarf ihn als vergangen. Jetzt meldet das Modell `bis`, laufende Termine werden ab heute eingetragen.
2. "steht schon so im Kalender" nannte den Titel aus der Mail, nicht den Eintrag im Kalender. Jetzt steht der
   gefundene Kalendereintrag in der Rückmeldung.
"""
from datetime import date, datetime

import hw_import as hw
import rueckmeldung as rm
from scraper import Termin

HEUTE = date(2026, 10, 24)  # Samstag


def _mail(text="23. bis 25.10. Grillstand der Tafel"):
    return hw.Mail(konto="kalender", id=1, message_id="m1@x", datum=datetime(2026, 10, 23, 14, 15), betreff="Kalender",
                   absender="E <e@x.example>", text=text, vertrauen="vertraut")


def _termin(**kw):
    t = {"name": "Grillstand der Tafel", "datum": "2026-10-23", "bis": "2026-10-25", "uhrzeit": "17:30",
         "ort": "Gymnasialkirche", "eindeutig": True, "in_recklinghausen": True,
         "beleg": "23. bis 25.10. Grillstand der Tafel", "kategorie": "Fest"}
    t.update(kw)
    return t


def _bewerte(t, dublette=None):
    return hw.bewerte_termin(t, _mail(), HEUTE, lambda e, m: False, lambda e: dublette, lambda e: None)


# --------------------------------------------------------------------------- mehrtägig

def test_laufender_mehrtaegiger_termin_wird_ab_heute_eingetragen():
    status, grund, e = _bewerte(_termin())
    assert status == "auto" and e["datum"] == "2026-10-24"
    assert "läuft bis 25.10." in grund


def test_mehrtaegiger_termin_endet_heute():
    status, _, e = _bewerte(_termin(datum="2026-10-22", bis="2026-10-24"))
    assert status == "auto" and e["datum"] == "2026-10-24"


def test_vorbei_bleibt_vorbei():
    for bis in ("2026-10-23", "", "kaputt", None):
        status, grund, e = _bewerte(_termin(bis=bis))
        assert status == "verwerfen" and "Vergangenheit" in grund and e is None, bis


def test_zukuenftiger_mehrtaegiger_termin_bleibt_am_ersten_tag():
    status, _, e = _bewerte(_termin(datum="2026-10-30", bis="2026-11-01", beleg="30.10. bis 1.11."))
    assert status == "auto" and e["datum"] == "2026-10-30"


def test_wochentag_wird_am_ersten_tag_geprueft():
    """Beleg nennt den Freitag (erster Tag), eingetragen wird Samstag: keine Wochentag-Warnung."""
    t = _termin(beleg="Freitag bis Sonntag, 23. bis 25. Oktober")
    status, _, e = hw.bewerte_termin(t, _mail("Freitag bis Sonntag, 23. bis 25. Oktober"), HEUTE,
                                     lambda e, m: False, lambda e: None, lambda e: None)
    assert status == "auto" and "Wochentag" not in e.get("hw_warnung", "")


def test_schema_und_prompt_kennen_bis():
    felder = hw.TOOL["input_schema"]["properties"]["termine"]["items"]["properties"]
    assert "bis" in felder
    assert "`bis`" in hw.SYSTEM


# --------------------------------------------------------------------------- Dublette mit Kalendereintrag

def test_dublette_liefert_den_kalendereintrag(monkeypatch):
    tag = datetime(2026, 10, 28)
    bestehend = [Termin(name="Nachts im Museum", datum=tag, uhrzeit="17:30 Uhr", ort="RETRO STATION", link="",
                        quelle="stadt-re"),
                 Termin(name="ROADTRIP OMAN BY TRIKE", datum=tag, uhrzeit="17:00 Uhr", ort="Börster Weg 38a",
                        link="", quelle="adfc")]
    monkeypatch.setattr(hw, "lade_bestehende", lambda d: list(bestehend))
    monkeypatch.setattr(hw, "lade_json", lambda: [])
    eintrag = {"name": '"Oman by Trike": Radreisebericht', "datum": "2026-10-28", "uhrzeit": "18:00",
               "ort": "ADFC-Infoladen", "link": "", "beschreibung": "", "kategorie": "Vortrag"}
    treffer = hw.ist_dublette_im_kalender(eintrag)
    assert treffer and treffer.name == "ROADTRIP OMAN BY TRIKE"
    assert hw.ist_dublette_im_kalender({**eintrag, "name": "Kürbisschnitzen"}) is None


def test_bericht_nennt_kalendereintrag(monkeypatch):
    oman = Termin(name="ROADTRIP OMAN BY TRIKE", datum=datetime(2026, 10, 28), uhrzeit="17:00 Uhr", ort="", link="",
                  quelle="adfc")
    monkeypatch.setattr(hw, "ist_dublette_im_kalender", lambda e: oman if "Oman" in e["name"] else None)
    monkeypatch.setattr(hw, "finde_konflikt", lambda e: None)
    monkeypatch.setattr(hw, "analysiere", lambda c, m, h: {"termine": [
        _termin(name='"Oman by Trike": Radreisebericht', datum="2026-10-28", bis="", beleg="BILD")]})
    res = hw.verarbeite_mail(None, _mail(), HEUTE, True, [], [], hw.neuer_bericht())
    v = res["bericht"]["verworfen"][0]
    assert v["im_kalender"] == "ROADTRIP OMAN BY TRIKE, 17:00 Uhr"
    inhalt = hw.rueckmeldung_inhalt(res["bericht"])
    assert inhalt["verworfen"][0] == {"datum": "2026-10-28", "name": '"Oman by Trike": Radreisebericht',
                                      "grund": "steht schon im Kalender",
                                      "im_kalender": "ROADTRIP OMAN BY TRIKE, 17:00 Uhr"}


def test_kalendereintrag_ohne_uhrzeit():
    t = Termin(name="Markt", datum=datetime(2026, 10, 28), uhrzeit="siehe Website", ort="", link="", quelle="x")
    assert hw.kalender_zeile(t) == "Markt"
    assert hw.kalender_zeile(True) == ""


def test_rueckmeldung_zeigt_kalendereintrag():
    inhalt = {"verworfen": [{"datum": "2026-10-28", "name": '"Oman by Trike": Radreisebericht',
                             "grund": "steht schon im Kalender", "im_kalender": "ROADTRIP OMAN BY TRIKE, 17:00 Uhr"},
                            {"datum": "2026-10-26", "name": "Alt", "grund": "steht schon im Kalender"}]}
    text = rm.baue_text([inhalt])
    assert ('- Mi 28.10. "Oman by Trike": Radreisebericht (steht schon im Kalender als: '
            'ROADTRIP OMAN BY TRIKE, 17:00 Uhr)') in text
    assert "- Mo 26.10. Alt (steht schon im Kalender)" in text
    assert "schon so im Kalender" not in text
