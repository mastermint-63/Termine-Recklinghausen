"""Scraper für Veranstaltungen in Recklinghausen aus mehreren Quellen."""

import json
import re
import requests
from dataclasses import dataclass
from datetime import datetime, timedelta
from calendar import monthrange
from html import unescape
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept-Language': 'de-DE, de;q=0.9',
}

# URLs
REGIOACTIVE_URL = "https://www.regioactive.de/events/22868/recklinghausen/veranstaltungen-party-konzerte"
STADT_RE_URL = "https://www.recklinghausen.de/inhalte/startseite/_veranstaltungskalender/"
ALTSTADTSCHMIEDE_URL = "https://www.altstadtschmiede.de/events/"
VESTERLEBEN_URL = "https://vesterleben.de/termine-alle"
STERNWARTE_URL = "https://sternwarte-recklinghausen.de/programm/veranstaltungskalender/"
KUNSTHALLE_URL = "https://kunsthalle-recklinghausen.de/programm/kalender"
STADTBIBLIOTHEK_URL = "https://www.recklinghausen.de/inhalte/startseite/familie_bildung/stadtbibliothek/Veranstaltungen/index.asp"
NLGR_URL = "https://nlgr.de/veranstaltungen/"
LITERATURTAGE_URL = "https://literaturtage-recklinghausen.de/veranstaltungen/"
VHS_BASE_URL = "https://www.vhs-recklinghausen.de"
AKADEMIE_URL = "https://www.ahademie.com/veranstaltungen/"
GESCHICHTE_RE_URL = "https://geschichte-recklinghausen.de/veranstaltung/"
GASTKIRCHE_URL = "https://www.gastkirche.de/index.php/termine/eventsnachwoche"
RUHRFESTSPIELE_URL = "https://www.ruhrfestspiele.de/programm"
BACKYARD_URL = "https://backyard-club.de/events"
CINEWORLD_API = "https://api.cineamo.com/showings"
CINEWORLD_CINEMA_ID = 877
CINEWORLD_URL = "https://www.cineworld-recklinghausen.de/de/programm"
STADTARCHIV_PDF_BASE = "https://www.recklinghausen.de/Inhalte/Startseite/Ruhrfestspiele_Kultur/Dokumente"
NEUE_PHILHARMONIE_URL = "https://www.neue-philharmonie-westfalen.de/termine"
IKONEN_MUSEUM_URL = "https://ikonen-museum.com/veranstaltungen/termine"
DEBUT_UM_11_URL = "https://debut-um-11.de/konzerte-102/"
ADFC_API_URL = "https://api-touren-termine.adfc.de/api/eventItems/search"
ADFC_UNIT_TERMINE = "164420"
ADFC_UNIT_RADTOUREN = "16442006"
ADFC_RE_URL = "https://recklinghausen.adfc.de/"
RE_LEUCHTET_API = "https://re-leuchtet.de/wp-json/tribe/events/v1/events"
RE_LEUCHTET_URL = "https://re-leuchtet.de/programm"
ZU_GAST_URL = "https://www.zu-gast-in-re.de/programm"
ATELIERHAUS_ICS = "https://atelierhaus-recklinghausen.de/?plugin=all-in-one-event-calendar&controller=ai1ec_exporter_controller&action=export_events"
ATELIERHAUS_URL = "https://atelierhaus-recklinghausen.de/kalendar/"
JOSEFEICH_URL = "https://josefeich.de/events/"
RECKLINGHAEUSER_URL = "https://www.der-recklinghaeuser.de/"
SUBERGS_URL = "https://www.subergs.de/events/"
SENIORENBEIRAT_URL = "https://seniorenbeirat-recklinghausen.com/veranstaltungen/liste/"
ZECHE_KLAERCHEN_URL = "https://zeche-klaerchen.de/index.php/aktuelles"


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
    kandidaten = []

    # Übersicht: Name, Datum und Detaillink sammeln
    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) < 2:
            continue

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

        datum_text = cells[1].get_text(strip=True)
        if not datum_text:
            continue

        try:
            datum = datetime.strptime(datum_text, '%d.%m.%Y')
        except ValueError:
            continue

        if not _im_monat(datum, jahr, monat):
            continue

        kandidaten.append((name, datum, link))

    # Detailseiten abrufen: Uhrzeit, Beschreibung, Veranstaltungsstätte
    termine = []
    for name, datum, link in kandidaten:
        uhrzeit = 'siehe Website'
        beschreibung = ''
        ort = 'Recklinghausen'

        try:
            detail = requests.get(link, headers=HEADERS, timeout=15)
            detail.raise_for_status()
            ds = BeautifulSoup(detail.text, 'html.parser')

            def _sf(cls):
                d = ds.find(class_=cls)
                if d:
                    val = d.find(class_='selfdb_columnvalue')
                    if val:
                        return val.get_text(separator=' ', strip=True)
                return ''

            if z := _sf('selfdb_fieldZeiten'):
                uhrzeit = z
            if i := _sf('selfdb_fieldInhalt'):
                if i.startswith(name):
                    i = i[len(name):].strip()
                beschreibung = i[:800]
            if s := _sf('selfdb_fieldVeranstaltungssttte'):
                ort = s

        except requests.RequestException:
            pass

        termine.append(Termin(
            name=name[:150], datum=datum, uhrzeit=uhrzeit,
            ort=ort, link=link, beschreibung=beschreibung,
            quelle='stadt-re', kategorie='',
        ))

    return termine


# ---------------------------------------------------------------------------
# 3. Altstadtschmiede — JSON-LD Events (MEC Plugin)
# ---------------------------------------------------------------------------

def _hole_altstadtschmiede_beschreibung(url: str) -> str:
    """Holt die Beschreibung von einer Altstadtschmiede-Detailseite."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except requests.RequestException:
        return ''
    soup = BeautifulSoup(r.text, 'html.parser')
    desc_div = soup.select_one('.mec-single-event-description')
    if not desc_div:
        return ''
    # Erste Zeile = Datum/Preis, Ticket-Buttons überspringen → nur <p>-Absätze ab dem 2. nehmen
    absaetze = desc_div.find_all('p')
    texte = []
    for p in absaetze:
        text = p.get_text(strip=True)
        if not text:
            continue
        # Erste Zeile enthält Datum/Uhrzeit/Preis (z.B. "25.03. / 19 Uhr / VVK ...")
        if re.match(r'\d{1,2}\.\d{2}\.?\s*/\s*\d', text):
            continue
        texte.append(text)
    return '\n'.join(texte)


def hole_altstadtschmiede(jahr: int, monat: int) -> list[Termin]:
    """Holt Events von der Altstadtschmiede via JSON-LD + Beschreibungen von Detailseiten."""
    try:
        response = requests.get(ALTSTADTSCHMIEDE_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (altstadtschmiede): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    termine = []

    for script in soup.find_all('script', type='application/ld+json'):
        raw = script.string or ''
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            # Fallback: unescapte HTML-Anführungszeichen in der Beschreibung → Regex
            if '"@type": "Event"' not in raw:
                continue
            names = re.findall(r'"name":\s*"([^"]+)"', raw)
            date_m = re.search(r'"startDate":\s*"(\d{4}-\d{2}-\d{2})', raw)
            url_m = re.search(r'"url":\s*"(https://[^"]+)"', raw)
            if not names or not date_m:
                continue
            data = {
                '@type': 'Event',
                'name': names[-1],  # letztes name-Feld = Event-Titel
                'startDate': date_m.group(1),
                'url': url_m.group(1) if url_m else ALTSTADTSCHMIEDE_URL,
                'description': raw,  # Rohdaten für Uhrzeit-Regex
            }

        if data.get('@type') != 'Event':
            continue

        name = unescape(data.get('name', '').strip())
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

        # Uhrzeit aus der JSON-LD-Beschreibung extrahieren (z.B. "09.02. / 18 Uhr")
        beschreibung_html = data.get('description', '')
        beschreibung_kurz = _html_zu_text(beschreibung_html)
        uhrzeit_match = re.search(r'(\d{1,2}(?:[.:]\d{2})?)\s*Uhr', beschreibung_kurz)
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

        # Beschreibung von der Detailseite holen
        beschreibung = _hole_altstadtschmiede_beschreibung(link)

        termine.append(Termin(
            name=name[:150], datum=datum, uhrzeit=uhrzeit,
            ort='Altstadtschmiede', link=link, beschreibung=beschreibung,
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
                if not re.match(r'^(Sonntag|Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag)', lines[i]):
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


# ---------------------------------------------------------------------------
# 13. Verein für Orts- und Heimatkunde (geschichte-recklinghausen.de)
# ---------------------------------------------------------------------------

def hole_geschichte_re(jahr: int, monat: int) -> list[Termin]:
    """Holt Events vom Verein für Orts- und Heimatkunde Recklinghausen.

    WordPress mit The Events Calendar + ECT (Events Calendar Templates).
    Timeline-Ansicht: div.ect-timeline-post mit content-Attribut für Datum,
    h2>a für Titel/Link, meta[itemprop=name] für Ort, div.ect-event-content
    für Beschreibung.
    """
    try:
        response = requests.get(GESCHICHTE_RE_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (geschichte-re): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    termine = []

    for post in soup.find_all('div', class_='ect-timeline-post'):
        # Datum aus content-Attribut: "2026-03-25CET6:00" oder "2026-04-11CEST9:00"
        date_area = post.find('div', class_='ect-date-area')
        if not date_area:
            continue

        content = date_area.get('content', '')
        if not content:
            continue

        # "2026-03-25CET6:00" → Datum + Uhrzeit
        # ECT-Plugin-Bug: speichert Stunde % 12 (ohne AM/PM)
        # 18:00→6:00, 14:00→2:00, 9:00→9:00
        date_match = re.match(r'(\d{4}-\d{2}-\d{2})(?:CES?T)(\d{1,2}):(\d{2})', content)
        if not date_match:
            continue

        try:
            datum = datetime.strptime(date_match.group(1), '%Y-%m-%d')
            stunde, minute = int(date_match.group(2)), int(date_match.group(3))
            # Stunde 1–8 → Nachmittag/Abend (+12), 9–11 → Vormittag
            if 1 <= stunde <= 8:
                stunde += 12
            datum = datum.replace(hour=stunde, minute=minute)
        except ValueError:
            continue

        if not _im_monat(datum, jahr, monat):
            continue

        uhrzeit = f"{stunde:02d}:{minute:02d} Uhr" if stunde or minute else 'siehe Website'

        # Titel + Link aus h2 > a
        h2 = post.find('h2')
        if not h2:
            continue
        a_tag = h2.find('a')
        name = a_tag.get_text(strip=True) if a_tag else h2.get_text(strip=True)
        if not name:
            continue
        link = a_tag.get('href', '') if a_tag else GESCHICHTE_RE_URL

        # Ort aus venue meta-Tag
        venue_block = post.find('div', class_='timeline-view-venue')
        ort = ''
        if venue_block:
            venue_meta = venue_block.find('meta', itemprop='name')
            if venue_meta:
                ort = venue_meta.get('content', '')

        # Beschreibung aus ect-event-content
        desc_div = post.find('div', class_='ect-event-content')
        beschreibung = ''
        if desc_div:
            beschreibung = desc_div.get_text(strip=True)
            # "Finde mehr heraus »" entfernen
            beschreibung = re.sub(r'\s*\[…\].*$', '', beschreibung)

        termine.append(Termin(
            name=name[:150], datum=datum, uhrzeit=uhrzeit,
            ort=ort[:150] or 'Recklinghausen', link=link,
            beschreibung=beschreibung[:200],
            quelle='geschichte-re', kategorie='Geschichte',
        ))

    return termine


# ---------------------------------------------------------------------------
# 14. Gastkirche Recklinghausen — JEvents Wochenansicht
# ---------------------------------------------------------------------------

# Kategorie-IDs: 68 = Gruppentermine, 70 = Veranstaltungen
_GASTKIRCHE_KATEGORIEN = {'68': 'Gruppentermine', '70': 'Veranstaltungen'}


def _montage_fuer_monat(jahr: int, monat: int) -> list[datetime]:
    """Gibt alle Montage zurück, deren Woche Tage im Zielmonat enthält."""
    erster = datetime(jahr, monat, 1)
    # Montag der Woche, die den 1. enthält
    montag = erster - timedelta(days=erster.weekday())
    letzter_tag = monthrange(jahr, monat)[1]
    letzter = datetime(jahr, monat, letzter_tag)

    montage = []
    while montag <= letzter:
        montage.append(montag)
        montag += timedelta(days=7)
    return montage


def _parse_gastkirche_woche(soup: BeautifulSoup, jahr: int, monat: int,
                            kategorie_name: str) -> list[Termin]:
    """Parst Events aus einer JEvents-Wochenseite."""
    termine = []

    # Jahr aus Header: "09. Februar 2026 - 15. Februar 2026"
    header = soup.find('td', class_='cal_td_daysnames')
    header_jahr = jahr
    if header:
        jahr_match = re.search(r'(\d{4})', header.get_text())
        if jahr_match:
            header_jahr = int(jahr_match.group(1))

    table = soup.find('table', class_='ev_table')
    if not table:
        return []

    for row in table.find_all('tr'):
        left = row.find('td', class_=lambda c: c and (
            'ev_td_left' in c or 'ev_td_today' in c))
        right = row.find('td', class_='ev_td_right')
        if not left or not right:
            continue
        if 'Keine Events' in right.get_text():
            continue

        # Tag + Monat aus left: "Montag09. Februar" oder "Freitag13. Februar"
        left_text = left.get_text(strip=True)
        datum_match = re.search(r'(\d{1,2})\.\s*(\w+)', left_text)
        if not datum_match:
            continue

        tag = int(datum_match.group(1))
        monat_name = datum_match.group(2).lower()
        event_monat = _MONATE.get(monat_name, 0)
        if not event_monat:
            continue

        if event_monat != monat or header_jahr != jahr:
            continue

        # Events aus li.ev_td_li
        for li in right.find_all('li', class_='ev_td_li'):
            a_tag = li.find('a', class_='ev_link_row')
            if not a_tag:
                continue

            name = a_tag.get('title', '') or a_tag.get_text(strip=True)
            if not name:
                continue

            href = a_tag.get('href', '')
            link = f"https://www.gastkirche.de{href}" if href and not href.startswith('http') else href

            # Uhrzeit: Text vor dem Link, z.B. "15:00 Uhr"
            li_text = li.get_text(strip=True)
            uhrzeit = 'siehe Website'
            zeit_match = re.search(r'(\d{1,2}:\d{2})\s*Uhr', li_text)
            stunde, minute = 0, 0
            if zeit_match:
                uhrzeit = f"{zeit_match.group(1)} Uhr"
                try:
                    h, m = map(int, zeit_match.group(1).split(':'))
                    stunde, minute = h, m
                except ValueError:
                    pass

            try:
                datum = datetime(header_jahr, event_monat, tag, stunde, minute)
            except ValueError:
                continue

            # Ort: "Ort: ..." im Text
            ort = ''
            ort_match = re.search(r'Ort:\s*(.+?)$', li_text)
            if ort_match:
                ort = ort_match.group(1).strip()

            termine.append(Termin(
                name=name[:150], datum=datum, uhrzeit=uhrzeit,
                ort=ort[:150] or 'Gastkirche', link=link,
                quelle='gastkirche', kategorie=kategorie_name,
            ))

    return termine


def hole_gastkirche(jahr: int, monat: int) -> list[Termin]:
    """Holt Events der Gastkirche Recklinghausen (Gruppentermine + Veranstaltungen).

    JEvents (Joomla): Wochenansicht mit Kategoriefilter.
    Iteriert über alle Wochen des Monats für Kategorien 68 und 70.
    """
    termine = []
    montage = _montage_fuer_monat(jahr, monat)

    for kat_id, kat_name in _GASTKIRCHE_KATEGORIEN.items():
        for montag in montage:
            url = f"{GASTKIRCHE_URL}/{montag.strftime('%Y/%m/%d')}/{kat_id}"
            try:
                response = requests.get(url, headers=HEADERS, timeout=30)
                response.raise_for_status()
            except requests.RequestException:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            termine.extend(_parse_gastkirche_woche(soup, jahr, monat, kat_name))

    return termine


# ---------------------------------------------------------------------------
# 15. Ruhrfestspiele Recklinghausen — Programm-Seite + Detailseiten
# ---------------------------------------------------------------------------

def hole_ruhrfestspiele(jahr: int, monat: int) -> list[Termin]:
    """Holt Events der Ruhrfestspiele Recklinghausen.

    Zweistufig: Hauptseite /programm → Produktions-Links sammeln,
    dann jede Detailseite → article.production-schedule-item parsen.
    ID-Attribut = YYYY-MM-DD, time-Element für Uhrzeit, Spielstätten-Link für Ort.
    Festival läuft ca. Mai–Juni; außerhalb 0 Termine.
    """
    # Hauptseite: alle Produktions-Links sammeln
    try:
        response = requests.get(RUHRFESTSPIELE_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (ruhrfestspiele): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    produktion_urls = []
    for a in soup.find_all('a', href=lambda h: h and f'/programm/{jahr}/' in h):
        href = a['href']
        if href not in produktion_urls:
            produktion_urls.append(href)

    if not produktion_urls:
        return []

    termine = []
    ziel_prefix = f"{jahr}-{monat:02d}-"

    for prod_url in produktion_urls:
        try:
            response = requests.get(prod_url, headers=HEADERS, timeout=30)
            response.raise_for_status()
        except requests.RequestException:
            continue

        prod_soup = BeautifulSoup(response.text, 'html.parser')

        # Produktionsname + Untertitel
        h1 = prod_soup.find('h1')
        prod_name = h1.get_text(strip=True) if h1 else ''
        if not prod_name:
            continue

        subtitle = prod_soup.find('p', class_='titles__subtitle')
        beschreibung = subtitle.get_text(strip=True) if subtitle else ''

        # Schedule-Items durchgehen
        for item in prod_soup.find_all('article', class_='production-schedule-item'):
            item_id = item.get('id', '')  # "2026-05-08"
            if not item_id.startswith(ziel_prefix):
                continue

            try:
                datum = datetime.strptime(item_id, '%Y-%m-%d')
            except ValueError:
                continue

            # Uhrzeit aus time-Element: "19:00 Uhr" oder "20:00 –21:00 Uhr"
            uhrzeit = 'siehe Website'
            time_el = item.find('time')
            if time_el:
                zeit_text = time_el.get_text(strip=True)
                zeit_match = re.search(r'(\d{1,2}:\d{2})', zeit_text)
                if zeit_match:
                    start_zeit = zeit_match.group(1)
                    uhrzeit = f"{start_zeit} Uhr"
                    try:
                        h, m = map(int, start_zeit.split(':'))
                        datum = datum.replace(hour=h, minute=m)
                    except ValueError:
                        pass

            # Spielstätte
            venue_a = item.find('a', href=lambda h: h and '/spielstaetten/' in h)
            ort = venue_a.get_text(strip=True) if venue_a else 'Ruhrfestspielhaus'

            termine.append(Termin(
                name=prod_name[:150], datum=datum, uhrzeit=uhrzeit,
                ort=ort[:150], link=prod_url,
                beschreibung=beschreibung[:200],
                quelle='ruhrfestspiele', kategorie='Theater/Festival',
            ))

    return termine


# ---------------------------------------------------------------------------
# 16. Backyard-Club e.V. — The Events Calendar (JSON-LD)
# ---------------------------------------------------------------------------

def hole_backyard(jahr: int, monat: int) -> list[Termin]:
    """Holt Events vom Backyard-Club Recklinghausen.

    The Events Calendar mit JSON-LD. Seite enthält JSON-LD doppelt
    (Hauptliste + Sidebar-Widget), daher interne Deduplizierung.
    """
    termine = _hole_events_calendar(
        BACKYARD_URL, 'backyard', 'Musik', jahr, monat
    )

    # HTML-Entities in Namen auflösen und Duplikate entfernen
    gesehen: set[str] = set()
    unique = []
    for t in termine:
        t.name = unescape(t.name)
        key = f"{t.name}|{t.datum.strftime('%Y-%m-%d %H:%M')}"
        if key not in gesehen:
            gesehen.add(key)
            unique.append(t)
    return unique


# ---------------------------------------------------------------------------
# 17. Cineworld Recklinghausen — Cineamo API
# ---------------------------------------------------------------------------

def hole_cineworld(jahr: int, monat: int) -> list[Termin]:
    """Holt Kinovorstellungen vom Cineworld Recklinghausen via Cineamo API.

    Die API liefert nur Daten pro Tag (kein Datumsbereich), daher wird
    jeder Tag des Monats einzeln abgefragt. Pro Film und Tag wird ein
    Termin erzeugt, alle Vorstellungszeiten stehen im Uhrzeit-Feld.
    """
    tage_im_monat = monthrange(jahr, monat)[1]
    # Film-Key (name|datum) → Liste der Uhrzeiten + Metadaten
    filme: dict[str, dict] = {}

    for tag in range(1, tage_im_monat + 1):
        datum_str = f"{jahr}-{monat:02d}-{tag:02d}"
        seite = 1

        while True:
            try:
                response = requests.get(
                    CINEWORLD_API,
                    params={'cinemaId': CINEWORLD_CINEMA_ID, 'date': datum_str, 'page': seite},
                    headers=HEADERS,
                    timeout=15,
                )
                if response.status_code != 200:
                    break
                data = response.json()
            except (requests.RequestException, ValueError):
                break

            items = data.get('_embedded', {}).get('showings', [])
            if not items:
                break

            for s in items:
                name = s.get('name', '').strip()
                start = s.get('startDatetime', '')
                if not name or not start:
                    continue

                try:
                    dt_utc = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    dt = dt_utc.astimezone(ZoneInfo('Europe/Berlin')).replace(tzinfo=None)
                except ValueError:
                    continue

                if not _im_monat(dt, jahr, monat):
                    continue

                zeit_str = dt.strftime('%H:%M')
                key = name  # Ein Eintrag pro Film pro Monat
                ticket_url = s.get('bookingUrlExternal', '') or s.get('onlineTicketUrl', '')

                if key not in filme:
                    filme[key] = {
                        'name': name,
                        'datum': dt.replace(hour=0, minute=0),  # Erste Vorstellung
                        'zeiten': set(),
                        'link': ticket_url or CINEWORLD_URL,
                        'beschreibung': '',
                    }
                else:
                    # Frühestes Datum merken
                    if dt.replace(hour=0, minute=0) < filme[key]['datum']:
                        filme[key]['datum'] = dt.replace(hour=0, minute=0)

                filme[key]['zeiten'].add(zeit_str)

            # Nächste Seite?
            if seite < data.get('_page_count', 1):
                seite += 1
            else:
                break

    termine = []
    for info in filme.values():
        zeiten = sorted(info['zeiten'])
        if len(zeiten) <= 4:
            uhrzeit = ' / '.join(zeiten) + ' Uhr'
        else:
            uhrzeit = 'täglich mehrere Zeiten'

        termine.append(Termin(
            name=info['name'][:150],
            datum=info['datum'],
            uhrzeit=uhrzeit,
            ort='Cineworld, Kemnastr. 3',
            link=info['link'],
            beschreibung=info['beschreibung'],
            quelle='cineworld',
            kategorie='Kino',
        ))

    return termine


# ---------------------------------------------------------------------------
# 18. Neue Philharmonie Westfalen — c-event-Struktur
# ---------------------------------------------------------------------------

def hole_neue_philharmonie(jahr: int, monat: int) -> list[Termin]:
    """Holt Events der Neuen Philharmonie Westfalen in Recklinghausen.

    HTML: div.c-event, Datum aus span.c-event__date-date ("10. März" ohne Jahr),
    Uhrzeit aus span.c-event__date-time, Titel aus h3.c-event__title,
    Ort aus div.c-event__venue + div.c-event__city.
    Stadtfilter: nur Events mit c-event__city = "Recklinghausen".
    """
    try:
        response = requests.get(NEUE_PHILHARMONIE_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (neue-philharmonie): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    termine = []

    for event in soup.find_all('div', class_='c-event'):
        # Stadtfilter: nur Recklinghausen
        city_div = event.find('div', class_='c-event__city')
        if not city_div or 'recklinghausen' not in city_div.get_text(strip=True).lower():
            continue

        # Datum: "10. März" (kein Jahr im HTML)
        date_span = event.find('span', class_='c-event__date-date')
        if not date_span:
            continue
        date_text = date_span.get_text(strip=True)

        date_match = re.match(r'(\d{1,2})\.\s*(\w+)', date_text)
        if not date_match:
            continue

        tag = int(date_match.group(1))
        monat_name = date_match.group(2).lower()
        event_monat = _MONATE.get(monat_name, 0)
        if not event_monat or event_monat != monat:
            continue

        # Uhrzeit: "19:30 Uhr"
        time_span = event.find('span', class_='c-event__date-time')
        uhrzeit = 'siehe Website'
        stunde, minute = 0, 0
        if time_span:
            zeit_match = re.search(r'(\d{1,2}):(\d{2})', time_span.get_text(strip=True))
            if zeit_match:
                stunde = int(zeit_match.group(1))
                minute = int(zeit_match.group(2))
                uhrzeit = f"{stunde:02d}:{minute:02d} Uhr"

        try:
            datum = datetime(jahr, event_monat, tag, stunde, minute)
        except ValueError:
            continue

        # Titel
        title_h3 = event.find('h3', class_='c-event__title')
        if not title_h3:
            continue
        name = title_h3.get_text(strip=True)
        if not name:
            continue

        # Ort: "Venue, Stadt"
        venue_div = event.find('div', class_='c-event__venue')
        venue = venue_div.get_text(strip=True) if venue_div else ''
        city = city_div.get_text(strip=True)
        ort = f"{venue}, {city}" if venue else city

        # Link
        link_a = event.find('a', class_='c-event__link')
        link = link_a.get('href', NEUE_PHILHARMONIE_URL) if link_a else NEUE_PHILHARMONIE_URL
        if link and not link.startswith('http'):
            link = f"https://www.neue-philharmonie-westfalen.de{link}"

        termine.append(Termin(
            name=name[:150], datum=datum, uhrzeit=uhrzeit,
            ort=ort[:150], link=link,
            quelle='neue-philharmonie', kategorie='Konzert',
        ))

    return termine


# ---------------------------------------------------------------------------
# 19. Ikonen-Museum Recklinghausen — event-list-item-Struktur
# ---------------------------------------------------------------------------

def hole_ikonen_museum(jahr: int, monat: int) -> list[Termin]:
    """Holt Events des Ikonen-Museums Recklinghausen.

    HTML: div.event-list-item, Datum aus div.event-list-value.event-startdate
    ("01.03." ohne Jahr), Titel aus div.title h4,
    Uhrzeit aus div.info ("Sonntag, 15:00 - 16:30 Uhr"),
    Beschreibung aus div.teaser.
    """
    try:
        response = requests.get(IKONEN_MUSEUM_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (ikonen-museum): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    termine = []

    for item in soup.find_all('div', class_='event-list-item'):
        # Datum: "01.03." (kein Jahr)
        datum_div = item.find('div', class_='event-startdate')
        if not datum_div:
            continue
        datum_text = datum_div.get_text(strip=True)
        datum_match = re.match(r'(\d{1,2})\.(\d{2})\.', datum_text)
        if not datum_match:
            continue

        tag = int(datum_match.group(1))
        event_monat = int(datum_match.group(2))
        if event_monat != monat:
            continue

        try:
            datum = datetime(jahr, event_monat, tag)
        except ValueError:
            continue

        # Titel
        title_div = item.find('div', class_='title')
        if not title_div:
            continue
        h4 = title_div.find('h4')
        name = h4.get_text(strip=True) if h4 else title_div.get_text(strip=True)
        if not name:
            continue

        # Uhrzeit aus div.info: "Sonntag, 15:00 - 16:30 Uhr"
        uhrzeit = 'siehe Website'
        info_div = item.find('div', class_='info')
        if info_div:
            info_text = info_div.get_text(strip=True)
            end_match = re.search(r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})\s*Uhr', info_text)
            start_match = re.search(r'(\d{1,2}:\d{2})', info_text)
            if end_match:
                uhrzeit = f"{end_match.group(1)}–{end_match.group(2)} Uhr"
            elif start_match:
                uhrzeit = f"{start_match.group(1)} Uhr"
            if start_match:
                try:
                    h, m = map(int, start_match.group(1).split(':'))
                    datum = datum.replace(hour=h, minute=m)
                except ValueError:
                    pass

        # Beschreibung
        teaser_div = item.find('div', class_='teaser')
        beschreibung = teaser_div.get_text(strip=True)[:200] if teaser_div else ''

        termine.append(Termin(
            name=name[:150], datum=datum, uhrzeit=uhrzeit,
            ort='Ikonen-Museum Recklinghausen', link=IKONEN_MUSEUM_URL,
            beschreibung=beschreibung,
            quelle='ikonen-museum', kategorie='Kunst',
        ))

    return termine


# ---------------------------------------------------------------------------
# 20. Debut um 11 (Ruhrfestspielhaus) — WordPress-Posts
# ---------------------------------------------------------------------------

def hole_debut_um_11(jahr: int, monat: int) -> list[Termin]:
    """Holt Konzerttermine der Reihe Debut um 11 im Ruhrfestspielhaus.

    WordPress: article.post-item, Konzerttermin aus h2.entry-title a Link-Text
    (Format: "15. März 2026, 11:00 Uhr" — enthält Jahr direkt).
    Beschreibung aus div.post-excerpt.
    """
    try:
        response = requests.get(DEBUT_UM_11_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (debut-um-11): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    termine = []

    monate_pattern = '|'.join(_MONATE.keys())
    datum_re = re.compile(
        rf'(\d{{1,2}})\.\s*({monate_pattern})\s+(\d{{4}}),?\s*(\d{{1,2}}):(\d{{2}})\s*Uhr',
        re.IGNORECASE,
    )

    for article in soup.find_all('article', class_='post-item'):
        title_h2 = article.find('h2', class_='entry-title')
        if not title_h2:
            continue
        a_tag = title_h2.find('a')
        if not a_tag:
            continue

        title_text = a_tag.get_text(strip=True)
        match = datum_re.search(title_text)
        if not match:
            continue

        tag = int(match.group(1))
        monat_name = match.group(2).lower()
        event_jahr = int(match.group(3))
        stunde = int(match.group(4))
        minute = int(match.group(5))

        event_monat = _MONATE.get(monat_name, 0)
        if not event_monat or event_monat != monat or event_jahr != jahr:
            continue

        try:
            datum = datetime(event_jahr, event_monat, tag, stunde, minute)
        except ValueError:
            continue

        link = a_tag.get('href', DEBUT_UM_11_URL)

        # Beschreibung / Programm aus dem Excerpt
        excerpt_div = article.find('div', class_='post-excerpt')
        beschreibung = excerpt_div.get_text(strip=True)[:200] if excerpt_div else ''

        termine.append(Termin(
            name='Debut um 11', datum=datum,
            uhrzeit=f"{stunde:02d}:{minute:02d} Uhr",
            ort='Ruhrfestspielhaus', link=link,
            beschreibung=beschreibung,
            quelle='debut-um-11', kategorie='Konzert',
        ))

    return termine


# ---------------------------------------------------------------------------
# 21. ADFC Recklinghausen — Termine + Radtouren via JSON-API
# ---------------------------------------------------------------------------

def _adfc_fetch(unit_key: str, event_type: str) -> list[dict]:
    """Holt alle Events einer ADFC-Unit aus der JSON-API (ein Request, kein Paging)."""
    params = {
        'unitKeys[]': unit_key,
        'eventType': event_type,
        'includeSubsidiary': 'true',
        'limit': '500',
    }
    try:
        response = requests.get(ADFC_API_URL, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.json().get('items', [])
    except (requests.RequestException, ValueError) as e:
        print(f"  Fehler beim Abrufen (adfc/{event_type}): {e}")
        return []


def hole_adfc(jahr: int, monat: int) -> list[Termin]:
    """Holt Events und Radtouren des ADFC Recklinghausen.

    JSON-API: api-touren-termine.adfc.de/api/eventItems/search
    Termine: unitKey=164420, Radtouren: unitKey=16442006.
    Felder: title, beginning, end, cShortDescription, city, startLocation,
    tourLength, tourSpeed, cSlug.
    Stadtfilter: city == "Recklinghausen".
    Kein Detail-Link verfügbar — Link zeigt auf ADFC-RE-Hauptseite.
    """
    alle_items = (
        [(item, 'Radtour') for item in _adfc_fetch(ADFC_UNIT_RADTOUREN, 'Radtour')]
        + [(item, 'Veranstaltung') for item in _adfc_fetch(ADFC_UNIT_TERMINE, 'Termin')]
    )

    termine = []
    for item, kategorie in alle_items:
        # Stadtfilter
        if item.get('city', '').lower() != 'recklinghausen':
            continue

        beginning = item.get('beginning', '')
        if not beginning:
            continue

        try:
            dt = datetime.fromisoformat(beginning).replace(tzinfo=None)
        except ValueError:
            continue

        if not _im_monat(dt, jahr, monat):
            continue

        name = item.get('title', '').strip()
        if not name:
            continue

        uhrzeit = dt.strftime('%H:%M Uhr') if dt.hour or dt.minute else 'siehe Website'

        # Ort: startLocation enthält "Straße PLZ Stadt"
        ort = item.get('startLocation', '').strip() or 'Recklinghausen'

        # Beschreibung: Kurztext + ggf. Tourangaben
        beschreibung = item.get('cShortDescription', '').strip()
        if kategorie == 'Radtour':
            tour_info = ' · '.join(filter(None, [
                item.get('tourLength', ''),
                item.get('tourSpeed', ''),
            ]))
            if tour_info:
                beschreibung = f"{tour_info}" + (f" — {beschreibung}" if beschreibung else '')

        termine.append(Termin(
            name=name[:150], datum=dt, uhrzeit=uhrzeit,
            ort=ort[:150], link=ADFC_RE_URL,
            beschreibung=beschreibung[:200],
            quelle='adfc', kategorie=kategorie,
        ))

    return termine


# ---------------------------------------------------------------------------
# 22. Atelierhaus Recklinghausen — ICS-Feed (ai1ec Plugin)
# ---------------------------------------------------------------------------

def _ics_unfold(text: str) -> str:
    """Entfaltet ICS-Zeilenfortsetzungen (CRLF + Leerzeichen/Tab)."""
    return re.sub(r'\r?\n[ \t]', '', text)


def _ics_wert(block: str, feld: str) -> str:
    """Liest einen Feldwert aus einem VEVENT-Block (mit Unfolding)."""
    m = re.search(rf'^{feld}(?:;[^:]+)?:(.+)$', block, re.MULTILINE)
    return _ics_unfold(m.group(1).strip()) if m else ''


def _ics_datum(dtstr: str) -> datetime | None:
    """Parst ein ICS-Datum (DATE oder DATETIME, mit/ohne Zeitzone)."""
    s = dtstr[:15].replace('Z', '')
    try:
        return datetime.strptime(s, '%Y%m%dT%H%M%S')
    except ValueError:
        try:
            return datetime.strptime(s[:8], '%Y%m%d')
        except ValueError:
            return None


def hole_atelierhaus(jahr: int, monat: int) -> list[Termin]:
    """Holt Events des Atelierhauses via ICS-Feed.

    Mehrtägige Ausstellungen erscheinen in jedem Monat, den sie abdecken.
    """
    try:
        response = requests.get(ATELIERHAUS_ICS, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (atelierhaus): {e}")
        return []

    erste = datetime(jahr, monat, 1)
    letzte = datetime(jahr, monat, monthrange(jahr, monat)[1])

    termine = []
    for block in re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', response.text, re.DOTALL):
        name = unescape(_ics_wert(block, 'SUMMARY'))
        if not name:
            continue

        dtstart_raw = _ics_wert(block, 'DTSTART')
        dtend_raw = _ics_wert(block, 'DTEND')
        if not dtstart_raw:
            continue

        datum_start = _ics_datum(dtstart_raw)
        datum_end = _ics_datum(dtend_raw) if dtend_raw else datum_start
        if not datum_start or not datum_end:
            continue

        all_day = 'T' not in dtstart_raw
        # iCal: DTEND bei Ganztages-Events = exklusiver Folgetag → einen Tag zurück
        if all_day and datum_end > datum_start:
            datum_end -= timedelta(days=1)

        mehrtaegig = (datum_end - datum_start).days >= 1
        link = _ics_wert(block, 'URL') or ATELIERHAUS_URL
        ort = _ics_wert(block, 'LOCATION') or 'Atelierhaus Recklinghausen'

        if mehrtaegig:
            # Ausstellung: erscheint wenn Zeitraum den Zielmonat überlappt
            if not (datum_start <= letzte and datum_end >= erste):
                continue
            datum = max(datum_start, erste)
            uhrzeit = 'ganztägig'
            bis = datum_end.strftime('%d.%m.%Y') if datum_end.year != jahr else datum_end.strftime('%d.%m.')
            beschreibung = f'Ausstellung bis {bis}'
            kategorie = 'Ausstellung'
        else:
            if not _im_monat(datum_start, jahr, monat):
                continue
            datum = datum_start
            uhrzeit = datum.strftime('%H:%M Uhr') if not all_day else 'ganztägig'
            beschreibung = ''
            kategorie = 'Kultur'

        termine.append(Termin(
            name=name[:150], datum=datum, uhrzeit=uhrzeit,
            ort=ort[:150], link=link, beschreibung=beschreibung,
            quelle='atelierhaus', kategorie=kategorie,
        ))

    return termine


# ---------------------------------------------------------------------------
# 23. Zu Gast in RE — Text-Parsing (Website-Builder, keine strukturierten Daten)
# ---------------------------------------------------------------------------

_MONATE_DE = {
    'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4,
    'Mai': 5, 'Juni': 6, 'Juli': 7, 'August': 8,
    'September': 9, 'Oktober': 10, 'November': 11, 'Dezember': 12,
}
_DATUM_RE_ZG = re.compile(
    r'(?:Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag),\s+'
    r'(\d{1,2})\.\s+(\w+)\s+(\d{4})'
)
_ZEIT_RE_ZG = re.compile(r'(?:ab\s+)?(\d{1,2})(?:[.,:]\s*(\d{2}))?\s*Uhr')


def hole_zu_gast_in_re(jahr: int, monat: int) -> list[Termin]:
    """Holt Festival-Tage von zu-gast-in-re.de via Text-Parsing.

    Das Festival findet jährlich Anfang August statt. Die Seite enthält nur
    das Programm des jeweils letzten oder aktuellen Jahres — gibt [] zurück,
    wenn noch kein Programm für das gewünschte Jahr/Monat veröffentlicht ist.
    """
    try:
        response = requests.get(ZU_GAST_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (zu-gast-in-re): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    # Alle Spans dedupliziert (Website-Builder dupliziert viele Elemente)
    spans = []
    prev = None
    for s in soup.find_all('span'):
        t = s.get_text(strip=True).replace('\xa0', ' ')
        if t and t != prev:
            spans.append(t)
            prev = t

    termine = []
    current_date = None
    current_program: list[str] = []

    def _abschluss():
        if current_date and _im_monat(current_date, jahr, monat) and current_program:
            program_text = ' '.join(current_program)
            m = _ZEIT_RE_ZG.search(program_text)
            if m:
                h, mi = int(m.group(1)), int(m.group(2) or 0)
                uhrzeit = f'{h:02d}:{mi:02d} Uhr'
                datum = current_date.replace(hour=h, minute=mi)
            else:
                uhrzeit = 'ganztägig'
                datum = current_date
            termine.append(Termin(
                name='Zu Gast in RE',
                datum=datum,
                uhrzeit=uhrzeit,
                ort='Rathausplatz, Recklinghausen',
                link=ZU_GAST_URL,
                beschreibung=program_text[:200],
                quelle='zu-gast-in-re',
                kategorie='Festival',
            ))

    for span_text in spans:
        m = _DATUM_RE_ZG.search(span_text)
        if m:
            _abschluss()
            tag = int(m.group(1))
            mo = _MONATE_DE.get(m.group(2), 0)
            j = int(m.group(3))
            current_date = datetime(j, mo, tag) if mo else None
            current_program = []
        elif current_date:
            current_program.append(span_text)

    _abschluss()
    return termine


# ---------------------------------------------------------------------------
# 23. RE-leuchtet — TEC REST-API
# ---------------------------------------------------------------------------

def hole_re_leuchtet(jahr: int, monat: int) -> list[Termin]:
    """Holt Events von RE-leuchtet via The Events Calendar REST-API."""
    letzter_tag = monthrange(jahr, monat)[1]
    params = {
        'start_date': f'{jahr}-{monat:02d}-01',
        'end_date': f'{jahr}-{monat:02d}-{letzter_tag}',
        'per_page': 50,
    }
    try:
        response = requests.get(RE_LEUCHTET_API, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as e:
        print(f"  Fehler beim Abrufen (re-leuchtet): {e}")
        return []

    termine = []
    for event in data.get('events', []):
        name = unescape(event.get('title', '').strip())
        if not name:
            continue

        start = event.get('start_date', '')
        try:
            datum = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue

        uhrzeit = datum.strftime('%H:%M Uhr') if datum.hour or datum.minute else 'siehe Website'
        venue = event.get('venue', {})
        ort = unescape(venue.get('venue', '') or 'Recklinghausen')
        link = event.get('url', '') or RE_LEUCHTET_URL
        beschreibung = _html_zu_text(event.get('description', ''))[:200]

        termine.append(Termin(
            name=name[:150], datum=datum, uhrzeit=uhrzeit,
            ort=ort[:150], link=link, beschreibung=beschreibung,
            quelle='re-leuchtet', kategorie='Kultur',
        ))

    return termine


# ---------------------------------------------------------------------------
# 23. Frauenforum Recklinghausen — Wiederkehrender Termin (kein Scraping)
# ---------------------------------------------------------------------------

def hole_frauenforum(jahr: int, monat: int) -> list[Termin]:
    """Berechnet den monatlichen Frauenforum-Termin (3. Dienstag, 17 Uhr).

    Kein Scraping — Termin wird aus Monatsregel berechnet.
    Pause im Juli und Dezember.
    Änderungen werden nur über Presse oder Facebook bekannt gegeben.
    """
    if monat in (7, 12):
        return []

    erster = datetime(jahr, monat, 1)
    tage_bis_dienstag = (1 - erster.weekday()) % 7
    dritter_dienstag = erster + timedelta(days=tage_bis_dienstag + 14)

    if dritter_dienstag.month != monat:
        return []

    datum = dritter_dienstag.replace(hour=17, minute=0)

    return [Termin(
        name='Frauenforum Recklinghausen',
        datum=datum,
        uhrzeit='17:00 Uhr',
        ort='Familienbüro, Große Geldstraße 19, Recklinghausen',
        link='',
        beschreibung='Treffen für alle Frauen des Frauenforums. Pause im Juli und Dezember. Änderungen nur über Presse oder Facebook.',
        quelle='frauenforum',
        kategorie='',
    )]


# ---------------------------------------------------------------------------
# 26. Josef P. Eich — Kirchenmusik (The Events Calendar / JSON-LD)
# ---------------------------------------------------------------------------

def hole_josefeich(jahr: int, monat: int) -> list[Termin]:
    """Holt Kirchenmusik-Termine von josefeich.de via JSON-LD."""
    return _hole_events_calendar(JOSEFEICH_URL, 'josefeich', 'Konzert', jahr, monat)


# ---------------------------------------------------------------------------
# 27. Der Recklinghäuser — Kultkneipe (Text-Parsing)
# ---------------------------------------------------------------------------

def hole_recklinghaeuser(jahr: int, monat: int) -> list[Termin]:
    """Holt Events von der-recklinghaeuser.de (Fließtext-Parsing)."""
    try:
        response = requests.get(RECKLINGHAEUSER_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (Der Recklinghäuser): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    termine = []

    # Events stehen als Fließtext, Datum im Format "Sa. 14. März 2026"
    text = soup.get_text('\n')
    monate_de = {
        'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4,
        'Mai': 5, 'Juni': 6, 'Juli': 7, 'August': 8,
        'September': 9, 'Oktober': 10, 'November': 11, 'Dezember': 12,
    }
    monate_pattern = '|'.join(monate_de.keys())
    pattern = re.compile(
        r'(?:Mo|Di|Mi|Do|Fr|Sa|So)\.\s+(\d{1,2})\.\s+(' + monate_pattern + r')\s+(\d{4})'
    )

    lines = text.split('\n')
    for i, line in enumerate(lines):
        m = pattern.search(line.strip())
        if not m:
            continue

        tag, monat_name, jahr_str = int(m.group(1)), m.group(2), int(m.group(3))
        monat_nr = monate_de[monat_name]

        try:
            datum = datetime(jahr_str, monat_nr, tag)
        except ValueError:
            continue

        if not _im_monat(datum, jahr, monat):
            continue

        # Titel und Uhrzeit aus den folgenden Zeilen extrahieren
        name = ''
        uhrzeit = 'siehe Website'
        for j in range(i + 1, min(i + 5, len(lines))):
            nachfolge = lines[j].strip()
            if not nachfolge:
                continue
            if not name:
                name = nachfolge
            # Uhrzeit im Format "ab 20 Uhr", "21 Uhr", "20:30 Uhr"
            zeit_match = re.search(r'(?:ab\s+)?(\d{1,2})(?::(\d{2}))?\s*Uhr', nachfolge, re.IGNORECASE)
            if zeit_match:
                h = int(zeit_match.group(1))
                mi = int(zeit_match.group(2)) if zeit_match.group(2) else 0
                datum = datum.replace(hour=h, minute=mi)
                uhrzeit = f"{h:02d}:{mi:02d} Uhr"
                break

        if not name:
            continue

        # Klammerinhalt mit Uhrzeit aus dem Namen entfernen
        name = re.sub(r'\s*\(.*?Uhr.*?\)', '', name).strip()

        termine.append(Termin(
            name=name[:150], datum=datum, uhrzeit=uhrzeit,
            ort='Der Recklinghäuser, Königswall 14',
            link=RECKLINGHAEUSER_URL,
            beschreibung='',
            quelle='recklinghaeuser', kategorie='',
        ))

    return termine


# ---------------------------------------------------------------------------
# 28. Subergs im Festspielhaus — WordPress-Blog (Datum im Titel)
# ---------------------------------------------------------------------------

def hole_subergs(jahr: int, monat: int) -> list[Termin]:
    """Holt Events von subergs.de/events/ (WordPress-Blogposts, Datum im Titel)."""
    try:
        response = requests.get(SUBERGS_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (Subergs): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    termine = []

    # Events haben h3-Tags mit Links, Datum im Format "DD.MM.YYYY – Titel"
    for h3 in soup.find_all('h3'):
        a = h3.find('a')
        if not a:
            continue

        text = a.get_text(strip=True)
        # Muster: "13.03.2026 – Tatort Dinner „Mord in Paris""
        m = re.match(r'(\d{2})\.(\d{2})\.(\d{4})\s*[–\-]\s*(.+)', text)
        if not m:
            continue

        tag, mon, jahr_str, name = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4).strip()

        try:
            datum = datetime(jahr_str, mon, tag)
        except ValueError:
            continue

        if not _im_monat(datum, jahr, monat):
            continue

        link = a.get('href', '')

        termine.append(Termin(
            name=name[:150], datum=datum, uhrzeit='siehe Website',
            ort='Subergs im Festspielhaus, Recklinghausen',
            link=link,
            beschreibung='',
            quelle='subergs', kategorie='',
        ))

    return termine


# ---------------------------------------------------------------------------
# 29. Seniorenbeirat Recklinghausen — Events Manager (WordPress)
# ---------------------------------------------------------------------------

def hole_seniorenbeirat(jahr: int, monat: int) -> list[Termin]:
    """Holt Events vom Seniorenbeirat Recklinghausen (Events Manager Plugin)."""
    termine = []
    besuchte_urls: set[str] = set()
    url = SENIORENBEIRAT_URL

    while url and url not in besuchte_urls and len(besuchte_urls) < 10:
        besuchte_urls.add(url)
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            if not besuchte_urls - {url}:
                print(f"  Fehler beim Abrufen (Seniorenbeirat): {e}")
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        gefunden = False

        for item in soup.select('.em-item'):
            h3 = item.find('h3')
            if not h3:
                continue

            a = h3.find('a')
            name = a.get_text(strip=True) if a else h3.get_text(strip=True)
            link = a.get('href', '') if a else ''
            if not name:
                continue

            meta = item.select_one('.em-item-meta')
            ort_el = item.select_one('.em-event-location a') or item.select_one('.em-event-location')
            meta_text = meta.get_text(strip=True) if meta else ''
            ort = ort_el.get_text(strip=True) if ort_el else ''

            # Datum parsen: "16. März 2026" oder "16.3.2026" oder "16.3." etc.
            datum = None
            uhrzeit = 'siehe Website'

            # Format "DD. Monat YYYY" (Events Manager Standard)
            monate_de = {
                'januar': 1, 'februar': 2, 'märz': 3, 'april': 4,
                'mai': 5, 'juni': 6, 'juli': 7, 'august': 8,
                'september': 9, 'oktober': 10, 'november': 11, 'dezember': 12,
            }
            dm = re.search(r'(\d{1,2})\.\s*(\w+)\s*(\d{4})', meta_text)
            if dm:
                tag = int(dm.group(1))
                monat_name = dm.group(2).lower()
                jahr_str = int(dm.group(3))
                if monat_name in monate_de:
                    try:
                        datum = datetime(jahr_str, monate_de[monat_name], tag)
                    except ValueError:
                        pass

            # Fallback: "DD.MM.YYYY"
            if not datum:
                dm2 = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', meta_text)
                if dm2:
                    try:
                        datum = datetime(int(dm2.group(3)), int(dm2.group(2)), int(dm2.group(1)))
                    except ValueError:
                        pass

            if not datum:
                continue

            # Uhrzeit aus eigenem Element extrahieren
            zeit_el = item.select_one('.em-event-time')
            zeit_text = zeit_el.get_text(strip=True) if zeit_el else ''
            zm = re.search(r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})', zeit_text)
            if zm:
                uhrzeit = f"{zm.group(1)}–{zm.group(2)} Uhr"
            else:
                zm2 = re.search(r'(\d{1,2}:\d{2})', zeit_text)
                if zm2:
                    uhrzeit = f"{zm2.group(1)} Uhr"

            # Stunde in datum setzen
            if uhrzeit != 'siehe Website':
                try:
                    h, m = map(int, re.search(r'(\d{1,2}):(\d{2})', uhrzeit).groups())
                    datum = datum.replace(hour=h, minute=m)
                except (ValueError, AttributeError):
                    pass

            if not _im_monat(datum, jahr, monat):
                gefunden = True  # Es gibt Events, aber nicht im Zielmonat
                continue

            gefunden = True
            termine.append(Termin(
                name=unescape(name)[:150], datum=datum, uhrzeit=uhrzeit,
                ort=unescape(ort)[:150] if ort else 'Recklinghausen',
                link=link,
                beschreibung='',
                quelle='seniorenbeirat', kategorie='Senioren',
            ))

        # Paginierung: nächste Seite via ?pno=N
        next_link = None
        for pg_a in soup.select('a[href*="pno="]'):
            href = pg_a.get('href', '')
            pno_match = re.search(r'pno=(\d+)', href)
            if pno_match and href not in besuchte_urls:
                next_link = href
                if not next_link.startswith('http'):
                    next_link = f"https://seniorenbeirat-recklinghausen.com{next_link}"
                break

        # Aufhören wenn keine Events mehr gefunden oder alle im Zielmonat vorbei
        if not gefunden and termine:
            break
        url = next_link

    return termine


# ---------------------------------------------------------------------------
# 30. Zeche Klärchen — Stadtteilpark Hochlarmark (Text-Parsing)
# ---------------------------------------------------------------------------

_MONATE_DE_ZK = {
    'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4,
    'Mai': 5, 'Juni': 6, 'Juli': 7, 'August': 8,
    'September': 9, 'Oktober': 10, 'November': 11, 'Dezember': 12,
}
_DATUM_RE_ZK = re.compile(
    r'(\d{1,2})\.\s*(?:und\s+\d{1,2}\.\s*)?'
    r'(?:(' + '|'.join(_MONATE_DE_ZK) + r')\s+(\d{4})'
    r'|(\d{2})\.(\d{4}))'
)


def hole_zeche_klaerchen(jahr: int, monat: int) -> list[Termin]:
    """Holt Events von Zeche Klärchen (Stadtteilpark Hochlarmark).

    Struktur: Joomla-Seite, Termine als Fließtext in <p>-Elementen mit
    font-size:24px Spans. Datum und Titel manchmal getrennte <p>-Tags,
    manchmal in einem gemeinsamen.
    Datumsformate: "27. März 2026", "12.09.2026", "10. und 11. Oktober 2026".
    """
    try:
        response = requests.get(ZECHE_KLAERCHEN_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Fehler beim Abrufen (Zeche Klärchen): {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    main = soup.find('main', id='tm-main') or soup

    # Alle <p>-Elemente mit 24px-Spans sammeln (Seitenuntertitel ausschließen)
    paras = []
    for p in main.find_all('p'):
        spans = p.find_all('span', style=lambda s: s and 'font-size: 24px' in s)
        if not spans:
            continue
        text = p.get_text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text.replace('\xa0', ' ')).strip()
        if text and 'Veranstaltungen im' not in text:
            paras.append(text)

    termine = []
    i = 0
    while i < len(paras):
        text = paras[i]
        m = _DATUM_RE_ZK.search(text)
        if not m:
            i += 1
            continue

        tag = int(m.group(1))
        if m.group(2):  # "DD. Monat YYYY"
            monat_nr = _MONATE_DE_ZK[m.group(2)]
            jahr_nr = int(m.group(3))
        else:  # "DD.MM.YYYY"
            monat_nr = int(m.group(4))
            jahr_nr = int(m.group(5))

        try:
            datum = datetime(jahr_nr, monat_nr, tag)
        except ValueError:
            i += 1
            continue

        if not _im_monat(datum, jahr, monat):
            i += 1
            continue

        # Titel: alles nach dem Datum im gleichen Para, sonst nächstes Para
        titel = text[m.end():].strip()
        if not titel and i + 1 < len(paras):
            naechstes = paras[i + 1]
            if not _DATUM_RE_ZK.search(naechstes):
                titel = naechstes
                i += 1

        if not titel:
            titel = 'Veranstaltung Zeche Klärchen'

        termine.append(Termin(
            name=titel[:150],
            datum=datum,
            uhrzeit='',
            ort='Zeche Klärchen, Hochlarmark',
            link=ZECHE_KLAERCHEN_URL,
            beschreibung='',
            quelle='zeche-klaerchen',
            kategorie='',
        ))
        i += 1

    return termine


# ---------------------------------------------------------------------------
# 31. Manuelle Termine — JSON-Datei
# ---------------------------------------------------------------------------

def hole_manuelle_termine(jahr: int, monat: int) -> list[Termin]:
    """Liest manuell eingetragene Termine aus manuelle_termine.json."""
    import os
    json_pfad = os.path.join(os.path.dirname(__file__), 'manuelle_termine.json')

    try:
        with open(json_pfad, 'r', encoding='utf-8') as f:
            eintraege = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    termine = []
    for e in eintraege:
        if not e.get('freigegeben'):
            continue

        try:
            datum = datetime.strptime(e['datum'], '%Y-%m-%d')
        except (ValueError, KeyError):
            continue

        if not _im_monat(datum, jahr, monat):
            continue

        uhrzeit = 'siehe Website'
        if e.get('uhrzeit'):
            try:
                h, m = map(int, e['uhrzeit'].split(':'))
                datum = datum.replace(hour=h, minute=m)
                uhrzeit = f"{h:02d}:{m:02d} Uhr"
            except ValueError:
                uhrzeit = e['uhrzeit']

        termine.append(Termin(
            name=e.get('name', '')[:150],
            datum=datum,
            uhrzeit=uhrzeit,
            ort=e.get('ort', '')[:150],
            link=e.get('link', ''),
            beschreibung=e.get('beschreibung', '')[:800],
            quelle='manuell',
            kategorie=e.get('kategorie', ''),
        ))

    return termine
