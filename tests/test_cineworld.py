"""Tests für hole_cineworld(): ein Eintrag pro Film UND Tag mit allen Uhrzeiten des Tages."""
from types import SimpleNamespace

import scraper


def _vorstellung(name, utc_start):
    return {"name": name, "startDatetime": utc_start, "bookingUrlExternal": "https://tickets.example/x"}


def _api(monkeypatch, pro_tag):
    """pro_tag: {'2026-10-03': [Vorstellungen]}; jeder andere Tag ist leer."""
    def get(url, params=None, **k):
        items = pro_tag.get(params["date"], [])
        return SimpleNamespace(json=lambda: {"_embedded": {"showings": items}, "_page_count": 1})
    monkeypatch.setattr(scraper, "_request_mit_retry", get)


def test_gleicher_film_an_zwei_tagen_gibt_zwei_eintraege(monkeypatch):
    _api(monkeypatch, {
        "2026-10-03": [_vorstellung("Film A", "2026-10-03T14:00:00Z")],
        "2026-10-05": [_vorstellung("Film A", "2026-10-05T14:00:00Z")],
    })
    ts = scraper.hole_cineworld(2026, 10)
    assert sorted(t.datum.day for t in ts if t.name == "Film A") == [3, 5]


def test_mehrere_zeiten_am_selben_tag_stehen_in_einem_eintrag(monkeypatch):
    _api(monkeypatch, {"2026-10-03": [
        _vorstellung("Film A", "2026-10-03T09:00:00Z"),   # 11:00 Berlin (MESZ)
        _vorstellung("Film A", "2026-10-03T15:15:00Z"),   # 17:15
        _vorstellung("Film A", "2026-10-03T17:45:00Z"),   # 19:45
        _vorstellung("Film A", "2026-10-03T11:00:00Z"),   # 13:00
        _vorstellung("Film A", "2026-10-03T13:30:00Z"),   # 15:30 -> 5 Zeiten, kein Sammeltext mehr
    ]})
    ts = scraper.hole_cineworld(2026, 10)
    assert len(ts) == 1
    assert ts[0].uhrzeit == "11:00 / 13:00 / 15:30 / 17:15 / 19:45 Uhr"
    assert "täglich" not in ts[0].uhrzeit


def test_verschiedene_filme_am_selben_tag_getrennt(monkeypatch):
    _api(monkeypatch, {"2026-10-03": [
        _vorstellung("Film A", "2026-10-03T14:00:00Z"), _vorstellung("Film B", "2026-10-03T14:00:00Z")]})
    assert sorted(t.name for t in scraper.hole_cineworld(2026, 10)) == ["Film A", "Film B"]


def test_felder(monkeypatch):
    _api(monkeypatch, {"2026-10-03": [_vorstellung("Film A", "2026-10-03T14:00:00Z")]})
    t = scraper.hole_cineworld(2026, 10)[0]
    assert t.quelle == "cineworld" and t.kategorie == "Kino" and t.ort == "Cineworld, Kemnastr. 3"
    assert t.datum.hour == 0 and t.link == "https://tickets.example/x"
