"""Redaktionstermine untereinander: Der Generator vergleicht sie nur über den Titel (eine Quelle listet nichts doppelt).

Beim Import reicht das nicht: Hebberts Mail vom 30.10.2026 nennt "Feier zur Wintersonnenwende", im Kalender steht von
einer anderen Mail "Abend zur Wintersonnenwende" zur selben Uhrzeit. Solche Fälle prüft ist_dublette_im_kalender().
"""
from datetime import datetime

import app
import hw_import as hw
from scraper import Termin

TAG = datetime(2026, 12, 20)


def _bestehend(monkeypatch, name, uhrzeit, quelle="manuell"):
    t = Termin(name=name, datum=TAG, uhrzeit=uhrzeit, ort="", link="", quelle=quelle)
    monkeypatch.setattr(hw, "lade_bestehende", lambda d: [t])
    monkeypatch.setattr(hw, "lade_json", lambda: [])
    return t


def _eintrag(name="Feier zur Wintersonnenwende", uhrzeit="17:00"):
    return {"name": name, "datum": "2026-12-20", "uhrzeit": uhrzeit, "ort": "", "link": "", "beschreibung": "",
            "kategorie": "Sonstiges"}


def test_gleiches_wort_gleiche_uhrzeit_ist_dublette(monkeypatch):
    t = _bestehend(monkeypatch, "Abend zur Wintersonnenwende", "17:00 Uhr")
    assert hw.ist_dublette_im_kalender(_eintrag()) is t


def test_andere_schreibweise_der_uhrzeit_zaehlt_als_gleich(monkeypatch):
    t = _bestehend(monkeypatch, "Abend zur Wintersonnenwende", "17.00 Uhr")
    assert hw.ist_dublette_im_kalender(_eintrag()) is t


def test_andere_uhrzeit_bleibt_eigener_termin_mit_warnung(monkeypatch):
    _bestehend(monkeypatch, "Abend zur Wintersonnenwende", "19:00 Uhr")
    e = _eintrag()
    assert hw.ist_dublette_im_kalender(e) is None
    assert e["_aehnlich"] == "Abend zur Wintersonnenwende, 19:00 Uhr"


def test_ohne_uhrzeit_bleibt_eigener_termin(monkeypatch):
    _bestehend(monkeypatch, "Abend zur Wintersonnenwende", "siehe Website")
    assert hw.ist_dublette_im_kalender(_eintrag()) is None
    _bestehend(monkeypatch, "Abend zur Wintersonnenwende", "17:00 Uhr")
    assert hw.ist_dublette_im_kalender(_eintrag(uhrzeit="")) is None


def test_stoppwort_macht_keine_dublette(monkeypatch):
    _bestehend(monkeypatch, "Live-Musik mit Verena", "17:00 Uhr")
    assert hw.ist_dublette_im_kalender(_eintrag("Afrika und ihre Musik")) is None


def test_generator_laesst_redaktionstermine_unveraendert():
    """Nur der Import wird strenger: Was schon im Kalender steht, verschwindet nicht beim Bauen."""
    termine = [Termin(name=n, datum=TAG, uhrzeit="17:00 Uhr", ort="", link="", quelle="manuell")
               for n in ("Abend zur Wintersonnenwende", "Feier zur Wintersonnenwende")]
    assert len(app.entferne_duplikate(termine)) == 2


def test_uhrzeit_gleich_nur_bei_zwei_konkreten_angaben():
    assert app._uhrzeit_gleich("19.00 Uhr", "19:00 Uhr")
    assert app._uhrzeit_gleich("19 Uhr", "19:00")
    assert not app._uhrzeit_gleich("19:00 Uhr", "18:00 Uhr")
    assert not app._uhrzeit_gleich("siehe Website", "19:00 Uhr")
    assert not app._uhrzeit_gleich("", "")


def test_prompt_verlangt_taegliche_veranstaltungen_je_tag():
    assert "je Tag ein Termin" in hw.SYSTEM
    assert "Ausstellungen" in hw.SYSTEM and "`bis`" in hw.SYSTEM
