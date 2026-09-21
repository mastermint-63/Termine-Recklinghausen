"""Tests für hole_selbsthilfe_kontaktstelle() gegen einen gesicherten Seitenausschnitt (Stand 21.09.2026)."""
from pathlib import Path
from types import SimpleNamespace

import pytest

import scraper

FIXTURE = Path(__file__).parent / "fixtures" / "selbsthilfe_kontaktstelle.html"


@pytest.fixture(autouse=True)
def seite(monkeypatch):
    html = FIXTURE.read_text(encoding="utf-8")
    monkeypatch.setattr(scraper, "_request_mit_retry", lambda *a, **k: SimpleNamespace(text=html))


def _alle():
    return [t for (j, m) in [(2026, 9), (2026, 10), (2026, 11), (2026, 12), (2027, 1)]
            for t in scraper.hole_selbsthilfe_kontaktstelle(j, m)]


def test_erwartete_termine_mit_datum_und_uhrzeit():
    ergebnis = {(t.datum.strftime("%Y-%m-%d"), t.uhrzeit) for t in _alle()}
    assert ergebnis == {
        ("2026-09-23", "16:00–17:30 Uhr"),   # Vortrag Gesundheits-APPs
        ("2026-10-02", "18:00 Uhr"),          # Lesung Paulushaus
        ("2026-10-31", "14:00–18:00 Uhr"),    # Kreativ-Workshop 1
        ("2026-11-28", "14:00–18:00 Uhr"),    # Kreativ-Workshop 2
        ("2026-12-01", "15:00–17:00 Uhr"),    # Vernissage
    }


def test_ort_ausserhalb_recklinghausen_wird_nicht_uebernommen():
    # Tanz-Vortrag und -Workshop am 16.10. finden in Oer-Erkenschwick statt
    assert not [t for t in _alle() if t.datum.strftime("%Y-%m-%d") == "2026-10-16"]


def test_interne_supervision_und_cafe_ohne_jahr_fehlen():
    namen = " ".join(t.name for t in _alle()).lower()
    assert "supervision" not in namen
    assert "café" not in namen
    assert not [t for t in _alle() if t.datum.strftime("%Y-%m-%d") == "2026-10-14"]


def test_vernissage_hat_eigenen_namen_und_ortshinweis():
    v = next(t for t in _alle() if t.datum.strftime("%Y-%m-%d") == "2026-12-01")
    assert v.name.endswith("Vernissage") and "Ort laut Ankündigung" in v.ort


def test_pflichtfelder_und_quelle():
    for t in _alle():
        assert t.name and t.link.startswith("https://www.paritaetischer-recklinghausen.de/")
        assert t.quelle == "selbsthilfe-kontaktstelle" and "Recklinghausen" in t.ort
        assert t.datum.hour in (14, 15, 16, 18)


def test_seitenfehler_liefert_leere_liste(monkeypatch):
    import requests

    def kaputt(*a, **k):
        raise requests.RequestException("boom")
    monkeypatch.setattr(scraper, "_request_mit_retry", kaputt)
    assert scraper.hole_selbsthilfe_kontaktstelle(2026, 10) == []
