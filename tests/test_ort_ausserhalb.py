"""Ortsfilter (Paket A, 14.10.2026): Termine in anderen Städten fallen raus.

Entscheidung FS: Ausflüge in andere Städte werden gestrichen, auch wenn der
Veranstalter aus Recklinghausen kommt. Die Gegenbeispiele stammen aus der
Gegenprobe an den 1.299 Terminen in vorschau/termine_cache.json.
"""
from datetime import datetime

import pytest

from app import entferne_ausserhalb, ist_ausserhalb
from scraper import Termin


def _t(ort, name='Termin', quelle='stadt-re'):
    return Termin(name=name, datum=datetime(2026, 10, 15), uhrzeit='10:00 Uhr',
                  ort=ort, link='', quelle=quelle)


AUSSERHALB = [
    'Folkwang Museum Essen',
    'Bochum',
    'Bochumer Kulturrat e.V., Lothringer Straße 36c, Bochum',
    'Marien Hospital Herne, Hölkeskampring 40, 44625 Herne, Deutschl',
    'Treffpunkt: Parkplatz am Wasserschloss Lembeck',
    'Zeche Ewald, Herten',
    'Herten',
    'Ausflug nach Münster',
    'Tagesfahrt in Düsseldorf, Treffpunkt Hauptbahnhof',
    'Haltern am See',
    'Seestraße 1, Haltern am See',
    'Mülheim an der Ruhr',
    'Gelsenkirchen-Buer',
    'Essen-Steele, Grendplatz',
    'Castrop-Rauxel',
    'Oer-Erkenschwick',
    'Musterweg 1, 44135 Musterstadt',
]

DRIN = [
    'Stadtbibliothek Augustinessenstraße 3',
    'Galerie VestQuartier, Augustinessenstraße 3, 45657 Recklinghausen (2. OG)',
    'Gemeinsames Mittagessen im Gasthaus',
    'Essen & Trinken im Innenhof',
    'Essen und Trinken',
    'Online (Zoom)',
    'online',
    'Online-Seminar, Referentin aus Essen',
    'Cineworld, Kemnastr. 3',
    'Cineworld',
    '',
    'Caritashaus Reginalda, Weißenburgstraße 20, Recklinghausen-Süd',
    'Bürgerhaus Süd',
    'Bochumer Straße 123, Recklinghausen',
    'Eyüp-Sultan-Moschee (Islamische Kulturunion), Bochumer Straße 98A, Recklinghausen',
    'Bei Sami, Hammer Str. 1 (ehemals Hotel Wüller)',
    'Weinhandlung Molitor, Hertener Str. 59, 45657 Recklinghausen',
    'Drübbelken, Münsterstr. 5, 45657 Recklinghausen',
    'DRK, Kölner Str. 20, RE',
    'Mahnmal Ecke Herzogswall/ Westerholter Weg',
    'Zeitreise Strom – Das Deutsche Elektrizitätsmuseum, Uferstraße 2-4',
    'Zeche Klärchen, Hochlarmark',
    'Drachenbrücke, Hochlarmark, Recklinghausen',
    'Fahrschule Flögel',
    'Paritätischer Wohlfahrtsverband Gehörlosenzentrum',
    'mOOndock, Alte Grenzstr. 153 D, 45663 Recklinghausen',
    'PlanetariumEintritt: 15 €, ermäßigt 11 €. Kartenreservierungen unter 02361- 23134 oder info@sternwarte-recklinghausen.de',
    'Herten-Fan-Treff, Suderwich',
]


@pytest.mark.parametrize('ort', AUSSERHALB)
def test_andere_stadt_faellt_raus(ort):
    assert ist_ausserhalb(_t(ort)), ort


@pytest.mark.parametrize('ort', DRIN)
def test_recklinghausen_bleibt(ort):
    assert not ist_ausserhalb(_t(ort)), ort


def test_courbet_essen_wird_gefiltert_und_geloggt(capsys):
    courbet = _t('Folkwang Museum Essen',
                 name='Sonderausstellung „Ich, Gustave Courbet“ im Folkwang-Museum',
                 quelle='seniorenbeirat')
    bibliothek = _t('Stadtbibliothek, Augustinessenstraße 3', name='Lesung')
    ergebnis = entferne_ausserhalb([courbet, bibliothek])
    assert ergebnis == [bibliothek]
    log = capsys.readouterr().out
    assert ('[Ort] ausserhalb: 15.10.2026 Sonderausstellung „Ich, Gustave Courbet“ '
            'im Folkwang-Museum (Folkwang Museum Essen)') in log


def test_gilt_auch_fuer_manuelle_termine():
    assert ist_ausserhalb(_t('Folkwang Museum Essen', quelle='manuell'))


def test_name_allein_entscheidet_nicht():
    # Nur der Ort zählt, ein Städtename im Titel filtert nichts
    assert not ist_ausserhalb(_t('Stadtbibliothek', name='Lesung: Ein Sommer in Essen'))
