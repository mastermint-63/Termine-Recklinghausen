"""hole_ratssitzungen: die gremien.info-API liefert Räume auch als null.

Anlass: Die Sitzung des Schulausschusses am 11.11.2026 kam mit "room": null. Der Scraper
stürzte ab, der Lauf brach ohne Push ab, die Live-Seite stand vom 31.10. bis 02.11.2026 still.
"""
from unittest.mock import MagicMock, patch

import scraper


def _sitzung(**felder):
    basis = {
        "datum": "2026-11-11",
        "titel": "Sitzung des Ausschusses für Schule und Bildung",
        "beginn": "16:00:00",
        "full_url": "https://stadt-recklinghausen.gremien.info/meeting?id=2026-ASB-55",
    }
    return {**basis, **felder}


def _hole(*sitzungen):
    antwort = MagicMock()
    antwort.json.return_value = {"meetings": list(sitzungen)}
    with patch.object(scraper.requests, "get", return_value=antwort):
        return scraper.hole_ratssitzungen(2026, 11)


def test_raum_null_liefert_termin_ohne_ort():
    termine = _hole(_sitzung(room=None))
    assert len(termine) == 1
    assert termine[0].ort == ""
    assert termine[0].uhrzeit == "16:00 Uhr"


def test_adresse_null_liefert_nur_raumnamen():
    termine = _hole(_sitzung(room={"name": "Ratssaal", "address": None}))
    assert termine[0].ort == "Ratssaal"


def test_raum_mit_adresse_bleibt_wie_bisher():
    termine = _hole(_sitzung(room={"name": "Ratssaal", "address": {"street": "Rathausplatz 3"}}))
    assert termine[0].ort == "Ratssaal, Rathausplatz 3"
