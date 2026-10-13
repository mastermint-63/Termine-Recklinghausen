"""Vesterleben-Detailseiten: Ort und voller Titel (Rückmeldung Erich, 13.10.2026).

Die Übersichtsliste kennt nur die Stadt und kürzt lange Titel
(„Zwangsarbeiter und Zwangsarbeiterinnen in“). Fixtures: gekürzte echte
Detailseiten vom 13.10.2026.
"""
from pathlib import Path

from scraper import _parse_vesterleben_detail

FIX = Path(__file__).parent / 'fixtures'


def _lade(name):
    return (FIX / name).read_text(encoding='utf-8')


def test_ort_mit_adresse():
    d = _parse_vesterleben_detail(_lade('vesterleben_detail_karas.html'))
    assert d['ort'] == 'Ratskeller Recklinghausen, Rathausplatz 3'


def test_voller_titel_aus_beschreibung():
    d = _parse_vesterleben_detail(_lade('vesterleben_detail_zwangsarbeiter.html'))
    assert d['titel'] == 'Zwangsarbeiter und Zwangsarbeiterinnen in Recklinghausen 1941–45'
    assert d['ort'] == 'Willy-Brandt-Haus, Herzogswall 17'


def test_platzhaltertext_nicht_als_beschreibung():
    d = _parse_vesterleben_detail(_lade('vesterleben_detail_karas.html'))
    assert 'angegebene Webseite' not in d['beschreibung']
    assert d['titel'] == ''


def _seite(wo_html, beschreibung='<p>Text</p>'):
    return f'''<main id="article"><ul class="termininfos">
        <li><span class="info-rubrik">Wo?</span>{wo_html}</li></ul>
        <article><h2>Beschreibung</h2>{beschreibung}</article></main>'''


def test_strasse_schon_im_ortsnamen():
    d = _parse_vesterleben_detail(_seite('Stadtbibliothek, Am Neumarkt 19<br/>Am Neumarkt 19 <br/>45663 | Recklinghausen'))
    assert d['ort'] == 'Stadtbibliothek, Am Neumarkt 19'


def test_recklinghaeuser_geschaeftsadresse_korrigiert():
    d = _parse_vesterleben_detail(_seite('Der Recklinghäuser<br/>Königswall 14 <br/>45657 | Recklinghausen'))
    assert d['ort'] == 'Der Recklinghäuser, Herrenstraße 12'


def test_echte_beschreibung_bleibt():
    d = _parse_vesterleben_detail(_seite('Altstadtschmiede<br/>Kellerstraße 10<br/>45657 | Recklinghausen',
                                         '<p>Blues aus Chicago mit Band.</p>'))
    assert d['beschreibung'] == 'Blues aus Chicago mit Band.'


def test_kaputte_seite_liefert_leere_werte():
    d = _parse_vesterleben_detail('<html><body>Fehler</body></html>')
    assert d == {'ort': '', 'titel': '', 'beschreibung': ''}


def test_buttons_nicht_in_beschreibung():
    for datei in ('vesterleben_detail_karas.html', 'vesterleben_detail_zwangsarbeiter.html'):
        d = _parse_vesterleben_detail(_lade(datei))
        assert 'speichern' not in d['beschreibung'] and 'teilen' not in d['beschreibung']


def test_rest_des_gekuerzten_titels_entfaellt():
    d = _parse_vesterleben_detail(_lade('vesterleben_detail_zwangsarbeiter.html'))
    assert d['beschreibung'] == ''
