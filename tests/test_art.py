"""Einheitliche Art für alle Termine (Paket B, 14.10.2026).

Anlass: Rückmeldung Erich, die Suche nach „Konzert“ fand viele Konzerte nicht,
weil jede Quelle eigene Kategorien liefert (die Stadt gar keine). Die Fälle
stammen aus der Durchsicht der 1.299 Termine in vorschau/termine_cache.json.
"""
from datetime import datetime

import pytest

from app import entferne_duplikate
from arten import ARTEN, bestimme_art, setze_arten
from scraper import Termin


def _t(name, quelle='stadt-re', kategorie='', beschreibung='', uhrzeit='19:00 Uhr'):
    return Termin(name=name, datum=datetime(2026, 10, 16), uhrzeit=uhrzeit, ort='Recklinghausen',
                  link='', beschreibung=beschreibung, quelle=quelle, kategorie=kategorie)


def test_artenliste_fest():
    assert ARTEN[-1] == 'Sonstiges'
    assert 'Konzert' in ARTEN and 'Party' in ARTEN and 'Kino' in ARTEN
    assert len(ARTEN) == len(set(ARTEN))


# Pflichtfälle aus dem Auftrag
@pytest.mark.parametrize('name, quelle, kategorie, art', [
    ('Rock-Pop-Akustik-Session', 'altstadtschmiede', 'Kultur', 'Konzert'),
    ('Jazz in der Kunsthalle – Die Sparda Lounge', 'kunsthalle', 'Kunst', 'Konzert'),
    ('Max Hagen Trio', 'backyard', 'Musik', 'Konzert'),
    ('Godzilla in the Kitchen, Mudfinger', 'backyard', 'Musik', 'Konzert'),
    ('2. Sinfoniekonzert - Lieben Sie Brahms?', 'stadt-re', '', 'Konzert'),
    ('1. Familienkonzert: Kuscheltierkonzert', 'stadt-re', '', 'Konzert'),
    ('Dark Revival Party im mOOndock', 'moondock', 'Party', 'Party'),
    ('Sitzung des Haupt- und Finanzausschusses', 'ratssitzungen', 'Politik', 'Politik'),
    ('Die verlorene Sprache', 'cineworld', 'Kino', 'Kino'),
])
def test_pflichtfaelle(name, quelle, kategorie, art):
    assert bestimme_art(_t(name, quelle, kategorie)) == art


def test_blickpunkt_auge_kein_konzert():
    t = _t('"Blickpunkt Auge"-Beratung', 'manuell', 'Sonstiges',
           beschreibung='Beratung rund um Sehbehinderung, kein Punk und keine Band.')
    assert bestimme_art(t) != 'Konzert'


# 1. Eindeutige Quellen
@pytest.mark.parametrize('name, quelle, kategorie, art', [
    ('Der Sternenhimmel des Monats', 'sternwarte', 'Astronomie', 'Lesung/Vortrag'),
    ('Ausflug zu den Sternen (ab 5)', 'sternwarte', 'Astronomie', 'Lesung/Vortrag'),
    ('Physik in Science Fiction-Filmen', 'sternwarte', 'Astronomie', 'Lesung/Vortrag'),
    ('Livekonzert! Knud Krautwig und Daniel Brandl sind Lithium', 'sternwarte', 'Astronomie', 'Konzert'),
    ('Keltika – Klänge aus der Anderswelt', 'sternwarte', 'Astronomie', 'Lesung/Vortrag'),
    # Musikprogramme im Planetarium laufen vom Band
    ('Musik im Sternenzelt', 'sternwarte', 'Astronomie', 'Lesung/Vortrag'),
    ('Musik. Zeit. Raum. - Musikprogramm im Planetarium', 'sternwarte', 'Astronomie', 'Lesung/Vortrag'),
    ('Livekonzert! Duo Gastspiel – Live unterm Sternenzelt!', 'sternwarte', 'Astronomie', 'Konzert'),
    ('Folk/Lyrik Livekonzert! From Shore To Shore', 'sternwarte', 'Astronomie', 'Konzert'),
    ('Zac Schulze Gang', 'backyard', 'Musik', 'Konzert'),
    # VHS-Kurse (mehrere Termine) bleiben Kurse, auch mit Yoga oder Schauspiel im Titel
    ('Kraft und Ruhe – Yoga für junge Menschen', 'vhs', 'Kurs', 'Kurs/Workshop'),
    ('Bühne frei! Entdecke dein Schauspieltalent', 'vhs', 'Kurs', 'Kurs/Workshop'),
    ('Literatur lebendig vortragen', 'vhs', 'Kurs', 'Kurs/Workshop'),
])
def test_quelle(name, quelle, kategorie, art):
    assert bestimme_art(_t(name, quelle, kategorie)) == art


# 2. Stichworte im Titel, auch gegen die Rohkategorie
@pytest.mark.parametrize('name, quelle, kategorie, art', [
    ('Jazz Einsteiger-Session', 'altstadtschmiede', 'Kultur', 'Konzert'),
    ('Rock-Pop-Aktusik-Session', 'vesterleben', 'Kultur', 'Konzert'),
    ('Allen-Forrester Band', 'vesterleben', 'Kultur', 'Konzert'),
    ('Akkordeonensemble REacction', 're-leuchtet', 'Kultur', 'Konzert'),
    ('Chorgemeinschaft St. Elisabeth', 're-leuchtet', 'Kultur', 'Konzert'),
    ('Schulchor', 're-leuchtet', 'Kultur', 'Konzert'),
    ('Gastspiel Akustikduo', 're-leuchtet', 'Kultur', 'Konzert'),
    ('„The Glams“, Live-Musik mit Verena und Meike', 're-leuchtet', 'Kultur', 'Konzert'),
    ('Live-Musik im Recklinghäuser: Desert Style', 'recklinghaeuser', '', 'Konzert'),
    ('Mohito Royal (Punkrock unplugged)', 'manuell', 'Konzert', 'Konzert'),
    ('Johann Sebastian Bach: Weihnachtsoratorium', 'stadt-re', '', 'Konzert'),
    ('Blues in der Bude: Greyhoud Georg Duo', 'stadt-re', '', 'Konzert'),
    ('Kaffee- und Kuchenkonzert des Jugendsinfonieorchesters', 'stadt-re', '', 'Konzert'),
    ('Geistliche Abendmusik', 'stadt-re', '', 'Konzert'),
    ('Tom Gaebel & His Orchestra: Best of', 'stadt-re', '', 'Konzert'),
    ('Peter Orloff & Schwarzmeer Kosaken-Chor - Abschiedskonzert', 'eventim', 'Konzert', 'Konzert'),
    ('Ein Abend zum Mitsingen mit "Sing-a-long" Duo', 'stadt-re', '', 'Konzert'),
    ('Funzelparty', 'stadt-re', '', 'Party'),
    ('ü30 PARTY', 'subergs', '', 'Party'),
    ('DJ Moguai auf dem Rathausplatz', 're-leuchtet', 'Kultur', 'Party'),
    ('Aladin - das Musical', 'stadt-re', '', 'Theater/Kabarett'),
    ('Herbert Knebels Affentheater - Voll Karacho!', 'stadt-re', '', 'Theater/Kabarett'),
    ('Martha and Me – English theatre', 'stadt-re', '', 'Theater/Kabarett'),
    ('Lesung mit Lena Schätte: "Das Schwarz an den Händen meines Vaters"', 'stadtbibliothek', 'Bibliothek', 'Lesung/Vortrag'),
    ('Multivisionsvortrag mit Bergsteigerlegende Thomas Huber', 'stadt-re', '', 'Lesung/Vortrag'),
    ('Silent Reading Party - In Ruhe und Gemeinschaft lesen', 'stadt-re', '', 'Lesung/Vortrag'),
    ('Öffentliche Führung', 'kunsthalle', 'Kunst', 'Führung'),
    ('Öffentliche Themenführung: Teufel und Dämonen', 'ikonen-museum', 'Kunst', 'Führung'),
    ('Kuratorinnen-Führung durch die RETRO STATION', 'stadt-re', '', 'Führung'),
    ('Nachts im Museum - Taschenlampenführung in der Retro Station', 're-leuchtet', 'Kultur', 'Führung'),
    ('Stadtgang von unten', 'gastkirche', 'Veranstaltungen', 'Führung'),
    ('Workshop für Kinder zur Advents- und Weihnachtszeit', 'ikonen-museum', 'Kunst', 'Kurs/Workshop'),
    ('Inklusiver Erste Hilfe Kurs für Menschen mit und ohne Behinderung', 'stadt-re', '', 'Kurs/Workshop'),
    ('Bilderbuchkino in Süd', 'stadtbibliothek', 'Bibliothek', 'Kinder/Familie'),
    ('Babytreff im Familienbüro (jeden Montag)', 'stadt-re', '', 'Kinder/Familie'),
    ('Ausstellungseröffnung; Brigitte Albers "verthing flows"', 'stadt-re', '', 'Ausstellung/Kunst'),
    ('Licht ART in der Sterngasse', 're-leuchtet', 'Kultur', 'Ausstellung/Kunst'),
    ('Trödelmarkt Vestlandhalle', 'vesterleben', 'Kultur', 'Fest/Markt'),
    ('MITTELALTERMERKT', 'zeche-klaerchen', '', 'Fest/Markt'),
    ('Ukrainefest', 'gastkirche', 'Veranstaltungen', 'Fest/Markt'),
    ('Tonie-Tauschbörse', 'stadtbibliothek', 'Bibliothek', 'Fest/Markt'),
    ('Sitztanz', 'stadt-re', '', 'Sport/Bewegung'),
    ('LINE DANCE trifft auf Karneval', 'stadt-re', '', 'Sport/Bewegung'),
    ('ADFC Feierabend-Tour – Fahrt ins Blaue', 'vesterleben', 'Kultur', 'Sport/Bewegung'),
    ('Öffentliche Sitzung Seniorenbeirat Recklinghausen', 'seniorenbeirat', 'Senioren', 'Politik'),
    ('Queerer Stammtisch', 'altstadtschmiede', 'Kultur', 'Begegnung/Treffen'),
    ('Repair Café', 'facebook', '', 'Begegnung/Treffen'),
    ('Film „Die verlorene Sprache” von Samira Klaho', 'nlgr', 'Literatur', 'Kino'),
    ('Nachspiel - Ein Kino-Dokumentarfilm von Christoph Hühner', 'vhs', 'Bildung', 'Kino'),
])
def test_titel(name, quelle, kategorie, art):
    assert bestimme_art(_t(name, quelle, kategorie)) == art


# Fehlalarme: Wortteile und mehrdeutige Wörter
@pytest.mark.parametrize('name, quelle, kategorie, nicht', [
    ('Bandscheibe und Rücken: Vortrag', 'vhs', 'Bildung', 'Konzert'),
    ('Internationales Sprachcafé mit Bandura', 'genial-re', 'Begegnung', 'Konzert'),
    ('Ausflug zu den Sternen (ab 5)', 'vesterleben', 'Kultur', 'Fest/Markt'),
    ('Führung & Gewaltfreie Kommunikation.', 'vhs', 'Bildung', 'Führung'),
    ('Fit für Vereinsführung - Satzungsrecht', 'vhs', 'Bildung', 'Führung'),
    ('Trump und die MAGA-Bewegung', 'vhs', 'Bildung', 'Sport/Bewegung'),
    ('Abstand und Distanz im Alltag', 'vhs', 'Bildung', 'Sport/Bewegung'),
    ('Ruhrpolen und Reichstagswahlen', 'geschichte-re', 'Geschichte', 'Politik'),
    ('Lesen und Schreiben im Alltag (Exkursion)', 'vhs', 'Bildung', 'Lesung/Vortrag'),
    ('Als die Bilder laufen lernten. Von der Kinematographen-Bude bis zum Cinemax-Kino', 'vhs', 'Bildung', 'Kino'),
    ('Kopfkino: Ein Hörspiel gemeinsam genießen', 'stadtbibliothek', 'Bibliothek', 'Kino'),
    ('Vortrag Bauen mit Steinkörben und Geokunststoffen', 'geschichte-re', 'Geschichte', 'Ausstellung/Kunst'),
    ('Großer Karnevalssitzung der KG', 'stadt-re', '', 'Politik'),
    ('Der Arbeitsmarkt im Wandel', 'vhs', 'Bildung', 'Fest/Markt'),
    ('Ein Diskurs über Europa', 'vhs', 'Bildung', 'Kurs/Workshop'),
    ('Medidativer Tanzabend', 'gastkirche', 'Veranstaltungen', 'Party'),
    ('Grüne Erbsen und Kleine Rote Punkte - Schwarze Löcher', 'sternwarte', 'Astronomie', 'Konzert'),
    ('Entscheidungen leichter treffen', 'vhs', 'Bildung', 'Begegnung/Treffen'),
])
def test_fehlalarme(name, quelle, kategorie, nicht):
    assert bestimme_art(_t(name, quelle, kategorie)) != nicht


def test_singen_und_lieder():
    # Offenes Singen der Chöre ist ein Auftritt, gemeinsames Singen ein Treffen
    assert bestimme_art(_t('Adventssingen')) == 'Konzert'
    assert bestimme_art(_t('Miteinander singen', 'gastkirche', 'Veranstaltungen')) == 'Begegnung/Treffen'
    # Mitmachprojekt mit Rezepttausch, kein Konzert
    assert bestimme_art(_t('Die Lieder meiner Nachbar*innen', 'altstadtschmiede', 'Kultur')) != 'Konzert'


def test_kino_theater_ist_vortrag():
    name = ('Als die Bilder laufen lernten. Von der Kinematographen-Bude bis zum Cinemax-Kino '
            'auf den Spuren der Recklinghäuser Kino-Theater')
    assert bestimme_art(_t(name, 'vhs', 'Bildung')) == 'Lesung/Vortrag'
    assert bestimme_art(_t('Recklinghäuser Lichtspieltheater', 'stadt-re', '')) == 'Sonstiges'


@pytest.mark.parametrize('name', [
    'Makramee entdecken im Herbst - Weihnachtsdeko',
    'Bienenwachskerzen selber herstellen',
    'Kunst, Kaffee, Kuchen: Keramik bemalen mit Adnan Kassim',
])
def test_basteln_ist_workshop(name):
    assert bestimme_art(_t(name, 'vhs', 'Bildung')) == 'Kurs/Workshop'


def test_treffen_als_name():
    assert bestimme_art(_t('Treffen - Agenda Forum (Öffentlich)', 'agenda21', 'Ehrenamt')) == 'Begegnung/Treffen'
    assert bestimme_art(_t('Monatstreffen', 'genial-re', '')) == 'Begegnung/Treffen'


# 3. Beschreibung nur mit eindeutigen Wörtern
def test_beschreibung_konzert():
    t = _t('Smetana in Turnschuhen: „Má vlast“', beschreibung='Ein Konzert für die ganze Familie.')
    assert bestimme_art(t) == 'Konzert'


def test_beschreibung_mehrdeutiges_wort_zaehlt_nicht():
    t = _t('Herzfaden', beschreibung='Eine Geschichte über eine Band und ihre Freunde.')
    assert bestimme_art(t) == 'Sonstiges'


@pytest.mark.parametrize('beschreibung, art', [
    ('Nach dem Roman von Dörte Hansen Ohnsorg Theater Ein Bauernhaus …', 'Theater/Kabarett'),
    ('ab 4 Jahren Burghofbühne Dinslaken Im Land der Träume …', 'Theater/Kabarett'),
    ('Impro-Comedy Sitzplatz aussuchen …', 'Theater/Kabarett'),
    ('Oratorium für Soli, Chor und Orchester', 'Konzert'),
    ('Freuen Sie sich auf ein besinnliches Gesangskonzert.', 'Konzert'),
    ('Mit dem Radreisevortrag Roadtrip Oman beginnt der ADFC …', 'Lesung/Vortrag'),
    # „Großkonzerne“ ist kein Konzert
    ('Daraus gingen Großkonzerne hervor. Der Vortrag untersucht …', 'Lesung/Vortrag'),
    ('Beim Rundgang durch das stadtgeschichtliche Museum werden Sprichwörter erklärt.', 'Führung'),
    ('Die Führung spannt den Bogen von der Naturaltauschwirtschaft …', 'Führung'),
    ('Felix Feldmann präsentiert Lichtjonglage auf einem Rundgang durch das Kulturquartier.', 'Sonstiges'),
    # gemischtes Programm bleibt offen
    ('Musikalische Vorführungen und Vorträge in der Gymnasialkirche', 'Sonstiges'),
])
def test_beschreibung(beschreibung, art):
    assert bestimme_art(_t('Ohne Stichwort', 're-leuchtet', 'Kultur', beschreibung=beschreibung)) == art


def test_titel_vor_beschreibung():
    t = _t('Lesung mit Arne Semsrott', 'altstadtschmiede', 'Kultur',
           beschreibung='Im Anschluss Konzert der Hausband.')
    assert bestimme_art(t) == 'Lesung/Vortrag'


# 4. Rohkategorie
@pytest.mark.parametrize('name, quelle, kategorie, art', [
    ('Pirates in black', 'vesterleben', 'Musik', 'Konzert'),
    ('Debut um 11', 'debut-um-11', 'Konzert', 'Konzert'),
    ('Die heilige Johanna der Schlachthöfe', 'gegendruck', 'Theater', 'Theater/Kabarett'),
    ('Spanisch A1.1 Bildungsurlaub', 'vhs', 'Kurs', 'Kurs/Workshop'),
    ('Auf ein Gläschen', 'genial-re', 'Begegnung', 'Begegnung/Treffen'),
    ('Seniorenbüro', 'seniorenbeirat', 'Senioren', 'Begegnung/Treffen'),
    ('Zum Heid-, Weihnachts- und Pfingstsee', 'adfc', 'Radtour', 'Sport/Bewegung'),
    ('Heldengeschichten - von der Ikone zum Comic', 'ikonen-museum', 'Kunst', 'Ausstellung/Kunst'),
    ('Wie geht es weiter in den USA unter Trump?', 'ev-akademie', 'Bildung', 'Lesung/Vortrag'),
    ('Hochlarer Bauernmarkt', 'manuell', 'Fest', 'Fest/Markt'),
])
def test_rohkategorie(name, quelle, kategorie, art):
    assert bestimme_art(_t(name, quelle, kategorie)) == art


def test_sonst_sonstiges():
    assert bestimme_art(_t('KI:MBISS - KI zum Mitnehmen', 'stadt-re', '')) == 'Sonstiges'
    assert bestimme_art(_t('DIALOG e.V.', 'altstadtschmiede', 'Kultur')) == 'Sonstiges'


def test_setze_arten():
    termine = [_t('Funzelparty'), _t('Altes Land')]
    setze_arten(termine)
    assert [t.art for t in termine] == ['Party', 'Sonstiges']


# Dubletten: der behaltene Termin übernimmt eine bessere Art
def test_dublette_uebernimmt_art():
    sternwarte = _t('Ausflug zu den Sternen (ab 5)', 'stadt-re', '')
    vesterleben = _t('Ausflug zu den Sternen (ab 5)', 'vesterleben', 'Musik')
    termine = [sternwarte, vesterleben]
    setze_arten(termine)
    assert sternwarte.art == 'Sonstiges'
    ergebnis = entferne_duplikate(termine)
    assert len(ergebnis) == 1
    assert ergebnis[0].art == 'Konzert'


def test_dublette_behaelt_eigene_art():
    nlgr = _t('Stimmen aus dem Exil', 'nlgr', 'Literatur')
    gegendruck = _t('Stimmen aus dem Exil', 'stadt-re', 'Theater')
    termine = [nlgr, gegendruck]
    setze_arten(termine)
    ergebnis = entferne_duplikate(termine)
    assert len(ergebnis) == 1
    assert ergebnis[0].art == 'Lesung/Vortrag'


def test_dublette_ohne_art_bleibt_leer_ohne_fehler():
    # hw_import nutzt entferne_duplikate() ohne setze_arten()
    ergebnis = entferne_duplikate([_t('Funzelparty'), _t('Funzelparty', 'vesterleben')])
    assert len(ergebnis) == 1
    assert ergebnis[0].art == ''


def test_art_nicht_im_stand():
    import app
    t = _t('Funzelparty')
    setze_arten([t])
    assert 'art' not in app._termin_zu_dict(t)
