import os

from scraper import _re_leuchtet_parse

FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 're_leuchtet_programm_2026-10-10.html')


def _html():
    with open(FIXTURE, encoding='utf-8') as f:
        return f.read()


def test_ein_termin_pro_vorkommen():
    termine = _re_leuchtet_parse(_html(), 2026, 10) + _re_leuchtet_parse(_html(), 2026, 11)
    namen = sorted(t.name for t in termine)
    assert namen.count('Vivian Swoboda') == 2  # 23.10. und 02.11.
    assert any(n.startswith('Eröffnung von Recklinghausen leuchtet') for n in namen)


def test_felder():
    termine = _re_leuchtet_parse(_html(), 2026, 10)
    er = next(t for t in termine if t.name.startswith('Eröffnung'))
    assert er.datum.strftime('%d.%m.%Y %H:%M') == '23.10.2026 19:30'
    assert er.uhrzeit == '19:30 Uhr'
    assert er.ort == 'Rathaus Recklinghausen / Rathausplatz'
    assert er.link.startswith('https://re-leuchtet.de/programm?rel_event=')
    assert er.beschreibung
    assert er.quelle == 're-leuchtet'


def test_anderer_monat_leer():
    assert _re_leuchtet_parse(_html(), 2026, 12) == []
