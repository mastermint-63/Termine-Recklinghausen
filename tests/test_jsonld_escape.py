from datetime import datetime

from scraper import Termin
from app import generiere_html


def test_jsonld_kein_script_ausbruch():
    t = Termin(name='Böse</script><script>alert(1)</script>', datum=datetime(2026, 10, 10, 14),
               uhrzeit='14:00 Uhr', ort='Altstadtschmiede', link='', beschreibung='',
               quelle='altstadtschmiede', kategorie='Kultur')
    html = generiere_html([t], 2026, 10, [(2026, 10)], dateiname='termine_re_2026_10.html')
    ld = html.split('<script type="application/ld+json">', 1)[1].split('</script>', 1)[0]
    assert '<' not in ld
    assert '\\u003c/script' in ld
