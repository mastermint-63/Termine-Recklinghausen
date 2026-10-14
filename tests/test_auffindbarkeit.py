"""Tests für Tagesseiten, Startseite, JSON-LD, iCal und llms.txt (Auffindbarkeit, Plan 13.10.2026)."""
import json
import re
from datetime import date, datetime, timedelta

import pytest

import app
from scraper import Termin

TAG = date(2026, 10, 13)
ERSTER, LETZTER = date(2026, 10, 1), date(2026, 10, 31)


def _t(name, quelle="nlgr", uhrzeit="19:30 Uhr", tag=TAG, **kw):
    return Termin(name=name, datum=datetime(tag.year, tag.month, tag.day, 19, 30), uhrzeit=uhrzeit,
                  ort=kw.pop("ort", "Altstadtschmiede, Kellerstraße 10, 45657 Recklinghausen"),
                  link=kw.pop("link", "https://example.test/x"), quelle=quelle, **kw)


def _jsonld(html):
    return [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


# --- Uhrzeiten -------------------------------------------------------------

@pytest.mark.parametrize("uhrzeit, erwartet", [
    ("19:30 Uhr", ("19:30", None)),
    ("19:30–21:00 Uhr", ("19:30", "21:00")),
    ("14.00 - 17.00 Uhr", ("14:00", "17:00")),
    ("von 9:30 bis 12 Uhr", ("09:30", "12:00")),
    ("19 Uhr", ("19:00", None)),
    ("14:00 / 19:30 Uhr", ("14:00", None)),          # Kino: mehrere Vorstellungen
    ("22:00–02:00 Uhr", ("22:00", None)),             # über Mitternacht: kein Ende raten
    ("ganztägig", (None, None)),
    ("siehe Website", (None, None)),
    ("", (None, None)),
])
def test_zeitspanne(uhrzeit, erwartet):
    assert app.zeitspanne(uhrzeit) == erwartet


# --- JSON-LD ------------------------------------------------------------------

def test_event_jsonld_zeitzone_status_adresse():
    e = app.event_jsonld(_t("Konzert", uhrzeit="19:30–21:00 Uhr"))
    assert e["startDate"] == "2026-10-13T19:30:00+02:00"
    assert e["endDate"] == "2026-10-13T21:00:00+02:00"
    assert e["eventStatus"] == "https://schema.org/EventScheduled"
    assert e["location"]["address"]["streetAddress"] == "Kellerstraße 10"
    assert e["location"]["address"]["postalCode"] == "45657"


def test_event_jsonld_winterzeit_und_ganztaegig():
    e = app.event_jsonld(_t("Markt", uhrzeit="10:00 Uhr", tag=date(2026, 11, 7)))
    assert e["startDate"] == "2026-11-07T10:00:00+01:00"
    g = app.event_jsonld(_t("Ausstellung", uhrzeit="ganztägig"))
    assert g["startDate"] == "2026-10-13" and "endDate" not in g


def test_event_jsonld_absage_und_eintritt_frei():
    e = app.event_jsonld(_t("Vortrag", abgesagt=True, beschreibung="Eintritt frei, Anmeldung erbeten"))
    assert e["eventStatus"] == "https://schema.org/EventCancelled"
    assert e["isAccessibleForFree"] is True
    assert "isAccessibleForFree" not in app.event_jsonld(_t("Konzert", beschreibung="Eintritt 10 Euro"))


def test_monatsseite_jsonld_listet_tagesseiten_statt_kinofilme():
    termine = [_t(f"Film {i}", quelle="cineworld") for i in range(60)] + [_t("Lesung", tag=date(2026, 10, 14))]
    html = app.generiere_html(termine, 2026, 10, [(2026, 10)], "termine_re_2026_10.html")
    ld = _jsonld(html)[0]
    urls = [e["url"] for e in ld["mainEntity"]["itemListElement"]]
    assert urls == ["https://termine.holzwurm-recklinghausen.de/tag/2026-10-13.html",
                    "https://termine.holzwurm-recklinghausen.de/tag/2026-10-14.html"]
    assert '<h2 class="datum-header"><a href="tag/2026-10-13.html">' in html


# --- Tagesseiten --------------------------------------------------------------

def test_tagesseite_titel_canonical_und_kino_sammelzeile():
    termine = [_t("Sinfoniekonzert"), _t("Avatar 3", quelle="cineworld", uhrzeit="14:00 / 19:30 Uhr"),
               _t("Dune", quelle="cineworld", uhrzeit="20:00 Uhr")]
    html = app.generiere_tagesseite(TAG, termine, ERSTER, LETZTER)
    assert "<title>Veranstaltungen in Recklinghausen am Dienstag, 13. Oktober 2026 | Holzwurm</title>" in html
    assert '<link rel="canonical" href="https://termine.holzwurm-recklinghausen.de/tag/2026-10-13.html" />' in html
    assert 'data-quelle="cineworld"' not in html                 # keine Einzelfilme
    assert "zeigt an diesem Tag 2 Filme: Avatar 3, Dune." in html
    events = _jsonld(html)[0]["mainEntity"]["itemListElement"]
    assert [e["name"] for e in events] == ["Sinfoniekonzert"]


def test_tagesseite_relative_pfade_und_nachbartage():
    html = app.generiere_tagesseite(TAG, [_t("A")], ERSTER, LETZTER)
    assert 'href="../stil.css"' in html and 'src="../hebbert/1984-01-verkleinert.jpg"' in html
    assert 'href="2026-10-12.html"' in html and 'href="2026-10-14.html"' in html
    assert 'href="../termine_re_2026_10.html#datum-2026-10-13"' in html
    rand = app.generiere_tagesseite(ERSTER, [], ERSTER, LETZTER)
    assert 'class="nav-btn disabled"' in rand
    assert "noch keine Termine bekannt" in rand


def test_tagesseite_ohne_tracking():
    assert "umami" in app.generiere_tagesseite(TAG, [], ERSTER, LETZTER)
    assert "umami" not in app.generiere_tagesseite(TAG, [], ERSTER, LETZTER, tracking=False)


def test_tagesseite_kein_script_ausbruch():
    html = app.generiere_tagesseite(TAG, [_t("Böse</script><script>alert(1)</script>")], ERSTER, LETZTER)
    for ld in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        assert "<" not in ld
    assert "<script>alert(1)" not in html


def test_heute_seite_canonical_und_weiterleitung():
    html = app.generiere_tagesseite(TAG, [_t("A")], ERSTER, LETZTER, art="heute")
    assert '<link rel="canonical" href="https://termine.holzwurm-recklinghausen.de/heute.html" />' in html
    assert "k !== '2026-10-13'" in html and "window.location.replace('tag/' + k + '.html')" in html
    assert 'href="tag/2026-10-14.html"' in html and 'href="stil.css"' in html


@pytest.mark.parametrize("heute, erwartet", [
    (date(2026, 10, 13), [date(2026, 10, 16), date(2026, 10, 17), date(2026, 10, 18)]),  # Dienstag
    (date(2026, 10, 16), [date(2026, 10, 16), date(2026, 10, 17), date(2026, 10, 18)]),  # Freitag
    (date(2026, 10, 18), [date(2026, 10, 18)]),                                          # Sonntag
])
def test_wochenend_tage(heute, erwartet):
    assert app.wochenend_tage(heute) == erwartet


def test_startseite_eigener_inhalt():
    termine = {TAG: [_t("Heute-Termin")], date(2026, 10, 14): [_t("Morgen-Termin", tag=date(2026, 10, 14))]}
    html = app.generiere_startseite(TAG, termine, [(2026, 10)], ERSTER, LETZTER)
    assert '<link rel="canonical" href="https://termine.holzwurm-recklinghausen.de/" />' in html
    assert "<h1>Veranstaltungskalender Recklinghausen</h1>" in html
    assert "Heute-Termin" in html and "Morgen-Termin" in html
    assert 'href="tag/2026-10-15.html"' in html and 'href="termine_re_2026_10.html"' in html


# --- iCal: Einzeltermine ("In meinen Kalender") ---------------------------------

def test_termin_ics_ein_termin_mit_zeitzone_und_gefaltet():
    lang = "Sehr " * 40 + "lange Beschreibung; mit Komma, und Ümläuten"
    ics = app.generiere_termin_ics(_t("Konzert", uhrzeit="19:30–21:00 Uhr", beschreibung=lang))
    assert ics.startswith("BEGIN:VCALENDAR\r\n") and ics.endswith("END:VCALENDAR\r\n")
    assert ics.count("BEGIN:VEVENT") == 1
    assert "DTSTART;TZID=Europe/Berlin:20261013T193000" in ics
    assert "DTEND;TZID=Europe/Berlin:20261013T210000" in ics
    assert "BEGIN:VTIMEZONE" in ics and "URL:https://example.test/x" in ics
    assert "X-WR-CALNAME" not in ics and "REFRESH-INTERVAL" not in ics   # kein Abo
    for zeile in ics.split("\r\n"):
        assert len(zeile.encode("utf-8")) <= 75
    entfaltet = ics.replace("\r\n ", "")
    assert "lange Beschreibung\\; mit Komma\\, und Ümläuten" in entfaltet


def test_termin_ics_ganztaegig_und_stabil():
    ics = app.generiere_termin_ics(_t("Ausstellung", uhrzeit="ganztägig"))
    assert "DTSTART;VALUE=DATE:20261013" in ics and "DTEND;VALUE=DATE:20261014" in ics
    assert ics == app.generiere_termin_ics(_t("Ausstellung", uhrzeit="ganztägig"))  # kein Zeitstempel des Laufs


def test_kalender_link_nicht_bei_kino_und_absage():
    assert 'href="kalender/' in app._termin_html(_t("Konzert"))
    assert 'href="../kalender/' in app._termin_html(_t("Konzert"), "../")
    assert "In meinen Kalender" not in app._termin_html(_t("Film", quelle="cineworld"))
    assert "In meinen Kalender" not in app._termin_html(_t("Vortrag", abgesagt=True))


def test_kalender_link_stoert_hw_import_parser_nicht():
    """hw_import liest Titel, Ort und Uhrzeit aus den Monatsseiten (termin-ort muss rein bleiben)."""
    html = app._termin_html(_t("Konzert", ort="Altstadtschmiede"))
    assert re.search(r'termin-ort">(.*?)</div>', html, re.S).group(1) == "Altstadtschmiede"


# --- Schreiben ----------------------------------------------------------------

def test_schreibe_wenn_geaendert(tmp_path):
    pfad = str(tmp_path / "tag" / "x.html")
    assert app.schreibe_wenn_geaendert(pfad, "a") is True
    assert app.schreibe_wenn_geaendert(pfad, "a") is False
    assert app.schreibe_wenn_geaendert(pfad, "b") is True


def test_generiere_auffindbarkeit_schreibt_alle_dateien(tmp_path):
    termine = {(2026, 10): [_t("Konzert"), _t("Film", quelle="cineworld")]}
    pfade = app.generiere_auffindbarkeit(str(tmp_path), termine, [(2026, 10)], TAG, tracking=False)
    assert len(pfade) == 31 and pfade[12] == "tag/2026-10-13.html"
    for datei in ("stil.css", "index.html", "heute.html", "morgen.html", "wochenende.html",
                  "llms.txt", "tag/2026-10-13.html", f"kalender/{app.termin_uid(_t('Konzert'))}.ics"):
        assert (tmp_path / datei).exists(), datei
    assert not (tmp_path / "termine.ics").exists()
    assert len(list((tmp_path / "kalender").iterdir())) == 1          # Kino ohne Datei
    assert "umami" not in (tmp_path / "index.html").read_text()
    # zweiter Lauf mit gleichen Daten ändert keine Tagesseite
    vorher = (tmp_path / "tag/2026-10-13.html").stat().st_mtime_ns
    app.generiere_auffindbarkeit(str(tmp_path), termine, [(2026, 10)], TAG, tracking=False)
    assert (tmp_path / "tag/2026-10-13.html").stat().st_mtime_ns == vorher
    # verwaiste Kalender-Datei verschwindet, wenn der Termin wegfällt
    app.generiere_auffindbarkeit(str(tmp_path), {(2026, 10): [_t("Lesung")]}, [(2026, 10)], TAG, tracking=False)
    assert [p.name for p in (tmp_path / "kalender").iterdir()] == [f"{app.termin_uid(_t('Lesung'))}.ics"]


def test_sortierung_nach_beginn_nicht_nach_text():
    termine = [_t("Abend", uhrzeit="19.30 Uhr"), _t("Morgen", uhrzeit="9:00–13:00 Uhr"),
               _t("Info", uhrzeit="siehe Website"), _t("Ausstellung", uhrzeit="ganztägig")]
    assert [t.name for t in app._sortierte_termine(termine)] == ["Morgen", "Abend", "Ausstellung", "Info"]


@pytest.mark.parametrize("link", [
    "https://example.test/a\r\nATTACH:https://boese.test/x",
    "https://example.test/a\nEND:VEVENT\nBEGIN:VEVENT",
    "https://example.test/a\rLOCATION:Falsch",
    "https://example.test/a b",
    "javascript:alert(1)",
])
def test_termin_ics_link_kann_keine_zeilen_einschleusen(link):
    ics = app.generiere_termin_ics(_t("Konzert", link=link))
    zeilen = ics.split("\r\n")
    assert not any(z.startswith(("ATTACH", "LOCATION:Falsch", "URL:")) for z in zeilen)
    assert ics.count("BEGIN:VEVENT") == 1 and "\r" not in ics.replace("\r\n", "") and "\n" not in ics.replace("\r\n", "")


def test_termin_ics_text_ohne_einzelnes_cr():
    ics = app.generiere_termin_ics(_t("Konzert\rLOCATION:Falsch", ort="Ort\rX-BOESE:1"))
    assert "\r" not in ics.replace("\r\n", "")
    assert not any(z.startswith(("LOCATION:Falsch", "X-BOESE")) for z in ics.split("\r\n"))


def test_verschobener_termin_im_jsonld_nicht_abgesagt():
    from app import event_jsonld
    t = Termin(name='Lesung', datum=datetime(2026, 10, 20, 19), uhrzeit='19:00 Uhr', ort='Stadtbibliothek',
               link='', abgesagt=True, verschoben_auf='2026-10-30')
    obj = event_jsonld(t)
    assert obj['eventStatus'] == 'https://schema.org/EventRescheduled'
    assert obj['startDate'] == '2026-10-30'
    assert obj['previousStartDate'].startswith('2026-10-20')


def test_tagesseite_navigation_auch_am_seitenende():
    """Rückmeldung Erich: am Ende einer Tagesseite direkt zum nächsten Tag."""
    html = app.generiere_tagesseite(TAG, [_t("A")], ERSTER, LETZTER)
    folgetag = (TAG + timedelta(days=1)).isoformat()
    assert html.count(f'href="{folgetag}.html"') == 2
    assert html.index('aria-label="Tagesnavigation unten"') > html.index('termin-name')


def test_startseite_datum_verlinkt_statt_eigene_seite():
    """Rückmeldung Ralf: „Eigene Seite für diesen Tag“ ist überflüssig, die Überschrift verlinkt."""
    html = app.generiere_startseite(TAG, {TAG: [_t("A")]}, [(TAG.year, TAG.month)], ERSTER, LETZTER)
    assert 'Eigene Seite für diesen Tag' not in html
    assert f'<h2><a href="tag/{TAG.isoformat()}.html">Heute,' in html


def test_kopf_neue_seiten_bricht_langes_wort_nicht():
    """Rückmeldung Ralf: „Veranstaltungskalender“ lief am Desktop ins rechte Bild."""
    assert '.kopf-neu .header-text { flex-shrink: 1; min-width: min-content; }' in app.ZUSATZ_CSS
    assert '.kopf-neu .hebbert' in app.ZUSATZ_CSS


# --- Art-Etikett und JSON-LD-Typ nach Art (Paket C, 14.10.2026) -------------

@pytest.mark.parametrize('art, typ', [
    ('Konzert', 'MusicEvent'), ('Theater/Kabarett', 'TheaterEvent'), ('Party', 'SocialEvent'),
    ('Lesung/Vortrag', 'EducationEvent'), ('Ausstellung/Kunst', 'ExhibitionEvent'),
    ('Kurs/Workshop', 'EducationEvent'), ('Fest/Markt', 'Festival'), ('Kinder/Familie', 'ChildrensEvent'),
    ('Sport/Bewegung', 'SportsEvent'), ('Kino', 'ScreeningEvent'),
    ('Führung', 'Event'), ('Politik', 'Event'), ('Begegnung/Treffen', 'Event'), ('Sonstiges', 'Event'),
    ('', 'Event'),
])
def test_jsonld_typ_nach_art(art, typ):
    assert app.event_jsonld(_t("A", art=art))["@type"] == typ


def test_art_etikett_am_termin():
    html = app._termin_html(_t("Jazz", art='Konzert', kategorie='Musik'))
    assert '<span class="badge badge-art">Konzert</span>' in html
    assert 'badge-kategorie' not in html  # Art ersetzt die Rohkategorie


@pytest.mark.parametrize('art', ['Sonstiges', 'Kino', ''])
def test_kein_art_etikett_bei_sonstiges_und_kino(art):
    html = app._termin_html(_t("X", art=art, kategorie='Bildung'))
    assert 'badge-art' not in html and 'badge-kategorie' not in html


def test_art_etikett_und_typ_auf_tagesseite():
    html = app.generiere_tagesseite(TAG, [_t("A", art='Theater/Kabarett')], ERSTER, LETZTER, tracking=False)
    assert '<span class="badge badge-art">Theater/Kabarett</span>' in html
    events = _jsonld(html)[0]["mainEntity"]["itemListElement"]
    assert [e["@type"] for e in events] == ["TheaterEvent"]


def test_art_etikett_im_stil_mit_dunkelmodus():
    css = app.SEITEN_CSS + app.ZUSATZ_CSS
    assert '.badge-art' in css
    regel = css[css.index('.badge-art'):]
    regel = regel[:regel.index('}')]
    assert 'var(--' in regel  # Farben aus den Variablen, die der Dunkelmodus umstellt
