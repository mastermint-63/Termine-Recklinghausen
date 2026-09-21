"""Tests für hole_genial_re() gegen eine gesicherte AJAX-Antwort (Oktober 2026, Stand 21.09.2026)."""
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

import scraper

FIXTURE = Path(__file__).parent / "fixtures" / "genial_re_ajax_2026_10.json"


@pytest.fixture
def ajax(monkeypatch):
    """Seite liefert eine Nonce, admin-ajax liefert die gesicherte Antwort. Gibt die POST-Daten zurück."""
    aufrufe = []
    monkeypatch.setattr(scraper, "_request_mit_retry",
                        lambda *a, **k: SimpleNamespace(text='x "_nonce":"abc123def" y'))

    def post(url, data=None, **k):
        aufrufe.append(data)
        return SimpleNamespace(raise_for_status=lambda: None,
                               json=lambda: json.loads(FIXTURE.read_text(encoding="utf-8")))
    monkeypatch.setattr(scraper.requests, "post", post)
    return aufrufe


def _okt():
    return scraper.hole_genial_re(2026, 10)


def test_ajax_wird_mit_nonce_und_monatsgrenzen_aufgerufen(ajax):
    _okt()
    assert ajax[0]["action"] == "ep_get_calendar_event" and ajax[0]["security"] == "abc123def"
    assert ajax[0]["start"] == "2026-10-01T00:00:00" and ajax[0]["end"] == "2026-11-01T00:00:00"


def test_sprachcafe_wird_nicht_als_intern_ausgefiltert(ajax):
    # Regression: der Ausschluss "intern" darf nicht auf "Internationales" anspringen
    tage = sorted(t.datum.day for t in _okt() if t.name == "Internationales Sprachcafé")
    assert tage == [2, 9, 16, 23, 30]


def test_nur_oeffentliche_typen(ajax):
    namen = {t.name for t in _okt()}
    assert "Interne Veranstaltung" not in namen           # Typ 25
    assert "Vermietung gesamtes GENIAL" not in namen      # ohne Typ
    assert "Monatstreffen" not in namen                   # Oktober-Eintrag ohne Typ ('0')
    assert "Brettspiel-Abend" not in namen and "Kreistänze" not in namen  # Typ 10 Gruppen
    assert {"Internationales Sprachcafé", "Stricken am Sonntag", "Auf ein Gläschen", "Kreativmarkt"} <= namen


def test_mehrtaegiger_termin_erscheint_je_tag_ganztaegig(ajax):
    km = sorted((t.datum.day, t.uhrzeit) for t in _okt() if t.name == "Kreativmarkt")
    assert km == [(24, "ganztägig"), (25, "ganztägig")]


def test_uhrzeit_und_ort(ajax):
    stricken = next(t for t in _okt() if t.name == "Stricken am Sonntag")
    assert stricken.uhrzeit == "15:00–17:00 Uhr" and stricken.datum.hour == 15
    assert "Limperstraße 11" in stricken.ort and "Recklinghausen" in stricken.ort
    garten = next(t for t in _okt() if t.name == "Auf ein Gläschen")
    assert garten.ort == "Garten des Genial, Limperstraße 11, Recklinghausen"  # Adresse ergänzt
    viertel = next(t for t in _okt() if t.name.startswith("Unser Viertel"))
    assert viertel.ort == "Recklinghausen"                                       # kein Ort angegeben


def test_pflichtfelder_und_quelle(ajax):
    for t in _okt():
        assert t.quelle == "genial-re" and t.link.startswith("https://genial.re/") and t.beschreibung


def test_anderer_monat_zieht_mehrtaegige_termine_nicht_doppelt(ajax):
    # Die Fixture enthält Oktober-Termine; für November darf davon nichts erscheinen
    assert scraper.hole_genial_re(2026, 11) == []


def test_fehlende_nonce_liefert_leere_liste(monkeypatch):
    monkeypatch.setattr(scraper, "_request_mit_retry", lambda *a, **k: SimpleNamespace(text="keine nonce"))
    assert scraper.hole_genial_re(2026, 10) == []


def test_ajax_fehler_liefert_leere_liste(monkeypatch):
    monkeypatch.setattr(scraper, "_request_mit_retry", lambda *a, **k: SimpleNamespace(text='"_nonce":"x1"'))
    monkeypatch.setattr(time, "sleep", lambda s: None)

    def kaputt(*a, **k):
        raise requests.RequestException("boom")
    monkeypatch.setattr(scraper.requests, "post", kaputt)
    assert scraper.hole_genial_re(2026, 10) == []


def test_erfolglose_antwort_liefert_leere_liste(monkeypatch):
    monkeypatch.setattr(scraper, "_request_mit_retry", lambda *a, **k: SimpleNamespace(text='"_nonce":"x1"'))
    monkeypatch.setattr(scraper.requests, "post", lambda *a, **k: SimpleNamespace(
        raise_for_status=lambda: None, json=lambda: {"success": False, "data": "Bitte aktualisiere die Seite"}))
    assert scraper.hole_genial_re(2026, 10) == []
