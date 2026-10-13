from datetime import date, datetime

from scraper import Termin
from app import generiere_html, generiere_tagesseite


def test_jsonld_kein_script_ausbruch():
    t = Termin(name='Böse</script><script>alert(1)</script>', datum=datetime(2026, 10, 10, 14),
               uhrzeit='14:00 Uhr', ort='Altstadtschmiede', link='', beschreibung='',
               quelle='altstadtschmiede', kategorie='Kultur')
    html = generiere_html([t], 2026, 10, [(2026, 10)], dateiname='termine_re_2026_10.html')
    ld = html.split('<script type="application/ld+json">', 1)[1].split('</script>', 1)[0]
    assert '<' not in ld
    # Die Events selbst stehen im JSON-LD der Tagesseite
    tagesseite = generiere_tagesseite(date(2026, 10, 10), [t], date(2026, 10, 1), date(2026, 10, 31))
    ld = tagesseite.split('<script type="application/ld+json">', 1)[1].split('</script>', 1)[0]
    assert '<' not in ld
    assert '\\u003c/script' in ld


def test_link_kann_href_nicht_verlassen():
    t = Termin(name='Konzert', datum=datetime(2026, 10, 10, 20), uhrzeit='20:00 Uhr', ort='X',
               link='https://example.org/a"onmouseover="alert(1)', beschreibung='',
               quelle='eventim', kategorie='Konzert')
    html = generiere_html([t], 2026, 10, [(2026, 10)], dateiname='termine_re_2026_10.html')
    assert '/a"onmouseover' not in html  # JSON-LD enthält es korrekt als /a\\"
    assert 'href="https://example.org/a&quot;onmouseover=&quot;alert(1)"' in html
