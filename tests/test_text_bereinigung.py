"""HTML-Reste in gescrapten Texten (Rückmeldung Redaktion 13.10.2026).

NLGR, Backyard und Josef Eich (The Events Calendar) liefern doppelt kodiertes
HTML im JSON-LD: Auf der Seite stand „<p>Stimmen aus dem Exil …“ und
„Stimmen aus dem&nbsp;EXIL“.
"""
from datetime import datetime

from scraper import Termin, _html_zu_text, bereinige_text


def _termin(**kw):
    basis = dict(name='Test', datum=datetime(2026, 10, 15, 19, 30), uhrzeit='19:30 Uhr',
                 ort='Recklinghausen', link='https://example.test/')
    basis.update(kw)
    return Termin(**basis)


def test_doppelt_kodierter_absatz_verschwindet():
    assert _html_zu_text('&lt;p&gt;Stimmen aus dem Exil&lt;/p&gt;') == 'Stimmen aus dem Exil'


def test_doppelt_kodiertes_ampersand():
    assert bereinige_text('Rock &amp;amp; Roll') == 'Rock & Roll'


def test_nbsp_im_titel_wird_leerzeichen():
    t = _termin(name='Stimmen aus dem&nbsp;EXIL')
    assert t.name == 'Stimmen aus dem EXIL'


def test_geschuetztes_leerzeichen_im_titel():
    t = _termin(name='Mit\xa0Bowie\xa0zu\xa0Mond')
    assert t.name == 'Mit Bowie zu Mond'


def test_tags_in_beschreibung_werden_entfernt():
    t = _termin(beschreibung='<p>Erster Absatz.</p><p>Zweiter Absatz.</p>')
    assert '<' not in t.beschreibung
    assert 'Erster Absatz.' in t.beschreibung and 'Zweiter Absatz.' in t.beschreibung
    assert 'Absatz.Zweiter' not in t.beschreibung


def test_zeilenumbruch_bleibt_in_beschreibung():
    assert bereinige_text('Zeile 1<br>Zeile 2') == 'Zeile 1\nZeile 2'


def test_kleiner_zeichen_ohne_tag_bleibt():
    assert bereinige_text('Kinder <3 Musik') == 'Kinder <3 Musik'


def test_normales_ampersand_bleibt():
    assert bereinige_text('Kunst & Kultur') == 'Kunst & Kultur'


def test_ort_wird_bereinigt():
    t = _termin(ort='Willy-Brandt-Haus,&nbsp;Herzogswall')
    assert t.ort == 'Willy-Brandt-Haus, Herzogswall'


def test_leere_felder_bleiben_leer():
    t = _termin(beschreibung='', ort='')
    assert t.beschreibung == '' and t.ort == ''


def test_uhrzeit_siehe_website_ohne_link():
    t = _termin(uhrzeit='siehe Website', link='')
    assert t.uhrzeit_anzeige() == 'Uhrzeit offen'
    # intern bleibt der generische Wert, die Dublettenprüfung kennt nur ihn
    assert t.uhrzeit == 'siehe Website'


def test_uhrzeit_siehe_website_mit_link_bleibt():
    t = _termin(uhrzeit='siehe Website')
    assert t.uhrzeit_anzeige() == 'siehe Website'


def test_normale_uhrzeit_bleibt():
    assert _termin().uhrzeit_anzeige() == '19:30 Uhr'
