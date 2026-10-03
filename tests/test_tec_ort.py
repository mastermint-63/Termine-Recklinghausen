from scraper import _tec_ort


def test_venue_objekt():
    assert _tec_ort({'venue': {'venue': 'Institut f&uuml;r Stadtgeschichte'}}) == 'Institut für Stadtgeschichte'


def test_venue_leere_liste():
    assert _tec_ort({'venue': []}) == 'Recklinghausen'


def test_venue_fehlt_oder_leer():
    assert _tec_ort({}) == 'Recklinghausen'
    assert _tec_ort({'venue': {'venue': ''}}) == 'Recklinghausen'
