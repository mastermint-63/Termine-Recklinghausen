#!/usr/bin/env python3
"""
Termine in Recklinghausen — Dashboard
Sammelt Veranstaltungen aus mehreren Quellen und generiert ein HTML-Dashboard.

Verwendung:
    python3 app.py              # Generiert aktuellen + 4 weitere Monate
    python3 app.py 2026 2       # Generiert ab Februar 2026 (5 Monate)
    python3 app.py 2026 2 6     # Generiert 6 Monate ab Februar 2026
    python3 app.py --no-browser # Ohne Browser öffnen
"""

import html as _html
import json as _json
import os
import re
import webbrowser
import calendar
from datetime import datetime
from difflib import SequenceMatcher

from scraper import (
    # hole_regioactive,  # regioactive.de blockiert seit 2026-03 mit 403
    hole_stadt_re, hole_altstadtschmiede,
    hole_vesterleben, hole_sternwarte, hole_kunsthalle,
    hole_stadtbibliothek, hole_nlgr, hole_literaturtage, hole_vhs,
    hole_stadtarchiv, hole_geschichte_re,
    hole_gastkirche, hole_ruhrfestspiele, hole_backyard, hole_cineworld,
    hole_neue_philharmonie, hole_ikonen_museum, hole_debut_um_11, hole_adfc,
    hole_atelierhaus, hole_zu_gast_in_re, hole_re_leuchtet, hole_frauenforum,
    hole_josefeich, hole_recklinghaeuser, hole_subergs,
    hole_seniorenbeirat, hole_zeche_klaerchen, hole_stadtlabor,
    hole_gegendruck, hole_ev_akademie, hole_manuelle_termine, hole_ratssitzungen,
    hole_moondock, hole_facebook, Termin,
)


QUELLEN = {
    # 'regioactive': 'regioactive.de',  # blockiert seit 2026-03 mit 403
    'stadt-re': 'Stadt RE',
    'altstadtschmiede': 'Altstadtschmiede',
    'vesterleben': 'Vesterleben.de',
    'sternwarte': 'Sternwarte',
    'kunsthalle': 'Kunsthalle',
    'stadtbibliothek': 'Stadtbibliothek',
    'nlgr': 'Neue Lit. Gesellschaft',
    'literaturtage': 'Literaturtage',
    'vhs': 'VHS',

    'stadtarchiv': 'Stadtarchiv',
    'geschichte-re': 'Heimatkunde',
    'gastkirche': 'Gastkirche',
    'ruhrfestspiele': 'Ruhrfestspiele',
    'backyard': 'Backyard-Club',
    'cineworld': 'Cineworld',
    'neue-philharmonie': 'Neue Philharmonie',
    'ikonen-museum': 'Ikonen-Museum',
    'debut-um-11': 'Debut um 11',
    'adfc': 'ADFC Recklinghausen',
    'atelierhaus': 'Atelierhaus',
    'zu-gast-in-re': 'Zu Gast in RE',
    're-leuchtet': 'RE-leuchtet',
    'frauenforum': 'Frauenforum',
    'josefeich': 'Josef P. Eich',
    'recklinghaeuser': 'Der Recklinghäuser',
    'subergs': 'Subergs',
    'seniorenbeirat': 'Seniorenbeirat',
    'zeche-klaerchen': 'Zeche Klärchen',
    'stadtlabor': 'StadtLabor RE',
    'gegendruck': 'Theater Gegendruck',
    'ev-akademie': 'Ev. Akademie',
    'manuell': 'Redaktion',
    'ratssitzungen': 'Ratssitzungen',
    'moondock': 'mOOndock',
    'facebook': 'Weitere Tipps',
}

# Footer-Quellenlinks (Anzeigename, URL). Werden im Footer per sorted() alphabetisch
# gerendert — beim Hinzufügen einer neuen Quelle hier eintragen, Reihenfolge egal.
# regioactive.de bewusst NICHT enthalten (Cloudflare-Block seit 26.02.2026, liefert nichts).
FOOTER_QUELLEN = [
    ('ADFC Recklinghausen', 'https://recklinghausen.adfc.de/'),
    ('Altstadtschmiede', 'https://www.altstadtschmiede.de/aktuelle-veranstaltungen'),
    ('Atelierhaus', 'https://atelierhaus-recklinghausen.de/kalendar/'),
    ('Backyard-Club', 'https://backyard-club.de/events'),
    ('Cineworld', 'https://www.cineworld-recklinghausen.de/de/programm'),
    ('Debut um 11', 'https://debut-um-11.de/konzerte-102/'),
    ('Der Recklinghäuser', 'https://www.der-recklinghaeuser.de/'),
    ('Gastkirche', 'https://www.gastkirche.de/index.php/termine'),
    ('Heimatkunde', 'https://geschichte-recklinghausen.de/veranstaltung/'),
    ('Ikonen-Museum', 'https://ikonen-museum.com/veranstaltungen/termine'),
    ('Josef P. Eich', 'https://josefeich.de/events/'),
    ('Kunsthalle', 'https://kunsthalle-recklinghausen.de/en/program/calendar'),
    ('Literaturtage', 'https://literaturtage-recklinghausen.de/veranstaltungen/'),
    ('mOOndock', 'https://www.moondock.tv/page/Events'),
    ('Neue Philharmonie', 'https://www.neue-philharmonie-westfalen.de/termine'),
    ('NLGR', 'https://nlgr.de/veranstaltungen/'),
    ('Ratssitzungen', 'https://stadt-recklinghausen.gremien.info'),
    ('RE-leuchtet', 'https://re-leuchtet.de/programm'),
    ('Ruhrfestspiele', 'https://www.ruhrfestspiele.de/programm'),
    ('Seniorenbeirat', 'https://seniorenbeirat-recklinghausen.com/veranstaltungen/'),
    ('Stadt RE', 'https://www.recklinghausen.de/inhalte/startseite/_veranstaltungskalender/'),
    ('Stadtarchiv', 'https://www.recklinghausen.de/Inhalte/Startseite/Ruhrfestspiele_Kultur/Dokumente/'),
    ('Stadtbibliothek', 'https://www.recklinghausen.de/inhalte/startseite/familie_bildung/stadtbibliothek/Veranstaltungen/'),
    ('StadtLabor RE', 'https://www.stadtlabor-re.de/aktuell/aktuell.php'),
    ('Sternwarte', 'https://sternwarte-recklinghausen.de/programm/veranstaltungskalender/'),
    ('Subergs', 'https://www.subergs.de/events/'),
    ('Theater Gegendruck', 'https://theater-gegendruck.de/termine/'),
    ('Ev. Akademie', 'https://www.akademie-re.de/veranstaltungen/'),
    ('Vesterleben.de', 'https://vesterleben.de/termine'),
    ('VHS', 'https://www.vhs-recklinghausen.de'),
    ('Weitere Tipps', 'https://www.facebook.com/events/search/?q=recklinghausen'),
    ('Zeche Klärchen', 'https://zeche-klaerchen.de/index.php/aktuelles'),
    ('Zu Gast in RE', 'https://www.zu-gast-in-re.de/programm'),
]

# Spotlight-Karten: Termine mit gleichem highlight-Key (aus manuelle_termine.json)
# werden pro Tag zu EINER besonders gestalteten Karte zusammengefasst statt als
# Einzeltermine zu erscheinen. Die Karte ist von der Quellen-Filterung ausgenommen.
HIGHLIGHTS = {
    'holzwurm50': {
        'jahre': '1976 — 2026',
        'titel': '50 Jahre Holzwurm',
        'untertitel': '… und kein bisschen leise!',
        'meta': 'Freitag, 18. September 2026 · Altstadtschmiede, Kellerstraße 10',
        'fuss': 'Anmeldung nicht erforderlich · Statt Geschenken: Beiträge fürs Mitbringbuffet',
        'link': 'https://holzwurm-recklinghausen.de/',
        'link_label': 'holzwurm-recklinghausen.de',
        'bild': 'hebbert/hebbert-winkend.png',
    },
}

# Scraper-Funktionen in Abruf-Reihenfolge: (Funktion, Label für Ausgabe)
SCRAPER = [
    # (hole_regioactive, 'regioactive.de'),  # blockiert seit 2026-03 mit 403
    (hole_stadt_re, 'Stadt RE'),
    (hole_altstadtschmiede, 'Altstadtschmiede'),
    (hole_vesterleben, 'Vesterleben.de'),
    (hole_sternwarte, 'Sternwarte'),
    (hole_kunsthalle, 'Kunsthalle'),
    (hole_stadtbibliothek, 'Stadtbibliothek'),
    (hole_nlgr, 'NLGR'),
    (hole_literaturtage, 'Literaturtage'),
    (hole_vhs, 'VHS'),
    (hole_stadtarchiv, 'Stadtarchiv'),
    (hole_geschichte_re, 'Heimatkunde'),
    (hole_gastkirche, 'Gastkirche'),
    (hole_ruhrfestspiele, 'Ruhrfestspiele'),
    (hole_backyard, 'Backyard-Club'),
    (hole_cineworld, 'Cineworld'),
    (hole_neue_philharmonie, 'Neue Philharmonie'),
    (hole_ikonen_museum, 'Ikonen-Museum'),
    (hole_debut_um_11, 'Debut um 11'),
    (hole_adfc, 'ADFC Recklinghausen'),
    (hole_atelierhaus, 'Atelierhaus'),
    (hole_zu_gast_in_re, 'Zu Gast in RE'),
    (hole_re_leuchtet, 'RE-leuchtet'),
    (hole_frauenforum, 'Frauenforum'),
    (hole_josefeich, 'Josef P. Eich'),
    (hole_recklinghaeuser, 'Der Recklinghäuser'),
    (hole_subergs, 'Subergs'),
    (hole_seniorenbeirat, 'Seniorenbeirat'),
    (hole_zeche_klaerchen, 'Zeche Klärchen'),
    (hole_stadtlabor, 'StadtLabor RE'),
    (hole_gegendruck, 'Theater Gegendruck'),
    (hole_ev_akademie, 'Ev. Akademie'),
    (hole_ratssitzungen, 'Ratssitzungen'),
    (hole_moondock, 'mOOndock'),
    (hole_facebook, 'Facebook'),
    (hole_manuelle_termine, 'Redaktion'),
]


def _normalisiere(name: str) -> str:
    """Normalisiert einen Eventnamen für Vergleiche."""
    name = name.lower().strip()
    name = name.replace('-', ' ')         # Bindestriche zu Leerzeichen
    name = re.sub(r'[^\w\s]', '', name)   # Sonderzeichen entfernen
    name = re.sub(r'\s+', ' ', name)      # Mehrfach-Leerzeichen
    return name


# Tier 2 = Aggregatoren (listen auch fremde Events auf → Malus im Score)
# Tier 1 = Veranstalter (Default; listen nur eigene Events)
_QUELLEN_TIER: dict[str, int] = {
    'stadt-re': 2,
    'vesterleben': 2,
    'recklinghaeuser': 2,
    'facebook': 2,
    # 'regioactive': 2,  # blockiert seit 2026-03; bei Reaktivierung aktivieren
}


def _ist_fuzzy_duplikat(name_a: str, name_b: str) -> bool:
    """Prüft ob zwei normalisierte Namen fuzzy-ähnlich genug sind für ein Duplikat."""
    woerter_a = name_a.split()
    woerter_b = name_b.split()
    # Guard: Beide Namen mindestens 4 Wörter (kurze Namen sind zu mehrdeutig)
    if len(woerter_a) < 4 or len(woerter_b) < 4:
        return False
    # SequenceMatcher: Zeichenbasierte Ähnlichkeit >= 0.75
    if SequenceMatcher(None, name_a, name_b).ratio() < 0.75:
        return False
    # Jaccard token overlap >= 0.5
    set_a = set(woerter_a)
    set_b = set(woerter_b)
    jaccard = len(set_a & set_b) / len(set_a | set_b)
    if jaccard < 0.7:
        return False
    return True


# Stoppwörter: zu generisch für Schlüsselwort-Dedup
_STOPPWOERTER = {
    # Artikel, Präpositionen, Konjunktionen
    'im', 'in', 'der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine',
    'und', 'oder', 'mit', 'für', 'von', 'zu', 'am', 'auf', 'aus', 'bei',
    'nach', 'vor', 'über', 'unter', 'zwischen', 'durch', 'bis', 'um',
    'einen', 'einem', 'einer', 'eines', 'nicht', 'aber', 'auch', 'noch',
    'wie', 'was', 'zum', 'zur', 'vom', 'beim', 'ins',
    # Veranstaltungs-generisch
    'recklinghausen', 're', 'veranstaltung', 'party', 'night', 'nacht',
    'club', 'live', 'show', 'abend', 'konzert', 'fest', 'festival',
    'vortrag', 'online', 'onlinevortrag', 'workshop', 'kurs', 'seminar',
    'bildungsurlaub', 'intensivkurs', 'thema', 'leicht', 'gemacht',
    # Sprachen / VHS-generisch
    'anfänger', 'anfängerinnen', 'teilnehmende', 'vorkenntnissen',
    'spanisch', 'französisch', 'englisch', 'italienisch', 'niederländisch',
    # Häufig in Titeln, aber nicht markant
    'geschichte', 'kunst', 'welt', 'leben', 'menschen', 'neue', 'neuen',
    'lesung', 'führung', 'ausstellung', 'eröffnung',
    'alltag', 'beruf', 'beruflichen', 'frau', 'frauen', 'mann', 'männer',
    'treffen', 'gruppe', 'trauer', 'trauergruppe',
    'reise', 'familienfragen',
}


def _hat_markantes_schluesselwort(name_a: str, name_b: str) -> bool:
    """Prüft ob zwei normalisierte Namen ein markantes Schlüsselwort teilen (≥5 Zeichen).
    Erkennt auch Zusammenschreibungen: 'discofox' matcht 'disco fox'."""
    woerter_a = set(name_a.split()) - _STOPPWOERTER
    woerter_b = set(name_b.split()) - _STOPPWOERTER
    # Direkte Wort-Übereinstimmung (nur markante Wörter)
    for wort in woerter_a & woerter_b:
        if len(wort) >= 5:
            return True
    # Zusammenschreibung: ganzer Name ohne Leerzeichen enthält Wort aus dem anderen
    # z.B. "discofox" in "disco fox night" → kompakt_b = "discofoxnight"
    kompakt_a = name_a.replace(' ', '')
    kompakt_b = name_b.replace(' ', '')
    for wort in woerter_a:
        if len(wort) >= 6 and wort in kompakt_b:
            return True
    for wort in woerter_b:
        if len(wort) >= 6 and wort in kompakt_a:
            return True
    return False


def _parse_stunde(uhrzeit: str) -> int | None:
    """Extrahiert die Startstunde aus einem Uhrzeit-String."""
    m = re.search(r'(\d{1,2})[:.]?\d{0,2}\s*(?:Uhr|uhr|$)', uhrzeit)
    if m:
        return int(m.group(1))
    m = re.match(r'(\d{1,2})', uhrzeit)
    if m:
        return int(m.group(1))
    return None


def _gleiche_zeitnah(uhrzeit_a: str, uhrzeit_b: str) -> bool:
    """Prüft ob zwei Uhrzeiten kompatibel sind (gleich, nah beieinander, oder eine fehlt/generisch)."""
    generisch = ('', 'ganztägig', 'siehe Website')
    if uhrzeit_a in generisch or uhrzeit_b in generisch:
        return True
    if uhrzeit_a == uhrzeit_b:
        return True
    # Toleranz: maximal 2 Stunden Differenz
    h_a = _parse_stunde(uhrzeit_a)
    h_b = _parse_stunde(uhrzeit_b)
    if h_a is not None and h_b is not None:
        return abs(h_a - h_b) <= 2
    return False


def _termin_score(t: Termin) -> int:
    """Bewertet die Informationsqualität eines Termins (höher = besser).
    Aggregator-Quellen (Tier 2) erhalten −10 Malus, damit spezifische
    Veranstalter im Dedup-Vergleich immer gewinnen.
    """
    score = 0
    if t.link:
        score += 2
    if t.uhrzeit and t.uhrzeit not in ('ganztägig', 'siehe Website'):
        score += 2
    if t.beschreibung:
        score += 1
    if t.ort:
        score += 1
    if _QUELLEN_TIER.get(t.quelle, 1) == 2:
        score -= 10  # Aggregator-Malus: Veranstalter gewinnen immer
    if t.highlight:
        score += 100  # Spotlight-Einträge gewinnen jedes Duplikat
    return score


# Veranstaltungen demokratiefeindlicher Gruppierungen werden grundsätzlich nicht
# aufgenommen. Wortgrenzen (\b) sind wichtig, damit harmlose Treffer (z.B. "afd"
# in einem URL-Hash) nicht fälschlich gefiltert werden.
_AUSGESCHLOSSENE_MUSTER = re.compile(
    r"\bafd\b|\ba\.f\.d\.?|alternative für deutschland|junge alternative|afd-kv",
    re.IGNORECASE,
)


def ist_ausgeschlossen(t: Termin) -> bool:
    """True, wenn der Termin von einer ausgeschlossenen Gruppierung stammt (z.B. AfD)."""
    text = " ".join(filter(None, [t.name, t.beschreibung, t.ort, t.link]))
    return bool(_AUSGESCHLOSSENE_MUSTER.search(text))


def entferne_ausgeschlossene(termine: list[Termin]) -> list[Termin]:
    """Filtert Termine demokratiefeindlicher Gruppierungen (AfD) heraus."""
    return [t for t in termine if not ist_ausgeschlossen(t)]


# Kommerzielle Einzelhandelswerbung (z.B. Laden-Neueröffnungen, Rabattaktionen)
# rutscht gelegentlich über das Facebook-Screening (Apify, "Weitere Tipps") rein
# und gehört nicht in den Veranstaltungskalender. Konservativ gehalten: greift nur
# bei eindeutigen Werbesignalen ODER bekannten Discounter-/Ladenketten. Wortgrenzen
# (\b) sind essenziell, damit harmlose Treffer (z.B. "dm" oder "action" als Teil
# eines anderen Wortes) nicht fälschlich gefiltert werden.
_WERBE_MUSTER = re.compile(
    r"\bneueröffnung\b|\bwiedereröffnung\b|\beröffnungsangebot\w*|\beröffnungsfeier\b|"
    r"\beröffnungswoche\b|\brabattaktion\w*|\d+\s*%\s*rabatt|\bschlussverkauf\b|"
    # Bekannte Discounter-/Ladenketten (Non-Food / Drogerie / Lebensmittel).
    # Bewusst NICHT enthalten: "Action" — als Alltagswort zu mehrdeutig
    # (Action-Film, Action-Workshop); Action-Filialwerbung wird über die
    # Werbesignale oben (Neueröffnung/Rabatt) gefangen.
    r"\btedi\b|\bkik\b|\bwoolworth\b|\brossmann\b|\bmüller drogerie\b|"
    r"\blidl\b|\baldi\b|\bpenny\b|\bnkd\b|\btakko\b|\bdeichmann\b|"
    r"\bmäc[\s-]?geiz\b|\bthomas philipps\b|\bernsting'?s family\b|\bkodi\b|\bpepco\b",
    re.IGNORECASE,
)


def ist_werbung(t: Termin) -> bool:
    """True, wenn ein Facebook-Termin kommerzielle Einzelhandelswerbung ist.

    Greift bewusst nur auf die Facebook-Quelle (Apify-Screening), aus der solche
    Werbung stammt — seriöse Veranstalter-Quellen bleiben unberührt.
    """
    if t.quelle != 'facebook':
        return False
    text = " ".join(filter(None, [t.name, t.beschreibung, t.ort]))
    return bool(_WERBE_MUSTER.search(text))


def entferne_werbung(termine: list[Termin]) -> list[Termin]:
    """Filtert kommerzielle Einzelhandelswerbung aus Facebook-Terminen heraus."""
    return [t for t in termine if not ist_werbung(t)]


def entferne_duplikate(termine: list[Termin]) -> list[Termin]:
    """Entfernt Duplikate: gleiches Datum + identischer oder enthaltener Name."""
    # Nach Datum gruppieren
    nach_datum: dict[str, list[Termin]] = {}
    for t in termine:
        key = t.datum.strftime('%Y-%m-%d')
        nach_datum.setdefault(key, []).append(t)

    ergebnis = []
    for datum_key in sorted(nach_datum):
        gruppe = nach_datum[datum_key]
        # Nach Score absteigend sortieren (bester zuerst)
        gruppe.sort(key=lambda t: -_termin_score(t))

        behalten: list[Termin] = []
        for kandidat in gruppe:
            norm_k = _normalisiere(kandidat.name)
            ist_duplikat = False
            for vorhandener in behalten:
                norm_v = _normalisiere(vorhandener.name)
                # Stufe 1: Exakt gleich oder einer ist Teilstring des anderen
                if norm_k == norm_v or norm_k in norm_v or norm_v in norm_k:
                    ist_duplikat = True
                # Stufe 2: Fuzzy-Match + kompatible Uhrzeit
                elif _ist_fuzzy_duplikat(norm_k, norm_v) and _gleiche_zeitnah(kandidat.uhrzeit, vorhandener.uhrzeit):
                    ist_duplikat = True
                    print(f"[Fuzzy-Dedup] '{kandidat.name}' ({kandidat.quelle}) ≈ '{vorhandener.name}' ({vorhandener.quelle})")
                # Stufe 3: Markantes Schlüsselwort + kompatible Uhrzeit
                elif _hat_markantes_schluesselwort(norm_k, norm_v) and _gleiche_zeitnah(kandidat.uhrzeit, vorhandener.uhrzeit):
                    ist_duplikat = True
                    print(f"[Keyword-Dedup] '{kandidat.name}' ({kandidat.quelle}) ≈ '{vorhandener.name}' ({vorhandener.quelle})")
                if ist_duplikat:
                    # Fehlende Felder aus dem Duplikat ergänzen
                    if not vorhandener.beschreibung and kandidat.beschreibung:
                        vorhandener.beschreibung = kandidat.beschreibung
                    if vorhandener.uhrzeit in ('', 'siehe Website') and kandidat.uhrzeit not in ('', 'siehe Website'):
                        vorhandener.uhrzeit = kandidat.uhrzeit
                    if not vorhandener.ort or vorhandener.ort == 'Recklinghausen':
                        if kandidat.ort and kandidat.ort != 'Recklinghausen':
                            vorhandener.ort = kandidat.ort
                    break
            if not ist_duplikat:
                behalten.append(kandidat)

        ergebnis.extend(behalten)

    return ergebnis


def dateiname_fuer_monat(jahr: int, monat: int) -> str:
    return f"termine_re_{jahr}_{monat:02d}.html"


def generiere_kalender(jahr: int, monat: int, tage_mit_events: set[int]) -> str:
    cal = calendar.Calendar(firstweekday=0)
    wochen = cal.monthdayscalendar(jahr, monat)

    html = '<table class="kalender" id="kalender">\n'
    html += '<tr>'
    for tag_name in ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']:
        html += f'<th>{tag_name}</th>'
    html += '</tr>\n'

    for woche in wochen:
        html += '<tr>'
        for tag in woche:
            if tag == 0:
                html += '<td></td>'
            elif tag in tage_mit_events:
                datum_key = f"{jahr}-{monat:02d}-{tag:02d}"
                html += f'<td data-datum="{datum_key}"><a href="#datum-{datum_key}" class="kal-link">{tag}</a></td>'
            else:
                datum_key = f"{jahr}-{monat:02d}-{tag:02d}"
                html += f'<td class="kal-leer" data-datum="{datum_key}">{tag}</td>'
        html += '</tr>\n'

    html += '</table>'
    return html


def generiere_html(termine: list[Termin], jahr: int, monat: int,
                   verfuegbare_monate: list[tuple[int, int]],
                   dateiname: str = "") -> str:
    monatsnamen = [
        '', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
        'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'
    ]

    # Termine nach Datum gruppieren
    nach_datum = {}
    for t in termine:
        key = t.datum.strftime('%Y-%m-%d')
        if key not in nach_datum:
            nach_datum[key] = []
        nach_datum[key].append(t)

    # Termine-HTML
    termine_html = ""
    for datum_key in sorted(nach_datum.keys()):
        tage = nach_datum[datum_key]
        datum_formatiert = tage[0].datum_formatiert()

        termine_html += f'''
        <div class="datum-gruppe" id="datum-{datum_key}">
            <h2 class="datum-header">{datum_formatiert}</h2>
            <div class="termine-liste">
        '''

        # Spotlight-Karten: alle Highlight-Termine des Tages mit gleichem Key
        # werden zu einer Gold-Karte gebündelt (Konfiguration in HIGHLIGHTS)
        spotlight_keys = []
        for t in tage:
            if t.highlight in HIGHLIGHTS and t.highlight not in spotlight_keys:
                spotlight_keys.append(t.highlight)
        for hl_key in spotlight_keys:
            cfg = HIGHLIGHTS[hl_key]
            punkte = sorted((t for t in tage if t.highlight == hl_key), key=lambda x: x.uhrzeit)
            punkte_html = ''
            for t in punkte:
                besch_html = f'<div class="spotlight-beschreibung">{_html.escape(t.beschreibung)}</div>' if t.beschreibung else ''
                zeit = _html.escape(t.uhrzeit.replace(' Uhr', ''))
                punkte_html += f'''
                    <div class="spotlight-punkt">
                        <div class="spotlight-zeit">{zeit}</div>
                        <div class="spotlight-punkt-info">
                            <div class="spotlight-name">{_html.escape(t.name)}</div>
                            {besch_html}
                        </div>
                    </div>'''
            bild_html = f'<img class="spotlight-hebbert" src="{cfg["bild"]}" alt="Hebbert, das Holzwurm-Maskottchen" loading="lazy">' if cfg.get('bild') else ''
            termine_html += f'''
                <div class="spotlight-karte" data-events="{len(punkte)}">
                    <div class="spotlight-kopf">
                        {bild_html}
                        <div class="spotlight-jahre">{cfg['jahre']}</div>
                        <div class="spotlight-titel">{cfg['titel']}</div>
                        <div class="spotlight-untertitel">{cfg['untertitel']}</div>
                        <div class="spotlight-meta">{cfg['meta']}</div>
                    </div>
                    <div class="spotlight-programm">{punkte_html}
                    </div>
                    <div class="spotlight-fuss">{cfg['fuss']} · <a href="{cfg['link']}" target="_blank" rel="noopener noreferrer">{cfg['link_label']}</a></div>
                </div>
            '''

        normale_termine = [t for t in tage if t.highlight not in HIGHLIGHTS]
        for t in sorted(normale_termine, key=lambda x: (x.uhrzeit == 'ganztägig', x.uhrzeit == 'siehe Website', x.uhrzeit, x.name)):
            beschreibung_escaped = _html.escape(t.beschreibung)[:1000]

            name_esc = _html.escape(t.name)
            uhrzeit_esc = _html.escape(t.uhrzeit)
            ort_esc = _html.escape(t.ort) if t.ort else ''
            link_safe = t.link if t.link and t.link.startswith(('http://', 'https://')) else ''

            # Badge für Quelle
            badge_classes = {
                'regioactive': 'badge-regioactive',
                'altstadtschmiede': 'badge-altstadtschmiede',
                'sternwarte': 'badge-sternwarte',
                'kunsthalle': 'badge-kunsthalle',
                'vesterleben': 'badge-vesterleben',
                'stadt-re': 'badge-stadt',
                'stadtbibliothek': 'badge-stadtbibliothek',
                'nlgr': 'badge-nlgr',
                'literaturtage': 'badge-literaturtage',
                'vhs': 'badge-vhs',

                'stadtarchiv': 'badge-stadtarchiv',
                'geschichte-re': 'badge-geschichte-re',
                'gastkirche': 'badge-gastkirche',
                'ruhrfestspiele': 'badge-ruhrfestspiele',
                'backyard': 'badge-backyard',
                'cineworld': 'badge-cineworld',
                'neue-philharmonie': 'badge-neue-philharmonie',
                'ikonen-museum': 'badge-ikonen-museum',
                'debut-um-11': 'badge-debut-um-11',
                'adfc': 'badge-adfc',
                'atelierhaus': 'badge-atelierhaus',
                'zu-gast-in-re': 'badge-zu-gast-in-re',
                're-leuchtet': 'badge-re-leuchtet',
                'frauenforum': 'badge-frauenforum',
                'josefeich': 'badge-josefeich',
                'recklinghaeuser': 'badge-recklinghaeuser',
                'subergs': 'badge-subergs',
                'seniorenbeirat': 'badge-seniorenbeirat',
                'zeche-klaerchen': 'badge-zeche-klaerchen',
                'stadtlabor': 'badge-stadtlabor',
                'gegendruck': 'badge-gegendruck',
                'ev-akademie': 'badge-ev-akademie',
                'ratssitzungen': 'badge-ratssitzungen',
                'moondock': 'badge-moondock',
                'facebook': 'badge-facebook',
                'manuell': 'badge-manuell',
            }
            badge_class = badge_classes.get(t.quelle, 'badge-default')
            quelle_label = QUELLEN.get(t.quelle, t.quelle)
            badge_html = f'<span class="badge {badge_class}">{quelle_label}</span>'

            if t.kategorie:
                badge_html += f' <span class="badge badge-kategorie">{_html.escape(t.kategorie)}</span>'

            # Name als Link oder aufklappbar
            if link_safe:
                name_html = f'<a href="{link_safe}" target="_blank" rel="noopener noreferrer">{name_esc}</a>'
            else:
                name_html = f'<span class="termin-toggle" onclick="this.closest(\'.termin\').classList.toggle(\'expanded\')">{name_esc}</span>'

            # Beschreibung: bei Link-Terminen und langer Beschreibung klickbar aufklappbar
            if beschreibung_escaped and link_safe and len(beschreibung_escaped) > 120:
                beschreibung_html = f'<div class="termin-beschreibung termin-beschreibung-mehr" onclick="this.closest(\'.termin\').classList.toggle(\'expanded\')">{beschreibung_escaped}</div>'
            elif beschreibung_escaped:
                beschreibung_html = f'<div class="termin-beschreibung">{beschreibung_escaped}</div>'
            else:
                beschreibung_html = ''

            termine_html += f'''
                <div class="termin" data-quelle="{t.quelle}">
                    <div class="termin-zeit">{uhrzeit_esc}</div>
                    <div class="termin-info">
                        <div class="termin-name">
                            {name_html}
                            {badge_html}
                        </div>
                        {f'<div class="termin-ort">{ort_esc}</div>' if ort_esc else ''}
                        {beschreibung_html}
                    </div>
                </div>
            '''

        termine_html += '''
            </div>
            <div class="zurueck-link"><a href="#kalender">&#8593; Kalender</a></div>
        </div>
        '''

    # Quellen-Filter
    quellen_filter = '<option value="">Alle Quellen</option>'
    vorhandene_quellen = sorted(set(t.quelle for t in termine))
    for q in vorhandene_quellen:
        label = QUELLEN.get(q, q)
        quellen_filter += f'<option value="{q}">{label}</option>'

    # Monatsnavigation
    prev_monat = monat - 1 if monat > 1 else 12
    prev_jahr = jahr if monat > 1 else jahr - 1
    next_monat = monat + 1 if monat < 12 else 1
    next_jahr = jahr if monat < 12 else jahr + 1

    prev_verfuegbar = (prev_jahr, prev_monat) in verfuegbare_monate
    next_verfuegbar = (next_jahr, next_monat) in verfuegbare_monate

    prev_link = dateiname_fuer_monat(prev_jahr, prev_monat) + "#top" if prev_verfuegbar else "#"
    next_link = dateiname_fuer_monat(next_jahr, next_monat) + "#top" if next_verfuegbar else "#"

    prev_class = "" if prev_verfuegbar else " disabled"
    next_class = "" if next_verfuegbar else " disabled"

    # Kalenderblatt
    tage_mit_events = set(int(k.split('-')[2]) for k in nach_datum.keys())
    kalender_html = generiere_kalender(jahr, monat, tage_mit_events)

    # Footer-Quellenlinks alphabetisch (case-insensitiv) rendern
    footer_links_html = ' &middot;\n            '.join(
        f'<a href="{url}" target="_blank" rel="noopener noreferrer">{_html.escape(name)}</a>'
        for name, url in sorted(FOOTER_QUELLEN, key=lambda x: x[0].lower())
    )

    basis_url = "https://termine.holzwurm-recklinghausen.de"
    if dateiname and dateiname != "index.html":
        canonical_url = f"{basis_url}/{dateiname}"
    else:
        canonical_url = f"{basis_url}/"

    anzahl = len(termine)
    beschreibung_meta = f"Veranstaltungskalender Recklinghausen {monatsnamen[monat]} {jahr} — {anzahl} Termine aus {len(SCRAPER)} Quellen"
    titel = f"Termine Recklinghausen {monatsnamen[monat]} {jahr} ({anzahl}) | Holzwurm"

    # JSON-LD: CollectionPage + einzelne Events
    events_ld = []
    for t in termine:
        event_obj = {
            "@type": "Event",
            "name": t.name,
            "startDate": t.datum.strftime('%Y-%m-%d'),
            "location": {
                "@type": "Place",
                "name": t.ort or "Recklinghausen",
                "address": {"@type": "PostalAddress", "addressLocality": "Recklinghausen"}
            }
        }
        if t.link and t.link.startswith(('http://', 'https://')):
            event_obj["url"] = t.link
        if t.beschreibung:
            event_obj["description"] = t.beschreibung[:300]
        if t.uhrzeit and t.uhrzeit not in ('ganztägig', 'siehe Website'):
            # Nur erste Uhrzeit verwenden (Kino hat "13:00 / 14:00 / ...")
            erste_zeit = t.uhrzeit.split('/')[0].replace(' Uhr', '').strip()
            if len(erste_zeit) == 5 and ':' in erste_zeit:
                event_obj["startDate"] = t.datum.strftime('%Y-%m-%d') + 'T' + erste_zeit
        events_ld.append(event_obj)

    jsonld = _json.dumps({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"Veranstaltungskalender Recklinghausen — {monatsnamen[monat]} {jahr}",
        "description": beschreibung_meta,
        "url": canonical_url,
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": anzahl,
            "itemListElement": events_ld[:50]
        }
    }, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="de">
<head>
    <script defer src="https://cloud.umami.is/script.js" data-website-id="14825bec-c437-48e5-af55-02f181fdb17c"></script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titel}</title>
    <meta name="description" content="{beschreibung_meta}"/>
    <meta name="robots" content="follow, index, max-snippet:-1, max-video-preview:-1, max-image-preview:large"/>
    <link rel="canonical" href="{canonical_url}" />
    <link rel="icon" type="image/x-icon" href="favicon.ico">
    <link rel="icon" type="image/webp" href="favicon-96x96-1.webp">
    <meta property="og:locale" content="de_DE" />
    <meta property="og:type" content="website" />
    <meta property="og:title" content="{titel}" />
    <meta property="og:description" content="{beschreibung_meta}" />
    <meta property="og:url" content="{canonical_url}" />
    <meta property="og:site_name" content="Holzwurm Recklinghausen" />
    <meta property="og:image" content="{basis_url}/og-image.png" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
    <meta property="og:image:alt" content="{beschreibung_meta}" />
    <script type="application/ld+json">{jsonld}</script>
    <style>
        :root {{
            --bg-color: #e8e0d8;
            --card-bg: #fcfcfc;
            --text-color: #3b3b3b;
            --text-secondary: #666;
            --border-color: #d8ccbd;
            --accent-color: #d88a2b;
            --accent-light: #343538;
            --hover-color: #f5f0ea;
        }}

        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg-color: #2a2520;
                --card-bg: #3a3530;
                --text-color: #e8e0d8;
                --text-secondary: #a09080;
                --border-color: #4a4035;
                --accent-color: #e8a040;
                --accent-light: #343538;
                --hover-color: #3a3530;
            }}
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: "Lucida Grande", Verdana, -apple-system, sans-serif;
            background: var(--bg-color);
            color: var(--text-color);
            line-height: 1.5;
            padding: 20px;
        }}

        .container {{
            max-width: 1080px;
            margin: 0 auto;
        }}

        header {{
            text-align: center;
            margin-bottom: 30px;
            position: relative;
        }}

        .header-inner {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
        }}

        .hebbert {{
            width: 360px;
            height: auto;
            opacity: 0.85;
            flex-shrink: 0;
        }}

        .hebbert:hover {{
            opacity: 1;
        }}

        .header-text {{
            flex-shrink: 0;
        }}

        h1 {{
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 6px;
        }}

        .header-claim {{
            font-size: 0.85rem;
            font-weight: 600;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--accent-color);
            margin-bottom: 10px;
        }}

        .nav {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            margin-bottom: 20px;
        }}

        .nav-btn {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--accent-color);
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            text-decoration: none;
        }}

        .nav-btn:hover {{
            background: var(--hover-color);
            color: #00bcff;
        }}

        .nav-btn.disabled {{
            opacity: 0.3;
            pointer-events: none;
        }}

        .monat-titel {{
            font-size: 1.2rem;
            font-weight: 500;
        }}

        .filter-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding: 10px 15px;
            background: rgba(252, 252, 252, 0.5);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border-radius: 10px;
            border: 1px solid var(--border-color);
            flex-wrap: wrap;
            gap: 10px;
            position: sticky;
            top: 8px;
            z-index: 100;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }}

        @media (prefers-color-scheme: dark) {{
            .filter-bar {{
                background: rgba(58, 53, 48, 0.5);
            }}
        }}

        .vhs-toggle {{
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: var(--bg-color);
            color: var(--text-color);
            font-size: 14px;
            cursor: pointer;
        }}

        .vhs-toggle:hover {{
            background: var(--hover-color);
        }}

        .vhs-toggle.active {{
            background: var(--accent-color);
            color: white;
            border-color: var(--accent-color);
        }}

        .filter-bar select {{
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: var(--bg-color);
            color: var(--text-color);
            font-size: 14px;
        }}

        .stats {{
            font-size: 14px;
            color: var(--text-secondary);
        }}

        .datum-gruppe {{
            margin-bottom: 20px;
        }}

        .datum-header {{
            font-weight: 600;
            font-size: 1rem;
            padding: 10px 15px;
            background: var(--accent-color);
            color: white;
            border-radius: 10px 10px 0 0;
            margin: 0;
        }}

        .termine-liste {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-top: none;
            border-radius: 0 0 10px 10px;
        }}

        .termin {{
            display: flex;
            padding: 12px 15px;
            border-bottom: 1px solid var(--border-color);
            transition: background 0.2s;
        }}

        .termin:last-child {{
            border-bottom: none;
        }}

        .termin:hover {{
            background: var(--hover-color);
        }}

        /* Spotlight-Karte (redaktionelle Highlights, z.B. 50 Jahre Holzwurm).
           Goldpalette angelehnt an das Holzwurm-Heftcover. */
        .spotlight-karte {{
            margin: 14px;
            border: 2px solid #b8912a;
            border-radius: 12px;
            overflow: hidden;
            background: var(--card-bg);
            box-shadow: 0 3px 12px rgba(184, 145, 42, 0.35);
        }}

        .spotlight-kopf {{
            position: relative;
            background: linear-gradient(135deg, #c9a227 0%, #a5820f 100%);
            color: #fff;
            padding: 18px 20px;
        }}

        .spotlight-hebbert {{
            float: right;
            width: 82px;
            height: auto;
            margin-left: 14px;
            background: #fff;
            border: 3px solid #fff;
            border-radius: 8px;
            transform: rotate(3deg);
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
        }}

        .spotlight-jahre {{
            font-size: 12px;
            letter-spacing: 3px;
            opacity: 0.9;
        }}

        .spotlight-titel {{
            font-size: 1.5rem;
            font-weight: 700;
            line-height: 1.2;
            margin: 2px 0;
        }}

        .spotlight-untertitel {{
            font-style: italic;
            font-size: 15px;
            margin-bottom: 8px;
        }}

        .spotlight-meta {{
            font-size: 13px;
            font-weight: 500;
            opacity: 0.95;
        }}

        .spotlight-programm {{
            padding: 6px 20px;
        }}

        .spotlight-punkt {{
            display: flex;
            gap: 14px;
            padding: 10px 0;
            border-bottom: 1px dashed var(--border-color);
        }}

        .spotlight-punkt:last-child {{
            border-bottom: none;
        }}

        .spotlight-zeit {{
            width: 52px;
            flex-shrink: 0;
            font-weight: 700;
            color: #a5820f;
            font-size: 14px;
        }}

        .spotlight-punkt-info {{
            flex: 1;
        }}

        .spotlight-name {{
            font-weight: 600;
            margin-bottom: 2px;
        }}

        .spotlight-beschreibung {{
            font-size: 13px;
            color: var(--text-secondary);
        }}

        .spotlight-fuss {{
            padding: 10px 20px;
            font-size: 13px;
            color: var(--text-secondary);
            background: rgba(201, 162, 39, 0.10);
            border-top: 1px solid var(--border-color);
        }}

        .spotlight-fuss a {{
            color: #a5820f;
            font-weight: 600;
            text-decoration: none;
        }}

        .spotlight-fuss a:hover {{
            text-decoration: underline;
        }}

        @media (prefers-color-scheme: dark) {{
            .spotlight-karte {{
                border-color: #d4af37;
                box-shadow: 0 3px 12px rgba(0, 0, 0, 0.4);
            }}

            .spotlight-kopf {{
                background: linear-gradient(135deg, #8a6d10 0%, #6b540c 100%);
            }}

            .spotlight-zeit,
            .spotlight-fuss a {{
                color: #d4af37;
            }}
        }}

        @media (max-width: 600px) {{
            .spotlight-hebbert {{
                width: 60px;
            }}
        }}

        .termin-zeit {{
            width: 110px;
            font-weight: 500;
            color: var(--accent-color);
            flex-shrink: 0;
            font-size: 14px;
        }}

        .termin-info {{
            flex: 1;
        }}

        .termin-name {{
            font-weight: 500;
            margin-bottom: 2px;
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }}

        .termin-name a {{
            color: var(--text-color);
            text-decoration: none;
        }}

        .termin-name a:hover {{
            color: var(--accent-color);
            text-decoration: underline;
        }}

        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
            white-space: nowrap;
        }}

        .badge-regioactive {{
            background: linear-gradient(135deg, #d88a2b 0%, #c67a1b 100%);
            color: white;
        }}

        .badge-altstadtschmiede {{
            background: linear-gradient(135deg, #8B6914 0%, #705210 100%);
            color: white;
        }}

        .badge-sternwarte {{
            background: linear-gradient(135deg, #343538 0%, #2f3033 100%);
            color: white;
        }}

        .badge-kunsthalle {{
            background: linear-gradient(135deg, #b05030 0%, #903820 100%);
            color: white;
        }}

        .badge-vesterleben {{
            background: linear-gradient(135deg, #5a8a3a 0%, #4a7a2a 100%);
            color: white;
        }}

        .badge-stadt {{
            background: linear-gradient(135deg, #2a7ab5 0%, #1a6a9a 100%);
            color: white;
        }}

        .badge-stadtbibliothek {{
            background: linear-gradient(135deg, #5a7ab0 0%, #4a6a9a 100%);
            color: white;
        }}

        .badge-nlgr {{
            background: linear-gradient(135deg, #8a5a8a 0%, #7a4a7a 100%);
            color: white;
        }}

        .badge-literaturtage {{
            background: linear-gradient(135deg, #a06050 0%, #905040 100%);
            color: white;
        }}

        .badge-vhs {{
            background: linear-gradient(135deg, #4a8a6a 0%, #3a7a5a 100%);
            color: white;
        }}


        .badge-stadtarchiv {{
            background: linear-gradient(135deg, #7a7060 0%, #6a6050 100%);
            color: white;
        }}

        .badge-geschichte-re {{
            background: linear-gradient(135deg, #8a6a40 0%, #7a5a30 100%);
            color: white;
        }}

        .badge-gastkirche {{
            background: linear-gradient(135deg, #6a8a6a 0%, #5a7a5a 100%);
            color: white;
        }}

        .badge-ruhrfestspiele {{
            background: linear-gradient(135deg, #c03030 0%, #a02020 100%);
            color: white;
        }}

        .badge-backyard {{
            background: linear-gradient(135deg, #4a4a4a 0%, #333333 100%);
            color: white;
        }}

        .badge-cineworld {{
            background: linear-gradient(135deg, #d4391c 0%, #b02010 100%);
            color: white;
        }}

        .badge-neue-philharmonie {{
            background: linear-gradient(135deg, #1a5276 0%, #154360 100%);
            color: white;
        }}

        .badge-ikonen-museum {{
            background: linear-gradient(135deg, #7d6608 0%, #6d5600 100%);
            color: white;
        }}

        .badge-debut-um-11 {{
            background: linear-gradient(135deg, #6c3483 0%, #5b2c6f 100%);
            color: white;
        }}

        .badge-adfc {{
            background: linear-gradient(135deg, #e2001a 0%, #c0001a 100%);
            color: white;
        }}

        .badge-atelierhaus {{
            background: linear-gradient(135deg, #7b5ea7 0%, #5e4080 100%);
            color: white;
        }}

        .badge-zu-gast-in-re {{
            background: linear-gradient(135deg, #1a7a4a 0%, #155f3a 100%);
            color: white;
        }}

        .badge-re-leuchtet {{
            background: linear-gradient(135deg, #f4a00a 0%, #d4880a 100%);
            color: white;
        }}

        .badge-frauenforum {{
            background: linear-gradient(135deg, #c0387a 0%, #a02060 100%);
            color: white;
        }}
        .badge-josefeich {{
            background: linear-gradient(135deg, #8a7050 0%, #7a6040 100%);
            color: white;
        }}
        .badge-recklinghaeuser {{
            background: linear-gradient(135deg, #b08030 0%, #a07020 100%);
            color: white;
        }}
        .badge-subergs {{
            background: linear-gradient(135deg, #5a5a7a 0%, #4a4a6a 100%);
            color: white;
        }}
        .badge-seniorenbeirat {{
            background: linear-gradient(135deg, #8a3a5a 0%, #7a2a4a 100%);
            color: white;
        }}
        .badge-zeche-klaerchen {{
            background: linear-gradient(135deg, #7a4a30 0%, #6a3a20 100%);
            color: white;
        }}
        .badge-stadtlabor {{
            background: linear-gradient(135deg, #c06020 0%, #b05010 100%);
            color: white;
        }}
        .badge-gegendruck {{
            background: linear-gradient(135deg, #8b2252 0%, #6b1242 100%);
            color: white;
        }}
        .badge-ev-akademie {{
            background: linear-gradient(135deg, #1f6f78 0%, #0f5f68 100%);
            color: white;
        }}
        .badge-ratssitzungen {{
            background: linear-gradient(135deg, #1a3a5c 0%, #0a2a4c 100%);
            color: white;
        }}
        .badge-moondock {{
            background: linear-gradient(135deg, #4a1a6b 0%, #3a0a5b 100%);
            color: white;
        }}
        .badge-facebook {{
            background: linear-gradient(135deg, #1877F2 0%, #0f65d9 100%);
            color: white;
        }}
        .badge-manuell {{
            background: linear-gradient(135deg, #2a8a8a 0%, #1a7a7a 100%);
            color: white;
        }}

        .badge-default {{
            background: var(--hover-color);
            color: var(--text-secondary);
        }}

        .badge-kategorie {{
            background: var(--hover-color);
            color: var(--text-secondary);
            border: 1px solid var(--border-color);
        }}

        .termin-ort {{
            font-size: 13px;
            color: var(--text-secondary);
        }}

        .termin-beschreibung {{
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 4px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}

        .termin-toggle {{
            cursor: pointer;
            color: var(--text-color);
            border-bottom: 1px dashed var(--text-secondary);
        }}

        .termin-toggle:hover {{
            color: var(--accent-color);
        }}

        .termin-toggle::after {{
            content: ' \\25B8';
            font-size: 11px;
            color: var(--text-secondary);
        }}

        .termin.expanded .termin-toggle::after {{
            content: ' \\25BE';
        }}

        .termin:has(.termin-toggle) .termin-beschreibung {{
            display: none;
        }}

        .termin-beschreibung-mehr {{
            cursor: pointer;
        }}

        .termin-beschreibung-mehr::after {{
            content: ' \\25B8';
            font-size: 11px;
            color: var(--text-secondary);
        }}

        .termin.expanded .termin-beschreibung-mehr::after {{
            content: ' \\25BE';
        }}

        .termin.expanded .termin-beschreibung {{
            display: block;
            -webkit-line-clamp: unset;
            overflow: visible;
        }}

        .zurueck-link {{
            text-align: right;
            padding: 6px 15px;
            font-size: 13px;
        }}

        .zurueck-link a {{
            color: var(--accent-color);
            text-decoration: none;
            font-weight: 500;
        }}

        .keine-termine {{
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
        }}

        .hidden {{
            display: none !important;
        }}

        footer {{
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            background: #2f3033;
            border-radius: 10px;
            color: #aaa;
            font-size: 12px;
        }}

        footer a {{
            color: #aaa;
        }}

        .kalender {{
            width: 100%;
            max-width: 400px;
            margin: 0 auto 25px;
            border-collapse: collapse;
            text-align: center;
        }}

        .kalender th {{
            padding: 6px;
            font-size: 13px;
            color: var(--text-secondary);
            font-weight: 500;
        }}

        .kalender td {{
            padding: 6px;
            font-size: 14px;
            border-radius: 6px;
        }}

        .kalender .kal-leer {{
            color: var(--text-secondary);
            opacity: 0.5;
        }}

        .kalender .kal-link {{
            display: inline-block;
            width: 32px;
            height: 32px;
            line-height: 32px;
            border-radius: 50%;
            background: var(--accent-color);
            color: white;
            text-decoration: none;
            font-weight: 600;
        }}

        .kalender .kal-link:hover {{
            opacity: 0.8;
        }}

        .kalender .kal-heute {{
            outline: 2px solid var(--accent-color);
            outline-offset: -2px;
        }}

        .kalender .kal-heute .kal-link {{
            box-shadow: 0 0 0 2px white, 0 0 0 4px var(--accent-color);
        }}

        .nav-bottom {{
            display: flex;
            justify-content: space-between;
            margin: 30px 0 20px;
        }}

        @media (max-width: 600px) {{
            .termin {{
                flex-direction: column;
                gap: 4px;
            }}
            .termin-zeit {{
                width: auto;
            }}
            .hebbert {{
                width: 210px;
            }}
            .header-inner {{
                gap: 10px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-inner">
                <img src="hebbert/1984-01-verkleinert.jpg" alt="Hebbert in Aktion" class="hebbert" width="604" height="280" decoding="async">
                <div class="header-text">
                    <h1>Termine und Veranstaltungen in Recklinghausen</h1>
                    <p class="header-claim">powered by HOLZWURM</p>
                </div>
                <img src="hebbert/1985-04-verkleinert.jpg" alt="Hebbert's Terminkalender" class="hebbert" width="351" height="276" decoding="async">
            </div>
            <nav class="nav" aria-label="Monatsnavigation">
                <a href="{prev_link}" class="nav-btn{prev_class}">&larr; {monatsnamen[prev_monat]}</a>
                <span class="monat-titel">{monatsnamen[monat]} {jahr}</span>
                <a href="{next_link}" class="nav-btn{next_class}">{monatsnamen[next_monat]} &rarr;</a>
            </nav>
        </header>

        {kalender_html}

        <div class="filter-bar">
            <select id="quelle-filter" onchange="filterTermine()">
                {quellen_filter}
            </select>
            <button id="vhs-toggle" class="vhs-toggle" onclick="toggleVHS()">VHS einblenden</button>
            <button id="kino-toggle" class="vhs-toggle" onclick="toggleKino()">Kino einblenden</button>
            <div class="stats">
                <span id="termine-count">{len(termine)}</span> Termine
            </div>
        </div>

        <main id="termine-container">
            {termine_html if termine else '<div class="keine-termine">Keine Termine gefunden</div>'}
        </main>

        <div class="nav-bottom">
            <a href="{prev_link}" class="nav-btn{prev_class}">&larr; {monatsnamen[prev_monat]}</a>
            <a href="{next_link}" class="nav-btn{next_class}">{monatsnamen[next_monat]} &rarr;</a>
        </div>

        <footer>
            Generiert am {datetime.now().strftime('%d.%m.%Y um %H:%M Uhr')}<br>
            Quellen:
            {footer_links_html}
            <br><br>
            <a href="https://holzwurm-recklinghausen.de/impressum" target="_blank" rel="noopener noreferrer">Impressum</a> &middot;
            <a href="https://holzwurm-recklinghausen.de/datenschutzerklaerung" target="_blank" rel="noopener noreferrer">Datenschutzerklärung</a>
        </footer>
    </div>

    <script>
        // Heutigen Tag im Kalender markieren + zum ersten heutigen/zukünftigen Termin springen
        (function() {{
            const heute = new Date();
            const pad = n => String(n).padStart(2, '0');
            const key = heute.getFullYear() + '-' + pad(heute.getMonth() + 1) + '-' + pad(heute.getDate());

            // Kalender-Markierung
            const td = document.querySelector('td[data-datum="' + key + '"]');
            if (td) td.classList.add('kal-heute');

            // Nur springen wenn kein Anker in der URL gesetzt ist
            if (window.location.hash) return;

            // Alle Datumsgruppen durchsuchen: heute oder danach
            const gruppen = document.querySelectorAll('.datum-gruppe[id^="datum-"]');
            for (const gruppe of gruppen) {{
                const datum = gruppe.id.replace('datum-', '');
                if (datum >= key) {{
                    gruppe.scrollIntoView({{behavior: 'instant', block: 'start'}});
                    break;
                }}
            }}
        }})();

        // VHS und Kino sind beim Seitenaufruf immer ausgeblendet
        let vhsAusgeblendet = true;
        let kinoAusgeblendet = true;

        function _aktualisiereBtns() {{
            const vBtn = document.getElementById('vhs-toggle');
            const kBtn = document.getElementById('kino-toggle');
            vBtn.textContent = vhsAusgeblendet ? 'VHS einblenden' : 'VHS ausblenden';
            vBtn.classList.toggle('active', vhsAusgeblendet);
            kBtn.textContent = kinoAusgeblendet ? 'Kino einblenden' : 'Kino ausblenden';
            kBtn.classList.toggle('active', kinoAusgeblendet);
        }}

        function toggleVHS() {{
            vhsAusgeblendet = !vhsAusgeblendet;
            _aktualisiereBtns();
            filterTermine();
        }}

        function toggleKino() {{
            kinoAusgeblendet = !kinoAusgeblendet;
            _aktualisiereBtns();
            filterTermine();
        }}

        // Buttons beschriften und Filter sofort anwenden (z.B. wenn localStorage gesetzt)
        _aktualisiereBtns();
        filterTermine();


        function filterTermine() {{
            const quelleFilter = document.getElementById('quelle-filter').value;
            const termine = document.querySelectorAll('.termin');
            let sichtbar = 0;

            termine.forEach(t => {{
                const quelleMatch = !quelleFilter || t.dataset.quelle === quelleFilter;
                const vhsMatch = !vhsAusgeblendet || t.dataset.quelle !== 'vhs';
                const kinoMatch = !kinoAusgeblendet || t.dataset.quelle !== 'cineworld';

                if (quelleMatch && vhsMatch && kinoMatch) {{
                    t.classList.remove('hidden');
                    sichtbar++;
                }} else {{
                    t.classList.add('hidden');
                }}
            }});

            // Spotlight-Karten sind von der Filterung ausgenommen (immer sichtbar),
            // ihre Termine zählen aber mit
            document.querySelectorAll('.spotlight-karte').forEach(k => {{
                sichtbar += parseInt(k.dataset.events || '0', 10);
            }});

            document.getElementById('termine-count').textContent = sichtbar;

            document.querySelectorAll('.datum-gruppe').forEach(g => {{
                const sichtbareTermine = g.querySelectorAll('.termin:not(.hidden)');
                const hatSpotlight = g.querySelector('.spotlight-karte') !== null;
                g.classList.toggle('hidden', sichtbareTermine.length === 0 && !hatSpotlight);
            }});
        }}
    </script>
</body>
</html>'''

    return html


def berechne_monate(start_jahr: int, start_monat: int, anzahl: int) -> list[tuple[int, int]]:
    monate = []
    jahr, monat = start_jahr, start_monat
    for _ in range(anzahl):
        monate.append((jahr, monat))
        monat += 1
        if monat > 12:
            monat = 1
            jahr += 1
    return monate


def main():
    import sys

    no_browser = '--no-browser' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]

    jetzt = datetime.now()
    jahr = int(args[0]) if len(args) > 0 else jetzt.year
    monat = int(args[1]) if len(args) > 1 else jetzt.month
    anzahl_monate = int(args[2]) if len(args) > 2 else 5

    monate_liste = berechne_monate(jahr, monat, anzahl_monate)

    print(f"Generiere {anzahl_monate} Monate ab {monat}/{jahr}...")
    print("=" * 50)

    basis_pfad = os.path.dirname(__file__)
    erster_dateiname = None
    erster_monat_termine = None

    for idx, (j, m) in enumerate(monate_liste):
        monatsnamen = ['', 'Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
        print(f"\n[{idx+1}/{anzahl_monate}] {monatsnamen[m]} {j}:")

        alle_termine = []

        for scraper_fn, label in SCRAPER:
            events = scraper_fn(j, m)
            print(f"  -> {len(events)} {label}")
            alle_termine.extend(events)

        vor_filter = len(alle_termine)
        alle_termine = entferne_ausgeschlossene(alle_termine)
        ausgeschlossen = vor_filter - len(alle_termine)
        if ausgeschlossen:
            print(f"  -> {ausgeschlossen} Termin(e) ausgeschlossen (demokratiefeindliche Gruppierung)")

        vor_werbung = len(alle_termine)
        alle_termine = entferne_werbung(alle_termine)
        werbung = vor_werbung - len(alle_termine)
        if werbung:
            print(f"  -> {werbung} Termin(e) ausgeschlossen (kommerzielle Werbung)")

        vor_dedup = len(alle_termine)
        alle_termine = entferne_duplikate(alle_termine)
        alle_termine.sort()
        entfernt = vor_dedup - len(alle_termine)
        print(f"  => Gesamt: {len(alle_termine)} Termine ({entfernt} Duplikate entfernt)")

        dateiname = dateiname_fuer_monat(j, m)
        html = generiere_html(alle_termine, j, m, monate_liste, dateiname)
        ausgabe_pfad = os.path.join(basis_pfad, dateiname)
        with open(ausgabe_pfad, 'w', encoding='utf-8') as f:
            f.write(html)

        if idx == 0:
            erster_dateiname = ausgabe_pfad
            erster_monat_termine = alle_termine

    # index.html — eigener Canonical auf Root-URL
    j0, m0 = monate_liste[0]
    index_html = generiere_html(erster_monat_termine, j0, m0, monate_liste, "index.html")
    index_pfad = os.path.join(basis_pfad, 'index.html')
    with open(index_pfad, 'w', encoding='utf-8') as f:
        f.write(index_html)
    print("index.html generiert (Canonical: Root-URL)")

    # sitemap.xml
    heute = datetime.now().strftime('%Y-%m-%d')
    basis_url = "https://termine.holzwurm-recklinghausen.de"
    prioritaeten = [1.00, 0.64, 0.51, 0.41, 0.33, 0.26, 0.20, 0.16, 0.13, 0.10]
    sitemap_urls = [f'  <url>\n    <loc>{basis_url}/</loc>\n    <lastmod>{heute}</lastmod>\n    <priority>1.00</priority>\n  </url>']
    for idx, (j, m) in enumerate(monate_liste):
        prio = prioritaeten[min(idx + 1, len(prioritaeten) - 1)]
        datei = dateiname_fuer_monat(j, m)
        sitemap_urls.append(f'  <url>\n    <loc>{basis_url}/{datei}</loc>\n    <lastmod>{heute}</lastmod>\n    <priority>{prio:.2f}</priority>\n  </url>')
    sitemap_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(sitemap_urls)}
</urlset>'''
    sitemap_pfad = os.path.join(basis_pfad, 'sitemap.xml')
    with open(sitemap_pfad, 'w', encoding='utf-8') as f:
        f.write(sitemap_xml)
    print(f"sitemap.xml generiert ({len(monate_liste) + 1} URLs)")

    print("\n" + "=" * 50)
    print(f"Fertig! {anzahl_monate} Dateien generiert.")

    if erster_dateiname and not no_browser:
        webbrowser.open(f'file://{erster_dateiname}')


if __name__ == '__main__':
    main()
