"""Absagen im Titel oder Beschreibungstext erkennen (ArtLab Kunsthalle, 13.10.2026).

Die Kunsthalle listete das ArtLab am 13.10. normal, im Text stand „DER TERMIN
ENTFÄLLT!“. Eine KI hat es prompt als Tipp empfohlen. Erkannt wird nur, was
eindeutig den Termin selbst betrifft; „Der Eintritt entfällt“ ist keine Absage.
"""
from datetime import datetime

import pytest

from scraper import Termin, ist_absage_text


def _termin(name='ArtLab', beschreibung=''):
    return Termin(name=name, datum=datetime(2026, 10, 13, 14, 40), uhrzeit='14:40 Uhr',
                  ort='Kunsthalle', link='https://example.test/', beschreibung=beschreibung)


@pytest.mark.parametrize('name, beschreibung', [
    ('ArtLab', 'DER TERMIN ENTFÄLLT!'),
    ('ABGESAGT: Lesung mit Max Muster', ''),
    ('Abgesagt - Konzert im Park', ''),
    ('Konzert im Park (abgesagt)', ''),
    ('Konzert im Park – ENTFÄLLT', ''),
    ('Fällt aus: Stadtführung', ''),
    ('AUSFALL: Müsli vor dem offenen Kühlschrank', ''),
    ('Vortrag', 'Die Veranstaltung muss leider entfallen.'),
    ('Vortrag', 'Der Vortrag fällt leider aus.'),
    ('Vortrag', 'Die Veranstaltung wurde abgesagt.'),
    ('Lesung', 'Diese Lesung muss leider abgesagt werden.'),
    ('Kurs', 'Der Kurs findet nicht statt.'),
    ('Vortrag', 'Krankheitsbedingt abgesagt!'),
])
def test_absage_erkannt(name, beschreibung):
    assert ist_absage_text(name, beschreibung)
    assert _termin(name, beschreibung).abgesagt


@pytest.mark.parametrize('name, beschreibung', [
    ('Workshop', 'Der Eintritt entfällt für Mitglieder.'),
    ('Konzert', 'Die Pause entfällt.'),
    ('Eine Absage an den Hass', 'Lesung und Gespräch.'),
    ('Konzert', 'Nachdem das Konzert im letzten Jahr abgesagt wurde, kommt die Band nun zurück.'),
    ('Kurs', 'Die Anmeldung entfällt, einfach vorbeikommen.'),
    ('Theater', 'Das Stück zeigt, warum nichts ausfällt.'),
    ('Ausfallschritt-Training', 'Fitness für Senioren.'),
    ('Vortrag', 'Bei Regen fällt die Führung aus.'),
])
def test_keine_absage(name, beschreibung):
    assert not ist_absage_text(name, beschreibung)
    assert not _termin(name, beschreibung).abgesagt


def test_manuelle_absage_bleibt():
    t = Termin(name='X', datum=datetime(2026, 10, 13), uhrzeit='', ort='', link='', abgesagt=True)
    assert t.abgesagt
