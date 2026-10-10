from scraper import _altstadtschmiede_uhrzeit


def test_zeitspanne_ohne_minuten_nimmt_beginn():
    # Repair Café 10.10.2026: "14-16 Uhr" stand vorher als 16:00 Uhr im Kalender
    assert _altstadtschmiede_uhrzeit('10.10. / 14-16 Uhr / kostenfreies Angebot') == (14, 0)


def test_zeitspanne_mit_bis():
    assert _altstadtschmiede_uhrzeit('Von 14:00 bis 16:00 Uhr können Besucher*innen') == (14, 0)


def test_zeitspanne_mit_gedankenstrich():
    assert _altstadtschmiede_uhrzeit('12.11. / 19.30 – 22 Uhr') == (19, 30)


def test_einzelne_uhrzeit():
    assert _altstadtschmiede_uhrzeit('09.02. / 18 Uhr / VVK 12 €') == (18, 0)
    assert _altstadtschmiede_uhrzeit('Einlass 19.30 Uhr') == (19, 30)


def test_keine_uhrzeit():
    assert _altstadtschmiede_uhrzeit('Ganztägig geöffnet') is None
