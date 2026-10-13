"""Suchseite über alle kommenden Termine (Wunsch Ralf, 13.10.2026).

Ralf: Die Browsersuche findet nur auf der aktuellen Seite, „Semsrott“ steht
erst im Folgemonat. Gesucht wird nach Ort, Art, Veranstalter, Name des Gastes.
"""
import json
from datetime import date, datetime

import app
from scraper import Termin

HEUTE = date(2026, 10, 13)


def _t(name, tag=date(2026, 11, 20), quelle='nlgr', **kw):
    basis = dict(name=name, datum=datetime(tag.year, tag.month, tag.day, 19, 30), uhrzeit='19:30 Uhr',
                 ort='Willy-Brandt-Haus', link='https://example.test/x', quelle=quelle, kategorie='Literatur')
    basis.update(kw)
    return Termin(**basis)


def _daten(termine):
    nach_tag = {}
    for t in termine:
        nach_tag.setdefault(t.datum.date(), []).append(t)
    js = app.generiere_suchdaten(nach_tag, HEUTE)
    assert js.startswith('window.HW_SUCHE = ') and js.rstrip().endswith(';')
    return json.loads(js.strip()[len('window.HW_SUCHE = '):-1])


def test_suchdaten_enthalten_folgemonat():
    d = _daten([_t('Lesung mit Arne Semsrott', beschreibung='Über Informationsfreiheit.')])
    e = d['termine'][0]
    assert e['n'] == 'Lesung mit Arne Semsrott'
    assert e['d'] == '2026-11-20' and e['z'] == '19:30 Uhr'
    assert e['o'] == 'Willy-Brandt-Haus' and e['q'] == app.QUELLEN['nlgr'] and e['k'] == 'Literatur'
    assert e['b'] == 'Über Informationsfreiheit.'
    assert d['stand'] == '13.10.2026'


def test_suchdaten_ohne_kino_und_ohne_vergangenes():
    d = _daten([_t('Film', quelle='cineworld', kategorie='Kino'),
                _t('Gestern', tag=date(2026, 10, 12)),
                _t('Heute', tag=HEUTE)])
    assert [e['n'] for e in d['termine']] == ['Heute']


def test_suchdaten_absage_und_unsicherer_link():
    d = _daten([_t('Abgesagt', abgesagt=True), _t('Kaputt', link='javascript:alert(1)')])
    nach_name = {e['n']: e for e in d['termine']}
    assert nach_name['Abgesagt']['a'] == 1
    assert nach_name['Kaputt']['l'] == ''


def test_suchdaten_kein_script_ausbruch():
    t = _t('X')
    t.name = 'Böse</script><script>alert(1)</script>'
    js = app.generiere_suchdaten({t.datum.date(): [t]}, HEUTE)
    assert '</script' not in js


def test_suchseite_formular_und_schutz():
    html = app.generiere_suchseite(tracking=False)
    assert 'role="search"' in html and 'name="q"' in html
    assert 'src="suche-daten.js"' in html
    assert 'noindex' in html
    assert 'innerHTML' not in html  # Trefferdaten nur als Text in die Seite
    assert '<noscript>' in html


def test_schnellnav_verlinkt_suche():
    assert '<a href="../suche.html">Suche</a>' in app._schnellnav('../')
