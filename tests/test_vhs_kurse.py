"""VHS: Einzelveranstaltung oder Kurs (Entscheidung FS, 13.10.2026).

Die VHS ist kein Kino: Zwei Drittel der Einträge sind Vorträge, Lesungen,
Gedenkveranstaltungen. Kurse (ab 2 Terminen, z.B. „Latein, 7 Termine“) bleiben
sichtbar, sind aber als Kurs gekennzeichnet. Struktur wie auf den echten
KuferWeb-Detailseiten (13.10.2026).
"""
from scraper import _parse_vhs_detail


def _seite(dauer: str, text: str = 'Beschreibung des Angebots.') -> str:
    return f'''<div class="row">
    <div class="col-md-3">
      <div class="row"><div class="col-md-4"><b>Kursnr.</b></div><div class="col-md-8">27A-4511</div></div>
      <div class="row"><div class="col-md-4"><b>Beginn</b></div>
        <div class="col-md-8">Mi., 03.02.2027, <br> 16:00 - 17:30 Uhr</div></div>
      <div class="row"><div class="col-md-4"><b>Dauer</b></div><div class="col-md-8">{dauer}</div></div>
      <div class="row"><div class="col-md-4"><b>Gebühr</b></div><div class="col-md-8">77,00 &euro; </div></div>
    </div>
    <div class="col-md-9"> <br />{text}</div>
  </div>'''


def test_kurs_mit_mehreren_terminen():
    d = _parse_vhs_detail(_seite('7 Termine'))
    assert d['termine'] == 7 and d['dauer'] == '7 Termine'


def test_leere_dauer_ist_einzeltermin():
    assert _parse_vhs_detail(_seite(''))['termine'] == 1


def test_ein_tag_ist_einzeltermin():
    assert _parse_vhs_detail(_seite('1 Tag'))['termine'] == 1


def test_mehrere_tage_sind_kurs():
    assert _parse_vhs_detail(_seite('5 Tage'))['termine'] == 5


def test_beschreibung_aus_detailseite():
    d = _parse_vhs_detail(_seite('', 'Die LINGUA LATINA, das Lateinische, ist die Grundsprache.'))
    assert d['beschreibung'] == 'Die LINGUA LATINA, das Lateinische, ist die Grundsprache.'


def test_seite_ohne_dauer():
    assert _parse_vhs_detail('<html><body>Wartung</body></html>') == {'termine': None, 'dauer': '', 'beschreibung': ''}


def _termin():
    from datetime import datetime
    from scraper import Termin
    return Termin(name='Latein mit Vorkenntnissen 1', datum=datetime(2027, 2, 3, 16), uhrzeit='16:00–17:30 Uhr',
                  ort='Willy-Brandt-Haus', link='https://example.test/kurs', quelle='vhs', kategorie='Bildung')


def test_kurs_wird_gekennzeichnet():
    from scraper import _vhs_ergaenze
    t = _termin()
    _vhs_ergaenze(t, {'termine': 7, 'dauer': '7 Termine', 'beschreibung': 'Die Sprache der Römer.'})
    assert t.kategorie == 'Kurs'
    assert t.beschreibung == 'Kurs mit 7 Terminen, Anmeldung über die VHS. Die Sprache der Römer.'


def test_kurs_ueber_tage():
    from scraper import _vhs_ergaenze
    t = _termin()
    _vhs_ergaenze(t, {'termine': 5, 'dauer': '5 Tage', 'beschreibung': ''})
    assert t.beschreibung == 'Kurs über 5 Tage, Anmeldung über die VHS.'


def test_einzeltermin_bleibt_bildung():
    from scraper import _vhs_ergaenze
    t = _termin()
    _vhs_ergaenze(t, {'termine': 1, 'dauer': '', 'beschreibung': 'Vortrag über Rom.'})
    assert t.kategorie == 'Bildung' and t.beschreibung == 'Vortrag über Rom.'


def test_unbekannte_dauer_aendert_nichts_an_der_kategorie():
    from scraper import _vhs_ergaenze
    t = _termin()
    _vhs_ergaenze(t, {'termine': None, 'dauer': '', 'beschreibung': ''})
    assert t.kategorie == 'Bildung' and t.beschreibung == ''
