import json
import os

from scraper import _eventim_zu_terminen

FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'eventim_zen_2026-10-10.json')


def _events():
    with open(FIXTURE, encoding='utf-8') as f:
        return json.load(f)


def test_nur_recklinghausen():
    # Umkreissuche liefert auch Oer-Erkenschwick und Herten
    termine = [t for m in (10, 11, 12) for t in _eventim_zu_terminen(_events(), 2026, m)]
    termine += [t for m in (1, 2, 3) for t in _eventim_zu_terminen(_events(), 2027, m)]
    assert len(termine) == 5
    assert all(t.quelle == 'eventim' for t in termine)


def test_felder_und_ortszeit():
    termine = _eventim_zu_terminen(_events(), 2026, 11)
    orloff = next(t for t in termine if 'Orloff' in t.name)
    assert orloff.datum.strftime('%d.%m.%Y %H:%M') == '26.11.2026 18:00'
    assert orloff.uhrzeit == '18:00 Uhr'
    assert orloff.ort == 'Kath. Kirche St. Antonius'
    assert orloff.link.startswith('https://www.eventim.de/event/')
    assert orloff.kategorie == 'Konzert'


def test_versalien_ort_normalisiert():
    termine = _eventim_zu_terminen(_events(), 2027, 1)
    udo = next(t for t in termine if 'Udo' in t.name)
    assert udo.ort == 'Ruhrfestspielhaus'


def test_abgesagt_und_kaputt_ueberspringen():
    events = [
        {'eventName': 'Abgesagt', 'startDate': '2026-11-01T20:00:00+01:00', 'status': 'Cancelled',
         'venue': {'name': 'Ratskeller Recklinghausen', 'city': 'Recklinghausen'}},
        {'eventName': None, 'startDate': '2026-11-01T20:00:00+01:00', 'venue': {'city': 'Recklinghausen'}},
        {'eventName': 'Ohne Datum', 'startDate': None, 'venue': {'city': 'Recklinghausen'}},
        {'eventName': 'Ohne Ort', 'startDate': '2026-11-01T20:00:00+01:00', 'venue': None},
    ]
    assert _eventim_zu_terminen(events, 2026, 11) == []
