"""Tests für Dedup-Logik in app.py."""
import sys
import os
from datetime import datetime

# app.py liegt im Parent-Verzeichnis
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper import Termin
from app import _termin_score, entferne_duplikate


def _termin(name, quelle, link='', uhrzeit='', beschreibung='', ort=''):
    return Termin(
        name=name,
        datum=datetime(2026, 3, 15),
        uhrzeit=uhrzeit,
        ort=ort,
        link=link,
        beschreibung=beschreibung,
        quelle=quelle,
        kategorie='',
    )


# --- _termin_score ---

def test_veranstalter_score_kein_malus():
    """Ein Veranstalter (z.B. nlgr) bekommt keinen Malus."""
    t = _termin('Konzert', 'nlgr', link='https://nlgr.de', uhrzeit='20:00 Uhr')
    assert _termin_score(t) == 4  # link(2) + uhrzeit(2)


def test_aggregator_bekommt_malus():
    """Stadt RE bekommt −10 Malus."""
    t = _termin('Konzert', 'stadt-re',
                link='https://re.de', uhrzeit='20:00 Uhr',
                beschreibung='Toll', ort='Stadtbibliothek')
    # Basis: 6, nach Malus: -4
    assert _termin_score(t) == -4


def test_vesterleben_bekommt_malus():
    """Vesterleben bekommt −10 Malus."""
    t = _termin('Event', 'vesterleben', link='https://vest.de')
    assert _termin_score(t) == -8  # link(2) - 10


def test_recklinghaeuser_bekommt_malus():
    """Der Recklinghäuser bekommt −10 Malus."""
    t = _termin('Event', 'recklinghaeuser', link='https://re.de')
    assert _termin_score(t) == -8  # link(2) - 10


def test_veranstalter_schlaegt_aggregator_immer():
    """Veranstalter ohne ein einziges Feld (Score 0) schlägt Aggregator mit allem (Score -4)."""
    veranstalter = _termin('Konzert', 'nlgr')  # Score: 0
    aggregator = _termin('Konzert', 'stadt-re',
                         link='https://re.de', uhrzeit='20:00',
                         beschreibung='Text', ort='Ort')  # Score: -4
    assert _termin_score(veranstalter) > _termin_score(aggregator)


# --- entferne_duplikate ---

def test_veranstalter_gewinnt_gegen_aggregator():
    """NLGR-Eintrag bleibt, Stadt-RE-Eintrag wird entfernt."""
    nlgr = _termin('Jahreskonzert NLGR', 'nlgr',
                   link='https://nlgr.de/konzert', uhrzeit='19:30 Uhr')
    stadt_re = _termin('Jahreskonzert NLGR', 'stadt-re',
                       link='https://re.de/x', uhrzeit='19:30 Uhr',
                       beschreibung='Tolle Veranstaltung', ort='Stadtbibliothek')

    ergebnis = entferne_duplikate([nlgr, stadt_re])

    assert len(ergebnis) == 1
    assert ergebnis[0].quelle == 'nlgr'


def test_aggregator_felder_werden_aufgefuellt():
    """NLGR gewinnt, bekommt aber Beschreibung + Ort aus Stadt RE."""
    nlgr = _termin('Jahreskonzert NLGR', 'nlgr',
                   link='https://nlgr.de/konzert', uhrzeit='19:30 Uhr')
    stadt_re = _termin('Jahreskonzert NLGR', 'stadt-re',
                       link='https://re.de/x', uhrzeit='19:30 Uhr',
                       beschreibung='Tolle Veranstaltung', ort='Stadtbibliothek')

    ergebnis = entferne_duplikate([nlgr, stadt_re])

    assert ergebnis[0].beschreibung == 'Tolle Veranstaltung'
    assert ergebnis[0].ort == 'Stadtbibliothek'
    # Link bleibt der NLGR-Link, nicht Stadt-RE-Link
    assert ergebnis[0].link == 'https://nlgr.de/konzert'


def test_zwei_aggregatoren_einer_bleibt():
    """Wenn Stadt RE und Vesterleben das gleiche Event listen, bleibt nur einer."""
    stadt_re = _termin('Stadtfest', 'stadt-re',
                       link='https://re.de', uhrzeit='12:00 Uhr',
                       beschreibung='Großes Fest', ort='Marktplatz')
    vesterleben = _termin('Stadtfest', 'vesterleben',
                          link='https://vest.de')

    ergebnis = entferne_duplikate([stadt_re, vesterleben])

    assert len(ergebnis) == 1
    assert ergebnis[0].quelle == 'stadt-re'  # höherer Basis-Score (−4 vs −8)


def test_uhrzeit_sonderfaelle_kein_bonus():
    """'ganztägig' und 'siehe Website' geben keinen Uhrzeit-Bonus."""
    t_ganztaegig = _termin('Konzert', 'nlgr', uhrzeit='ganztägig')
    t_website = _termin('Konzert', 'nlgr', uhrzeit='siehe Website')
    t_echte_uhrzeit = _termin('Konzert', 'nlgr', uhrzeit='20:00 Uhr')
    assert _termin_score(t_ganztaegig) == 0   # kein Bonus
    assert _termin_score(t_website) == 0       # kein Bonus
    assert _termin_score(t_echte_uhrzeit) == 2  # Uhrzeit-Bonus


def test_zwei_veranstalter_hoeherer_score_gewinnt():
    """Zwischen zwei Veranstaltern gewinnt der mit mehr Informationen."""
    reich = _termin('Konzert NLGR', 'nlgr',
                    link='https://nlgr.de', uhrzeit='20:00 Uhr',
                    beschreibung='Beschreibung', ort='Bühne')
    arm = _termin('Konzert NLGR', 'gastkirche', link='https://gastkirche.de')

    ergebnis = entferne_duplikate([reich, arm])

    assert len(ergebnis) == 1
    assert ergebnis[0].quelle == 'nlgr'


def test_zwei_aggregatoren_gleichstand_reihenfolge():
    """Bei Gleichstand zweier Aggregatoren entscheidet die Eingabe-Reihenfolge."""
    # Beide haben nur einen Link → gleicher Basis-Score (2 - 10 = -8)
    erster = _termin('Stadtfest', 'stadt-re', link='https://re.de')
    zweiter = _termin('Stadtfest', 'vesterleben', link='https://vest.de')

    ergebnis = entferne_duplikate([erster, zweiter])

    assert len(ergebnis) == 1
    assert ergebnis[0].quelle == 'stadt-re'  # erster in der Liste
