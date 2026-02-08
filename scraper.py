"""Scraper für Veranstaltungen in Recklinghausen aus mehreren Quellen."""

import json
import re
import requests
from dataclasses import dataclass
from datetime import datetime
from calendar import monthrange
from html import unescape
from bs4 import BeautifulSoup


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

# URLs
REGIOACTIVE_URL = "https://www.regioactive.de/events/22868/recklinghausen/veranstaltungen-party-konzerte"
STADT_RE_URL = "https://www.recklinghausen.de/inhalte/startseite/_veranstaltungskalender/"
ALTSTADTSCHMIEDE_URL = "https://www.altstadtschmiede.de/aktuelle-veranstaltungen"
VESTERLEBEN_URL = "https://vesterleben.de/termine-alle"
STERNWARTE_URL = "https://sternwarte-recklinghausen.de/programm/veranstaltungskalender/"
KUNSTHALLE_URL = "https://kunsthalle-recklinghausen.de/en/program/calendar"
STADTBIBLIOTHEK_URL = "https://www.recklinghausen.de/inhalte/startseite/familie_bildung/stadtbibliothek/Veranstaltungen/index.asp"
NLGR_URL = "https://nlgr.de/veranstaltungen/"
LITERATURTAGE_URL = "https://literaturtage-recklinghausen.de/veranstaltungen/"
VHS_BASE_URL = "https://www.vhs-recklinghausen.de"
AKADEMIE_URL = "https://www.ahademie.com/veranstaltungen/"
STADTARCHIV_PDF_BASE = "https://www.recklinghausen.de/Inhalte/Startseite/Ruhrfestspiele_Kultur/Dokumente"


@dataclass
class Termin:
    """Ein Termin/Event in Recklinghausen."""
    name: str
    datum: datetime
    uhrzeit: str
    ort: str
    link: str
    beschreibung: str = ''
    quelle: str = ''
    kategorie: str = ''

    def datum_formatiert(self) -> str:
        tage = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
        return f"{tage[self.datum.weekday()]} {self.datum.strftime('%d.%m.%Y')}"

    def __lt__(self, other):
        return (self.datum, self.uhrzeit, self.name) < (other.datum, other.uhrzeit, other.name)


def _html_zu_text(html: str) -> str:
    """Konvertiert HTML zu reinem Text."""
    text = re.sub(r'<br\s*/?>', '\n', html)
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    return text.strip()


def _im_monat(datum: datetime, jahr: int, monat: int) -> bool:
    """Prüft ob ein Datum im gewünschten Monat liegt."""
    return datum.year == jahr and datum.month == monat


# ---------------------------------------------------------------------------
# 1. RegioActive.de — JSON-LD ItemList
# ---------------------------------------------------------------------------

def hole_regioactive(jahr: int, monat: int) -> list[Termin]:
    """Holt Events von regioactive.de via JSON-LD structured data."""
    try:
        response = requests.get(REGIOACTIVE_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (regioactive): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    termine = []

    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue

        if data.get('@type') != 'ItemList':
            continue

        for item in data.get('itemListElement', []):
            event = item.get('item', {})
            if event.get('@type') != 'Event':
                continue

            name = event.get('name', '').strip()
            if not name:
                continue

            start = event.get('startDate', '')
            if not start:
                continue

            try:
                datum = datetime.fromisoformat(start)
                datum = datum.replace(tzinfo=None)
            except ValueError:
                continue

            if not _im_monat(datum, jahr, monat):
                continue

            uhrzeit = datum.strftime('%H:%M Uhr') if datum.hour or datum.minute else 'ganztägig'

            location = event.get('location', {})
            ort = location.get('name', '')
            adresse = location.get('address', {})
            if isinstance(adresse, dict):
                strasse = adresse.get('streetAddress', '')
                if strasse and ort:
                    ort = f"{ort}, {strasse}"

            link = event.get('url', '')
            beschreibung = _html_zu_text(event.get('description', ''))[:300]

            # Kategorie aus URL ableiten
            kategorie = ''
            if link:
                path = link.split('regioactive.de/')[-1].split('/')[0] if 'regioactive.de/' in link else ''
                kat_map = {
                    'konzert': 'Konzert', 'party': 'Party', 'comedy': 'Comedy',
                    'show': 'Show', 'musical': 'Musical', 'vortrag': 'Vortrag',
                    'fasching': 'Karneval', 'freizeit': 'Freizeit',
                }
                kategorie = kat_map.get(path, '')

            termine.append(Termin(
                name=name[:150], datum=datum, uhrzeit=uhrzeit,
                ort=ort[:150], link=link, beschreibung=beschreibung,
                quelle='regioactive', kategorie=kategorie,
            ))

    return termine


# ---------------------------------------------------------------------------
# 2. Stadt Recklinghausen — Veranstaltungskalender (ASP-Tabelle)
# ---------------------------------------------------------------------------

def hole_stadt_re(jahr: int, monat: int) -> list[Termin]:
    """Holt Events vom offiziellen Veranstaltungskalender der Stadt RE."""
    try:
        response = requests.get(STADT_RE_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (stadt-re): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    termine = []

    # Tabelle mit Events finden
    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) < 2:
            continue

        # Erste Zelle: Link mit Titel
        link_tag = cells[0].find('a')
        if not link_tag:
            continue

        name = link_tag.get_text(strip=True)
        if not name:
            continue

        href = link_tag.get('href', '')
        if href and not href.startswith('http'):
            link = f"https://www.recklinghausen.de{href}"
        else:
            link = href

        # Zweite Zelle: Datum
        datum_text = cells[1].get_text(strip=True)
        if not datum_text:
            continue

        try:
            datum = datetime.strptime(datum_text, '%d.%m.%Y')
        except ValueError:
            continue

        if not _im_monat(datum, jahr, monat):
            continue

        termine.append(Termin(
            name=name[:150], datum=datum, uhrzeit='siehe Website',
            ort='Recklinghausen', link=link, beschreibung='',
            quelle='stadt-re', kategorie='',
        ))

    return termine


# ---------------------------------------------------------------------------
# 3. Altstadtschmiede — JSON-LD Events (MEC Plugin)
# ---------------------------------------------------------------------------

def hole_altstadtschmiede(jahr: int, monat: int) -> list[Termin]:
    """Holt Events von der Altstadtschmiede via JSON-LD."""
    try:
        response = requests.get(ALTSTADTSCHMIEDE_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (altstadtschmiede): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    termine = []

    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue

        if data.get('@type') != 'Event':
            continue

        name = data.get('name', '').strip()
        if not name:
            continue

        start = data.get('startDate', '')
        if not start:
            continue

        try:
            # Format: YYYY-MM-DD (ohne Uhrzeit im JSON-LD)
            datum = datetime.strptime(start[:10], '%Y-%m-%d')
        except ValueError:
            continue

        if not _im_monat(datum, jahr, monat):
            continue

        # Uhrzeit aus der Beschreibung extrahieren (z.B. "09.02. / 18 Uhr")
        beschreibung_html = data.get('description', '')
        beschreibung = _html_zu_text(beschreibung_html)
        uhrzeit_match = re.search(r'(\d{1,2}(?:[.:]\d{2})?)\s*Uhr', beschreibung)
        if uhrzeit_match:
            zeit = uhrzeit_match.group(1).replace('.', ':')
            if ':' not in zeit:
                zeit += ':00'
            uhrzeit = f"{zeit} Uhr"
            try:
                h, m = map(int, zeit.split(':'))
                datum = datum.replace(hour=h, minute=m)
            except ValueError:
                pass
        else:
            uhrzeit = 'siehe Website'

        link = data.get('offers', {}).get('url', '') or data.get('url', '') or ALTSTADTSCHMIEDE_URL

        termine.append(Termin(
            name=name[:150], datum=datum, uhrzeit=uhrzeit,
            ort='Altstadtschmiede', link=link, beschreibung=beschreibung[:200],
            quelle='altstadtschmiede', kategorie='Kultur',
        ))

    return termine


# ---------------------------------------------------------------------------
# 4. Vesterleben.de — HTML-Scraping mit Stadtfilter
# ---------------------------------------------------------------------------

def hole_vesterleben(jahr: int, monat: int) -> list[Termin]:
    """Holt Events von vesterleben.de, gefiltert auf Recklinghausen."""
    try:
        response = requests.get(VESTERLEBEN_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (vesterleben): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    termine = []

    for link_tag in soup.find_all('a', href=lambda h: h and '/termin-detail/' in h):
        h3 = link_tag.find('h3')
        if not h3:
            continue
        name = h3.get_text(strip=True)
        if not name:
            continue

        # Text-Zeilen des gesamten Link-Elements
        # Struktur: "Sonntag |  8.02.2026" / "Stadtname" / "| 15:00 Uhr" / Titel / Desc / Adresse / "PLZ | Stadt"
        text = link_tag.get_text('\n', strip=True)
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        datum = None
        uhrzeit = 'siehe Website'
        stadt = ''

        for line in lines:
            # Datum: "Sonntag |  8.02.2026"
            datum_match = re.search(r'(\d{1,2})\.(\d{2})\.(\d{4})', line)
            if datum_match and not datum:
                try:
                    datum = datetime(int(datum_match.group(3)), int(datum_match.group(2)),
                                    int(datum_match.group(1)))
                except ValueError:
                    continue

            # Uhrzeit: "| 15:00 Uhr" oder "15:00 Uhr"
            zeit_match = re.search(r'(\d{1,2}:\d{2})\s*Uhr', line)
            if zeit_match:
                uhrzeit = f"{zeit_match.group(1)} Uhr"

            # Stadt aus PLZ-Zeile: "45768 | Recklinghausen"
            plz_match = re.match(r'^\d{5}\s*\|\s*(.+)', line)
            if plz_match:
                stadt = plz_match.group(1).strip()
            # Oder Stadt als eigenständige Zeile (kurz, ohne Ziffern, ohne |)
            elif not datum_match and not zeit_match and not plz_match:
                if re.match(r'^[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\s-]{2,25}$', line) and '|' not in line:
                    if not stadt:
                        stadt = line

        if not datum:
            continue

        # Nur Recklinghausen-Events
        if stadt and 'recklinghausen' not in stadt.lower():
            continue

        if not _im_monat(datum, jahr, monat):
            continue

        if uhrzeit != 'siehe Website':
            try:
                h, m = map(int, uhrzeit.replace(' Uhr', '').split(':'))
                datum = datum.replace(hour=h, minute=m)
            except ValueError:
                pass

        href = link_tag.get('href', '')
        if href and not href.startswith('http'):
            href = f"https://vesterleben.de{href}"

        # Kategorie aus Icon
        kategorie = ''
        icon = link_tag.find('img', src=lambda s: s and 'icons-kalender' in s)
        if icon:
            src = icon.get('src', '')
            kat_match = re.search(r'icon-(\w+)\.svg', src)
            if kat_match:
                kat_map = {
                    'kultur': 'Kultur', 'musik': 'Musik', 'sport': 'Sport',
                    'familie': 'Familie', 'comedy': 'Comedy', 'party': 'Party',
                    'markt': 'Markt', 'messe': 'Messe',
                }
                kategorie = kat_map.get(kat_match.group(1), kat_match.group(1).title())

        termine.append(Termin(
            name=name[:150], datum=datum, uhrzeit=uhrzeit,
            ort=stadt or 'Recklinghausen', link=href,
            quelle='vesterleben', kategorie=kategorie,
        ))

    return termine


# ---------------------------------------------------------------------------
# 5. Sternwarte Recklinghausen — Text-Parsing
# ---------------------------------------------------------------------------

# Deutsche Monatsnamen für Parsing
_MONATE = {
    'januar': 1, 'februar': 2, 'märz': 3, 'april': 4,
    'mai': 5, 'juni': 6, 'juli': 7, 'august': 8,
    'september': 9, 'oktober': 10, 'november': 11, 'dezember': 12,
}


def hole_sternwarte(jahr: int, monat: int) -> list[Termin]:
    """Holt Events von der Volkssternwarte.

    Struktur: <p><u>Tag, DD. Monat, HH.MM Uhr, Ort</u><br><strong>Titel</strong><br>Beschreibung</p>
    """
    try:
        response = requests.get(STERNWARTE_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (sternwarte): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    termine = []

    monate_pattern = '|'.join(_MONATE.keys())
    datum_re = re.compile(
        rf'(\d{{1,2}})\.\s*({monate_pattern}),?\s*(\d{{1,2}})[.:](\d{{2}})\s*Uhr',
        re.IGNORECASE
    )

    for p in soup.find_all('p'):
        u_tag = p.find('u')
        if not u_tag:
            continue

        u_text = u_tag.get_text(strip=True)
        match = datum_re.search(u_text)
        if not match:
            continue

        tag = int(match.group(1))
        monat_name = match.group(2).lower()
        stunde = int(match.group(3))
        minute = int(match.group(4))

        event_monat = _MONATE.get(monat_name, 0)
        if event_monat != monat:
            continue

        try:
            datum = datetime(jahr, event_monat, tag, stunde, minute)
        except ValueError:
            continue

        # Ort: alles nach "Uhr, " im u-Tag
        ort_match = re.search(r'Uhr[,\s]+(.+)', u_text)
        ort = ort_match.group(1).strip().rstrip('.') if ort_match else 'Sternwarte'

        # Titel aus <strong>-Tag
        strong = p.find('strong')
        if not strong:
            continue
        name = strong.get_text(strip=True)
        if not name:
            continue

        # Beschreibung: restlicher Text nach dem strong-Tag
        full_text = p.get_text('\n', strip=True)
        beschreibung = ''
        if name in full_text:
            rest = full_text.split(name, 1)[-1].strip()
            # Erste Zeile nach Titel die nicht zum Header gehört
            rest_lines = [l.strip() for l in rest.split('\n') if l.strip()]
            if rest_lines:
                beschreibung = rest_lines[0][:200]

        termine.append(Termin(
            name=name[:150], datum=datum,
            uhrzeit=f"{stunde:02d}:{minute:02d} Uhr",
            ort=ort[:150], link=STERNWARTE_URL,
            beschreibung=beschreibung,
            quelle='sternwarte', kategorie='Astronomie',
        ))

    return termine


# ---------------------------------------------------------------------------
# 6. Kunsthalle Recklinghausen — h4-basiertes Parsing
# ---------------------------------------------------------------------------

def hole_kunsthalle(jahr: int, monat: int) -> list[Termin]:
    """Holt Events von der Kunsthalle Recklinghausen.

    Struktur im Text: DD.MM. / Titel / Day, HH:MM - / HH:MM Uhr / Beschreibung
    """
    try:
        response = requests.get(KUNSTHALLE_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (kunsthalle): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    termine = []

    # Gesamten sichtbaren Text zeilenweise durchgehen
    text = soup.get_text('\n')
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    i = 0
    while i < len(lines):
        # Datum-Zeile finden: "DD.MM."
        datum_match = re.match(r'^(\d{1,2})\.(\d{2})\.$', lines[i])
        if not datum_match:
            i += 1
            continue

        tag = int(datum_match.group(1))
        event_monat = int(datum_match.group(2))

        if event_monat != monat:
            i += 1
            continue

        try:
            datum = datetime(jahr, event_monat, tag)
        except ValueError:
            i += 1
            continue

        # Nächste Zeile: Titel
        i += 1
        if i >= len(lines):
            break
        name = lines[i]

        # Folgezeilen nach Uhrzeit durchsuchen
        uhrzeit = 'siehe Website'
        beschreibung = ''
        i += 1
        while i < len(lines) and not re.match(r'^\d{1,2}\.\d{2}\.$', lines[i]):
            # Uhrzeit: "Sunday, 12:00 -" oder "12:00 - 13:00 Uhr"
            zeit_match = re.search(r'(\d{1,2}:\d{2})\s*-', lines[i])
            if zeit_match and uhrzeit == 'siehe Website':
                start_zeit = zeit_match.group(1)
                # Endzeit könnte auf gleicher oder nächster Zeile sein
                end_match = re.search(r'-\s*(\d{1,2}:\d{2})\s*Uhr', lines[i])
                if end_match:
                    uhrzeit = f"{start_zeit}–{end_match.group(1)} Uhr"
                elif i + 1 < len(lines):
                    end_match2 = re.search(r'(\d{1,2}:\d{2})\s*Uhr', lines[i + 1])
                    if end_match2:
                        uhrzeit = f"{start_zeit}–{end_match2.group(1)} Uhr"
                        i += 1
                    else:
                        uhrzeit = f"{start_zeit} Uhr"
                else:
                    uhrzeit = f"{start_zeit} Uhr"

                try:
                    h, m = map(int, start_zeit.split(':'))
                    datum = datum.replace(hour=h, minute=m)
                except ValueError:
                    pass
            elif not beschreibung and uhrzeit != 'siehe Website':
                # Erste Zeile nach Uhrzeit = Beschreibung
                if not re.match(r'^(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)', lines[i]):
                    beschreibung = lines[i]
            i += 1

        termine.append(Termin(
            name=name[:150], datum=datum, uhrzeit=uhrzeit,
            ort='Kunsthalle Recklinghausen', link=KUNSTHALLE_URL,
            beschreibung=beschreibung[:200],
            quelle='kunsthalle', kategorie='Kunst',
        ))

    return termine


# ---------------------------------------------------------------------------
# 7. Stadtbibliothek Recklinghausen — ASP-Datenbank (GKD)
# ---------------------------------------------------------------------------

def _selfdb_feld(entry, klasse: str) -> str:
    """Extrahiert den Wert eines selfdb-Felds aus einem Reporteintrag."""
    feld = entry.find('div', class_=klasse)
    if not feld:
        return ''
    wert = feld.find('div', class_='selfdb_columnvalue')
    return wert.get_text(strip=True) if wert else ''


def hole_stadtbibliothek(jahr: int, monat: int) -> list[Termin]:
    """Holt Events der Stadtbibliothek Recklinghausen.

    GKD-selfdb-System: div.selfdb_reportentry mit Feldern
    selfdb_fieldTitel, selfdb_Veranstaltungsdatum, selfdb_fieldZeiten,
    selfdb_fieldVeranstaltungssttte, selfdb_weiteredetails.
    """
    params = {
        'db': '79',
        'form': 'report',
        'fieldStadt': 'Recklinghausen',
        'fieldgkdveranstbeginn': f'01.{monat:02d}.{jahr}',
        'fieldStichworte': 'stadtbuecherei',
    }
    try:
        response = requests.get(STADTBIBLIOTHEK_URL, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (stadtbibliothek): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    termine = []

    for entry in soup.find_all('div', class_='selfdb_reportentry'):
        name = _selfdb_feld(entry, 'selfdb_fieldTitel')
        if not name:
            continue

        datum_text = _selfdb_feld(entry, 'selfdb_Veranstaltungsdatum')
        if not datum_text:
            continue

        try:
            datum = datetime.strptime(datum_text, '%d.%m.%Y')
        except ValueError:
            continue

        if not _im_monat(datum, jahr, monat):
            continue

        # Uhrzeit: "16:00" oder "11 Uhr" oder "18:30 - 20:30 Uhr"
        uhrzeit = 'siehe Website'
        zeit_text = _selfdb_feld(entry, 'selfdb_fieldZeiten')
        if zeit_text:
            zeit_match = re.search(r'(\d{1,2})[.:](\d{2})', zeit_text)
            if zeit_match:
                h, m = int(zeit_match.group(1)), int(zeit_match.group(2))
                uhrzeit = f"{h:02d}:{m:02d} Uhr"
                datum = datum.replace(hour=h, minute=m)
            else:
                # "11 Uhr" ohne Minuten
                h_match = re.search(r'(\d{1,2})\s*Uhr', zeit_text)
                if h_match:
                    h = int(h_match.group(1))
                    uhrzeit = f"{h:02d}:00 Uhr"
                    datum = datum.replace(hour=h)

        ort = _selfdb_feld(entry, 'selfdb_fieldVeranstaltungssttte') or 'Stadtbibliothek'

        link = ''
        details = entry.find('div', class_='selfdb_weiteredetails')
        if details:
            link_tag = details.find('a', href=True)
            if link_tag:
                href = link_tag['href']
                link = f"https://www.recklinghausen.de{href}" if not href.startswith('http') else href

        termine.append(Termin(
            name=name[:150], datum=datum, uhrzeit=uhrzeit,
            ort=ort[:150], link=link,
            quelle='stadtbibliothek', kategorie='Bibliothek',
        ))

    return termine


# ---------------------------------------------------------------------------
# 8 + 9. NLGR & Literaturtage — The Events Calendar (JSON-LD)
# ---------------------------------------------------------------------------

def _hole_events_calendar(url: str, quelle: str, kategorie: str,
                          jahr: int, monat: int) -> list[Termin]:
    """Holt Events von Seiten mit The Events Calendar Plugin via JSON-LD."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen ({quelle}): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    termine = []

    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue

        events = []
        if isinstance(data, list):
            events = data
        elif isinstance(data, dict):
            if data.get('@type') == 'Event':
                events = [data]
            elif '@graph' in data:
                events = [e for e in data['@graph'] if e.get('@type') == 'Event']

        for event in events:
            if event.get('@type') != 'Event':
                continue

            name = event.get('name', '').strip()
            if not name:
                continue

            start = event.get('startDate', '')
            if not start:
                continue

            try:
                datum = datetime.fromisoformat(start)
                datum = datum.replace(tzinfo=None)
            except ValueError:
                try:
                    datum = datetime.strptime(start[:10], '%Y-%m-%d')
                except ValueError:
                    continue

            if not _im_monat(datum, jahr, monat):
                continue

            uhrzeit = datum.strftime('%H:%M Uhr') if datum.hour or datum.minute else 'siehe Website'

            location = event.get('location', {})
            ort = ''
            if isinstance(location, dict):
                ort = location.get('name', '')
                address = location.get('address', {})
                if isinstance(address, dict):
                    street = address.get('streetAddress', '')
                    if street and ort:
                        ort = f"{ort}, {street}"
                elif isinstance(address, str):
                    if address and ort:
                        ort = f"{ort}, {address}"

            link = event.get('url', '') or url
            beschreibung = _html_zu_text(event.get('description', ''))[:300]

            termine.append(Termin(
                name=name[:150], datum=datum, uhrzeit=uhrzeit,
                ort=ort[:150] or 'Recklinghausen', link=link,
                beschreibung=beschreibung,
                quelle=quelle, kategorie=kategorie,
            ))

    return termine


def hole_nlgr(jahr: int, monat: int) -> list[Termin]:
    """Holt Events der Neuen Literarischen Gesellschaft Recklinghausen."""
    return _hole_events_calendar(NLGR_URL, 'nlgr', 'Literatur', jahr, monat)


def hole_literaturtage(jahr: int, monat: int) -> list[Termin]:
    """Holt Events der Literaturtage Recklinghausen."""
    return _hole_events_calendar(LITERATURTAGE_URL, 'literaturtage', 'Literatur', jahr, monat)


# ---------------------------------------------------------------------------
# 11. Evangelische Akademie Recklinghausen (ahademie.com) — TYPO3
# ---------------------------------------------------------------------------

def hole_akademie(jahr: int, monat: int) -> list[Termin]:
    """Holt Events der Evangelischen Akademie Recklinghausen.

    TYPO3-basiert: div.col-md-4 mit a.box-hov (Link+Datum in p.eventdate-big),
    p.subheadline (Titel) und optionalem <p> (Referent).
    Alle Events auf einer Seite, keine Paginierung.
    """
    try:
        response = requests.get(AKADEMIE_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (akademie): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    termine = []

    for card in soup.find_all('div', class_='col-md-4'):
        a_tag = card.find('a', class_='box-hov')
        if not a_tag:
            continue

        datum_p = a_tag.find('p', class_='eventdate-big')
        if not datum_p:
            continue

        datum_text = datum_p.get_text(strip=True)
        try:
            datum = datetime.strptime(datum_text, '%d.%m.%Y')
        except ValueError:
            continue

        if not _im_monat(datum, jahr, monat):
            continue

        titel_p = card.find('p', class_='subheadline')
        name = titel_p.get_text(strip=True) if titel_p else ''
        if not name:
            continue

        # Referent/Beschreibung: nächstes <p> nach dem Titel
        beschreibung = ''
        if titel_p:
            next_p = titel_p.find_next_sibling('p')
            if next_p:
                beschreibung = next_p.get_text(strip=True)

        href = a_tag.get('href', '')
        link = f"https://www.ahademie.com{href}" if href and not href.startswith('http') else href

        termine.append(Termin(
            name=name[:150], datum=datum, uhrzeit='siehe Website',
            ort='Ev. Akademie Recklinghausen', link=link,
            beschreibung=beschreibung[:200],
            quelle='akademie', kategorie='Bildung',
        ))

    return termine


# ---------------------------------------------------------------------------
# 12. Institut für Stadtgeschichte — Halbjahres-PDF
# ---------------------------------------------------------------------------

_WOCHENTAGE = r'Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag'


def _parse_stadtarchiv_text(text: str, jahr: int, monat: int, pdf_url: str) -> list[Termin]:
    """Parst Events aus dem Stadtarchiv-PDF-Text."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    termine = []
    gesehen: set[str] = set()

    monate_pattern = '|'.join(_MONATE.keys())

    # "Donnerstag, 18. Juni 2026, 18 Uhr" / "Sonntag, 17. Mai 2026, 10 und 15 Uhr"
    re_monatname = re.compile(
        rf'({_WOCHENTAGE}),\s*(\d{{1,2}})\.\s*({monate_pattern})\s+(\d{{4}}),\s*(\d{{1,2}})\s*(?:und\s*\d+\s*)?Uhr',
        re.IGNORECASE,
    )
    # "Mittwoch, 14.01.2026, 18 Uhr"
    re_numerisch = re.compile(
        rf'({_WOCHENTAGE}),\s*(\d{{1,2}})\.(\d{{2}})\.(\d{{4}}),\s*(\d{{1,2}})\s*Uhr',
    )
    # "13. Mai bis 17. Juli 2026" (Ausstellungs-Zeitraum)
    re_zeitraum = re.compile(
        rf'(\d{{1,2}})\.\s*({monate_pattern})\s+bis\s+\d{{1,2}}\.\s*(?:{monate_pattern})\s+(\d{{4}})',
        re.IGNORECASE,
    )

    def _ist_datumzeile(line: str) -> bool:
        return bool(re_monatname.search(line) or re_numerisch.search(line) or re_zeitraum.search(line))

    i = 0
    while i < len(lines):
        line = lines[i]
        datum = None
        uhrzeit = 'siehe Website'

        m = re_monatname.search(line)
        if m:
            tag, monat_name, event_jahr, stunde = int(m.group(2)), m.group(3).lower(), int(m.group(4)), int(m.group(5))
            event_monat = _MONATE.get(monat_name, 0)
            try:
                datum = datetime(event_jahr, event_monat, tag, stunde, 0)
                uhrzeit = f"{stunde:02d}:00 Uhr"
            except ValueError:
                pass

        if not datum:
            m = re_numerisch.search(line)
            if m:
                tag, event_monat, event_jahr, stunde = int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
                try:
                    datum = datetime(event_jahr, event_monat, tag, stunde, 0)
                    uhrzeit = f"{stunde:02d}:00 Uhr"
                except ValueError:
                    pass

        if not datum:
            m = re_zeitraum.search(line)
            if m:
                tag, monat_name, event_jahr = int(m.group(1)), m.group(2).lower(), int(m.group(3))
                event_monat = _MONATE.get(monat_name, 0)
                try:
                    datum = datetime(event_jahr, event_monat, tag)
                except ValueError:
                    pass

        if not datum or not _im_monat(datum, jahr, monat):
            i += 1
            continue

        # Titel: nächste 1–3 kurze Zeilen nach dem Datum
        # PDF-Spaltensatz: Fließtext ≥50 Zeichen, Überschriften kürzer
        title_parts = []
        j = i + 1
        while j < len(lines) and len(title_parts) < 3:
            next_line = lines[j]
            if _ist_datumzeile(next_line):
                break
            if next_line.startswith(('Institut für', 'Exkursion/', 'Sonderausstellung', 'Start am')):
                break
            if len(next_line) >= 50 and len(title_parts) > 0:
                break
            title_parts.append(next_line)
            j += 1

        name = ' '.join(title_parts).strip()
        # PDF-Zeilenumbrüche in Wörtern reparieren ("Land- gemeinde" → "Landgemeinde")
        # Aber nicht bei "Stadt- und", "Bus- und" etc. (echte Bindestriche vor und/oder/bzw)
        name = re.sub(r'(\w)- (?!und |oder |bzw )(\w)', r'\1\2', name)
        if not name:
            i += 1
            continue

        dedup_key = f"{name}|{datum.strftime('%Y-%m-%d')}"
        if dedup_key in gesehen:
            i += 1
            continue
        gesehen.add(dedup_key)

        termine.append(Termin(
            name=name[:150], datum=datum, uhrzeit=uhrzeit,
            ort='Institut für Stadtgeschichte', link=pdf_url,
            quelle='stadtarchiv', kategorie='Geschichte',
        ))
        i = j
        continue

    return termine


def hole_stadtarchiv(jahr: int, monat: int) -> list[Termin]:
    """Holt Events vom Institut für Stadtgeschichte aus dem Halbjahres-PDF.

    Probiert beide Halbjahres-PDFs (1. und 2. Halbjahr) für das gegebene Jahr.
    PyMuPDF extrahiert den Text, Regex parst die Datumsformate.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("  PyMuPDF nicht installiert (pip install pymupdf)")
        return []

    termine = []
    urls = [
        f"{STADTARCHIV_PDF_BASE}/Programm_1-Halbjahr_{jahr}_Stadtarchiv.pdf",
        f"{STADTARCHIV_PDF_BASE}/Programm_2-Halbjahr_{jahr}_Stadtarchiv.pdf",
    ]

    for pdf_url in urls:
        try:
            response = requests.get(pdf_url, headers=HEADERS, timeout=30)
            if response.status_code != 200:
                continue
        except requests.RequestException:
            continue

        doc = fitz.open(stream=response.content, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()

        termine.extend(_parse_stadtarchiv_text(text, jahr, monat, pdf_url))

    return termine


# ---------------------------------------------------------------------------
# 10. VHS Recklinghausen — KuferWeb (h4.kw-ue-title)
# ---------------------------------------------------------------------------

_VHS_KATEGORIEN = [
    'politik-und-gesellschaft',
    'kultur-gestalten',
    'gesundheit',
    'sprachen',
    'digitales-und-beruf',
    'grundbildung',
    'junge-vhs',
]


def _parse_vhs_seite(soup: BeautifulSoup, jahr: int, monat: int,
                     gesehen: set[str]) -> list[Termin]:
    """Parst VHS-Kurseinträge aus einer BeautifulSoup-Seite."""
    termine = []

    for h4 in soup.find_all('h4', class_='kw-ue-title'):
        a_tag = h4.find('a')
        if not a_tag:
            continue

        b_tag = a_tag.find('b')
        name = b_tag.get_text(strip=True) if b_tag else a_tag.get_text(strip=True)
        if not name:
            continue

        link = a_tag.get('href', '')

        # Metadaten aus den row-Divs des Eltern-Containers
        parent = h4.parent
        beginn = ''
        ort = ''
        for row in parent.find_all('div', class_='row'):
            cols = row.find_all('div')
            if len(cols) < 2:
                continue
            label = cols[0].get_text(strip=True)
            value = cols[1].get_text(strip=True)
            if label == 'Beginn':
                beginn = value
            elif label == 'Kursort':
                ort = value

        if not beginn:
            continue

        # "Di., 10.02.2026, 19:00 - 20:30 Uhr"
        datum_match = re.search(r'(\d{1,2})\.(\d{2})\.(\d{4})', beginn)
        if not datum_match:
            continue

        try:
            datum = datetime(int(datum_match.group(3)), int(datum_match.group(2)),
                             int(datum_match.group(1)))
        except ValueError:
            continue

        if not _im_monat(datum, jahr, monat):
            continue

        # Duplikate über Kategorien hinweg vermeiden (gleicher Name + Tag)
        dedup_key = f"{name}|{datum.strftime('%Y-%m-%d')}"
        if dedup_key in gesehen:
            continue
        gesehen.add(dedup_key)

        # Uhrzeit: "19:00 - 20:30 Uhr"
        uhrzeit = 'siehe Website'
        zeit_match = re.search(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*Uhr', beginn)
        if zeit_match:
            uhrzeit = f"{zeit_match.group(1)}–{zeit_match.group(2)} Uhr"
            try:
                h, m = map(int, zeit_match.group(1).split(':'))
                datum = datum.replace(hour=h, minute=m)
            except ValueError:
                pass

        termine.append(Termin(
            name=name[:150], datum=datum, uhrzeit=uhrzeit,
            ort=ort[:150] or 'VHS Recklinghausen', link=link,
            quelle='vhs', kategorie='Bildung',
        ))

    return termine


def hole_vhs(jahr: int, monat: int) -> list[Termin]:
    """Holt Events der VHS Recklinghausen.

    Iteriert über alle 7 Kategorie-Seiten mit Paginierung.
    KuferWeb zeigt max. 50 Einträge pro Seite; browse/forward-Links für Folgeseiten.
    Schleifen-Erkennung über bereits besuchte URLs.
    Duplikate (gleicher Kurs in mehreren Kategorien) werden intern entfernt.
    """
    termine = []
    gesehen: set[str] = set()

    for kategorie in _VHS_KATEGORIEN:
        url = f"{VHS_BASE_URL}/{kategorie}/"
        besuchte_urls: set[str] = set()

        while url and url not in besuchte_urls and len(besuchte_urls) < 5:
            besuchte_urls.add(url)
            try:
                response = requests.get(url, headers=HEADERS, timeout=30)
                response.raise_for_status()
            except requests.RequestException:
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            termine.extend(_parse_vhs_seite(soup, jahr, monat, gesehen))

            next_link = soup.find('a', href=lambda h: h and 'browse/forward' in h)
            url = next_link['href'] if next_link else None

    return termine
