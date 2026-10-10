"""Regressionstests aus dem Lauf vom 10.10.2026: echte Paare aus dem Dedup-Log.

Falsch zusammengeführt wurden Teilstrings mitten im Wort ("gustav" in "gustave"),
Termine derselben Quelle und Paare, die nur ein Allerweltswort teilten.
"""
import pytest

from tests.test_dedup import _termin
from app import entferne_duplikate

FALSCH = [
    ('"Seinem Gewissen verpflichtet" - Gustav Heinemann', 'ev-akademie',
     'Sonderausstellung „Ich, Gustave Courbet“ im Folkwang-Museum', 'seniorenbeirat'),
    ('Auf dem Weg zur Weihnacht', 'stadt-re',
     'André Rieus Weihnachtskonzert 2026: Let it Snow', 'cineworld'),
    ('Das PortAl Formidabel – Träumen unterm Sternenhimmel', 're-leuchtet',
     'Sonne, Mond und Sterne (ab 5)', 'sternwarte'),
    ('Der kleine Weihnachtsgeist', 'stadt-re',
     'Manga-Workshop in der Augustinessenstraße: Weihnachts-Spezial', 'stadtbibliothek'),
    ('Eltern helfen Eltern. Pflegegrad beantragen für Kinder und Jugendliche', 'vhs',
     'Lichterlauf für Kinder', 're-leuchtet'),
    ('iPhone und iPad Grundkurs für Anfänger*innen', 'vhs',
     'Smartphone ganz einfach: Grundkurs für Anfänger*innen', 'vhs'),
    ('Melodien unter Sternen II – Musik zum Träumen', 're-leuchtet',
     'Das PortAl Formidabel – Träumen unterm Sternenhimmel', 're-leuchtet'),
    ('Öffentliche Themenführung: Teufel und Dämonen', 'vesterleben',
     'Öffentliche Führung', 'kunsthalle'),
    ('Online-Vortrag: Zwischen Maria Himmelfahrt und St. Martin – Brauchtum, Himmel und Jahreslauf', 'sternwarte',
     'Rathausshow – Träume unterm Sternhimmel', 're-leuchtet'),
    ('Rathausshow – Träume unterm Sternhimmel', 're-leuchtet',
     'Drohnenshow am Rathaus', 're-leuchtet'),
    ('Sitzung des Haupt- und Finanzausschusses', 'ratssitzungen',
     'Sitzung AK Soziales', 'seniorenbeirat'),
]

RICHTIG = [
    ('Abschlusswochenende mit DJ Moguai', 'manuell', 'DJ Moguai auf dem Rathausplatz', 're-leuchtet'),
    ('Ausstellungseröffnung; Waldemar Grabelus - "Vest im Blick"', 'stadt-re',
     '"Vest im Blick" Vernissage 02.10.26 um 17 Uhr in der Galerie VestQuartier', 'stadtlabor'),
    ('Bring you own Community', 'vesterleben', 'Bring your own Community', 'altstadtschmiede'),
    ('Der Schrei des Himmels – Astronomie in der Kunst', 'vesterleben',
     'Vortragreihe: Astronomie in der Kunst - von der Renaissance bis zur Moderne', 'sternwarte'),
    ('Georg Möllers: Franziskanische Spuren in Recklinghausen – zum 800. Todestag von Franz von Assisi', 're-leuchtet',
     'Auf den franziskanischen Spuren in Recklinghausen bis heute', 'stadt-re'),
    ('Henze100: WO BIST DU DENN, und wo bin ich?', 'stadt-re',
     'HENZE 100 – Briefwechsel zwischen Ingeborg Bachmann und Max Frisch', 'nlgr'),
    ('Herbert Knebels Affentheater | Recklinghausen', 'facebook',
     'Herbert Knebels Affentheater - Voll Karacho!', 'stadt-re'),
    ('Infoveranstaltung zum Thema: "Pubertät"', 'vesterleben',
     'Pubertät im Blick: Eltern im Gespräch', 'stadt-re'),
    ('Jazz-Session', 'vesterleben', 'Jazz Einsteiger-Session', 'altstadtschmiede'),
    ('Rock-Pop-Aktusik-Session', 'vesterleben', 'Rock-Pop-Akustik-Session', 'altstadtschmiede'),
    ('Sitzung des Seniorenbeirates der Stadt Recklinghausen', 'ratssitzungen',
     'Öffentliche Sitzung Seniorenbeirat Recklinghausen', 'seniorenbeirat'),
    ('Stimmen aus dem Exil', 'gegendruck', 'Stimmen aus dem&nbsp;EXIL', 'nlgr'),
    ('Disco Fox Night', 'vesterleben', 'Discofox-Party', 'backyard'),
]


@pytest.mark.parametrize('name_a,quelle_a,name_b,quelle_b', FALSCH)
def test_kein_duplikat(name_a, quelle_a, name_b, quelle_b):
    ergebnis = entferne_duplikate([_termin(name_a, quelle_a), _termin(name_b, quelle_b)])
    assert len(ergebnis) == 2


@pytest.mark.parametrize('name_a,quelle_a,name_b,quelle_b', RICHTIG)
def test_duplikat(name_a, quelle_a, name_b, quelle_b):
    ergebnis = entferne_duplikate([_termin(name_a, quelle_a), _termin(name_b, quelle_b)])
    assert len(ergebnis) == 1
