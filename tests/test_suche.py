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


# --- Paket C (14.10.2026): Art statt Rohkategorie, Suchwort trifft auch die Art ---

import shutil
import subprocess

import pytest

import arten


def test_suchdaten_tragen_die_art():
    konzert = _t('Jazz in der Kunsthalle', art='Konzert')
    sonst = _t('Irgendwas', art='Sonstiges')
    d = _daten([konzert, sonst])
    nach_name = {e['n']: e for e in d['termine']}
    assert nach_name['Jazz in der Kunsthalle']['t'] == 'Konzert'
    assert 't' not in nach_name['Irgendwas']  # Sonstiges spart Platz, gilt in der Suche als Sonstiges


def test_suchwoerter_mit_synonymen():
    w = arten.such_woerter()
    assert w['konzert'] == 'Konzert'
    for wort in ('musik', 'livemusik', 'live-musik', 'gig'):
        assert w[wort] == 'Konzert', wort
    for wort in ('kabarett', 'comedy', 'theater'):
        assert w[wort] == 'Theater/Kabarett', wort
    for wort in ('disco', 'tanzen', 'party'):
        assert w[wort] == 'Party', wort
    assert w['lesung'] == 'Lesung/Vortrag' and w['vortrag'] == 'Lesung/Vortrag'
    assert w['fuhrung'] == 'Führung'  # normalisiert wie im Browser (ü -> u)
    assert 'kino' not in w and 'sonstiges' not in w  # Suche ist ohne Kino


def test_suchdaten_enthalten_suchwoerter():
    d = _daten([_t('X', art='Konzert')])
    assert d['artwoerter']['gig'] == 'Konzert'


def test_suchseite_art_filter_aus_fester_liste():
    html = app.generiere_suchseite(tracking=False)
    start = html.index('id="suche-art"')
    auswahl = html[start:html.index('</select>', start)]
    werte = [a for a in arten.ARTEN if a != 'Kino']
    positionen = [auswahl.index(f'<option value="{app._html.escape(a)}">') for a in werte]
    assert positionen == sorted(positionen)  # Reihenfolge wie die Liste
    assert 'value="Kino"' not in auswahl
    assert 'Literatur' not in auswahl  # keine Rohkategorien mehr


def test_suchtreffer_nur_als_text():
    html = app.generiere_suchseite(tracking=False)
    for verboten in ('innerHTML', 'outerHTML', 'insertAdjacentHTML', 'document.write'):
        assert verboten not in html
    assert 'e.textContent = text' in html


def _node(js):
    return subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout


@pytest.mark.skipif(shutil.which('node') is None, reason='node fehlt')
@pytest.mark.parametrize('anfrage, art, text, erwartet', [
    ('Konzert', 'Konzert', 'rock pop akustik session', True),
    ('konzerte', 'Konzert', 'jazz', True),
    ('Gig', 'Konzert', 'band', True),
    ('Live-Musik', 'Konzert', 'band', True),
    ('Konzert', 'Party', 'disco im moondock', False),
    ('Konzert', 'Lesung/Vortrag', 'lesung mit konzert', True),  # Volltext bleibt
    ('Disco', 'Party', 'tanznacht', True),
    ('Comedy', 'Theater/Kabarett', 'abend', True),
    ('Führungen', 'Führung', 'altstadt', True),
    ('Konzert Altstadt', 'Konzert', 'altstadtschmiede', True),
    ('Konzert Altstadt', 'Konzert', 'kunsthalle', False),
    ('kunsthalle', 'Ausstellung/Kunst', 'galerie', False),  # Präfix nur für Beugung
])
def test_suchlogik_im_browser_code(anfrage, art, text, erwartet):
    js = (app._SUCHE_LOGIK_JS
          + '\nvar w = ' + json.dumps(arten.such_woerter()) + ';'
          + '\nvar t = {s: hwNorm(' + json.dumps(text) + '), t: ' + json.dumps(art) + '};'
          + '\nprocess.stdout.write(String(hwTrifft(t, hwWoerter(' + json.dumps(anfrage) + '), w)));')
    assert _node(js) == str(erwartet).lower()


@pytest.mark.skipif(shutil.which('node') is None, reason='node fehlt')
@pytest.mark.parametrize('param, erwartet', [
    ('Konzert', 'Konzert'), ('Theater/Kabarett', 'Theater/Kabarett'),
    ('Musik', 'Konzert'),      # alte Rohkategorie mit Synonym
    ('Literatur', ''),         # alte Rohkategorie ohne Gegenstück: kein Fehler, kein Filter
    ('<script>', ''), ('Kino', ''), ('', ''),
])
def test_alter_art_parameter(param, erwartet):
    werte = [a for a in arten.ARTEN if a != 'Kino']
    js = (app._SUCHE_LOGIK_JS
          + '\nprocess.stdout.write(hwArtAusParam(' + json.dumps(param) + ', ' + json.dumps(werte) + ', '
          + json.dumps(arten.such_woerter()) + '));')
    assert _node(js) == erwartet
