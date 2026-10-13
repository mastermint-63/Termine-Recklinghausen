#!/usr/bin/env python3
"""
Termine in Recklinghausen — Dashboard
Sammelt Veranstaltungen aus mehreren Quellen und generiert ein HTML-Dashboard.

Verwendung:
    python3 app.py              # Generiert aktuellen + 4 weitere Monate
    python3 app.py 2026 2       # Generiert ab Februar 2026 (5 Monate)
    python3 app.py 2026 2 6     # Generiert 6 Monate ab Februar 2026
    python3 app.py --no-browser # Ohne Browser öffnen
    python3 app.py --ausgabe vorschau --termine-cache vorschau/termine_cache.json --ohne-tracking --no-browser
                                # Vorschau in eigenen Ordner, Termine nur einmal scrapen
"""

import html as _html
import json as _json
import os
import re
import webbrowser
import calendar
import dataclasses
from datetime import datetime
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo

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
    hole_moondock, hole_facebook, hole_campus_emscherland,
    hole_agenda21, hole_selbsthilfegruppen_re, hole_katholisch_netzwerk,
    hole_holzwurm, hole_selbsthilfe_kontaktstelle, hole_genial_re,
    hole_demokratie_werkstadt, hole_attac_re, hole_eventim, Termin,
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
    'campus-emscherland': 'Campus Emscherland',
    'manuell': 'Redaktion',
    'ratssitzungen': 'Ratssitzungen',
    'moondock': 'mOOndock',
    'facebook': 'Weitere Tipps',
    'agenda21': 'Lokale Agenda 21',
    'selbsthilfegruppen-re': 'Selbsthilfegruppen RE',
    'katholisch-netzwerk': 'Katholisch in RE',
    'holzwurm': 'Holzwurm',
    'selbsthilfe-kontaktstelle': 'Selbsthilfe-Kontaktstelle',
    'genial-re': 'ge·ni·al e.V.',
    'demokratie-werkstadt': 'Demokratie-Werkstadt',
    'attac-re': 'Attac Recklinghausen',
    'eventim': 'Eventim',
}

# Footer-Quellenlinks (Anzeigename, URL). Werden im Footer per sorted() alphabetisch
# gerendert — beim Hinzufügen einer neuen Quelle hier eintragen, Reihenfolge egal.
# regioactive.de bewusst NICHT enthalten (Cloudflare-Block seit 26.02.2026, liefert nichts).
FOOTER_QUELLEN = [
    ('ADFC Recklinghausen', 'https://recklinghausen.adfc.de/'),
    ('Altstadtschmiede', 'https://www.altstadtschmiede.de/aktuelle-veranstaltungen'),
    ('Lokale Agenda 21', 'https://www.lokale-agenda21-re.de/termine/'),
    ('Selbsthilfegruppen RE', 'https://www.selbsthilfegruppen-recklinghausen.de/?page_id=33'),
    ('Katholisch in RE', 'https://www.katholisch-re.de/aktuelles-termine/netzwerk'),
    ('Holzwurm', 'https://holzwurm-recklinghausen.de/veranstaltungen'),
    ('ge·ni·al e.V.', 'https://genial.re/all-events/'),
    ('Demokratie-Werkstadt', 'https://www.demokratie-werkstadt-re.de/termine/'),
    ('Attac Recklinghausen', 'https://www.attac-netzwerk.de/recklinghausen/termine'),
    ('Eventim', 'https://www.eventim.de/city/recklinghausen-83/'),
    ('Selbsthilfe-Kontaktstelle', 'https://www.paritaetischer-recklinghausen.de/netzwerk-buergerengagement/selbsthilfe-kontaktstelle/aktuelles-und-termine'),
    ('Atelierhaus', 'https://atelierhaus-recklinghausen.de/kalendar/'),
    ('Campus Emscherland', 'https://www.campus-emscherland.eu/'),
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
        'fuss': 'Anmeldung erforderlich · Statt Geschenken: Beiträge fürs Mitbringbuffet',
        'link': 'https://holzwurm-recklinghausen.de/',
        'link_label': 'holzwurm-recklinghausen.de',
        'bild': 'hebbert/hebbert-winkend.png',
        'signatur': 'hebbert/hebbert-signatur.png',
        'signatur_text': 'Euer',
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
    (hole_campus_emscherland, 'Campus Emscherland'),
    (hole_agenda21, 'Lokale Agenda 21'),
    (hole_selbsthilfegruppen_re, 'Selbsthilfegruppen RE'),
    (hole_katholisch_netzwerk, 'Katholisch in RE'),
    (hole_holzwurm, 'Holzwurm'),
    (hole_selbsthilfe_kontaktstelle, 'Selbsthilfe-Kontaktstelle'),
    (hole_genial_re, 'ge·ni·al e.V.'),
    (hole_demokratie_werkstadt, 'Demokratie-Werkstadt'),
    (hole_attac_re, 'Attac Recklinghausen'),
    (hole_eventim, 'Eventim'),
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
    'eventim': 2,
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
    # Generika ("Offenes Café" ≈ "Offenes Werkstadt-Treffen" wäre ein Fehlalarm)
    'offenes', 'offene', 'offener', 'treffen',
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
    # Fehlalarme 10.10.2026: Pflegegrad/Lichterlauf "kinder", Ausschüsse "sitzung"
    'kinder', 'jugendliche', 'öffentlich', 'öffentliche', 'öffentlicher', 'sitzung', 'grundkurs',
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
    # Zusammenschreibung: "discofox" ≈ "disco fox night". Der Treffer muss an Wortgrenzen
    # beginnen und enden, sonst trifft "gustav" in "gustave" oder "sterne" in "sternenhimmel".
    for wort in woerter_a:
        if len(wort) >= 6 and _an_wortgrenzen(wort, name_b):
            return True
    for wort in woerter_b:
        if len(wort) >= 6 and _an_wortgrenzen(wort, name_a):
            return True
    return False


_BEUGUNG = ('', 'e', 'n', 's', 'en', 'es', 'er')


def _an_wortgrenzen(wort: str, name: str) -> bool:
    """True, wenn wort eine Folge ganzer Wörter von name ergibt (ohne Leerzeichen).
    Lange Wörter (≥8) dürfen am Ende gebeugt sein: "seniorenbeirat" ≈ "seniorenbeirates"."""
    teile = name.split()
    for i in range(len(teile)):
        kette = ''
        for teil in teile[i:]:
            kette += teil
            if kette == wort:
                return True
            if len(wort) >= 8 and kette.startswith(wort) and kette[len(wort):] in _BEUGUNG:
                return True
            if len(kette) >= len(wort) + 2:
                break
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
                # Eine Quelle listet verschiedene Termine; unscharfe Stufen nur quellenübergreifend
                gleiche_quelle = kandidat.quelle == vorhandener.quelle
                # Stufe 1: Exakt gleich oder einer ist Teilstring des anderen
                if norm_k == norm_v or norm_k in norm_v or norm_v in norm_k:
                    ist_duplikat = True
                elif gleiche_quelle:
                    continue
                # Stufe 2: Fuzzy-Match + kompatible Uhrzeit
                elif _ist_fuzzy_duplikat(norm_k, norm_v) and _gleiche_zeitnah(kandidat.uhrzeit, vorhandener.uhrzeit):
                    ist_duplikat = True
                    print(f"[Fuzzy-Dedup] '{kandidat.name}' ({kandidat.quelle}) ≈ '{vorhandener.name}' ({vorhandener.quelle})")
                # Stufe 3: Markantes Schlüsselwort + kompatible Uhrzeit
                elif _hat_markantes_schluesselwort(norm_k, norm_v) and _gleiche_zeitnah(kandidat.uhrzeit, vorhandener.uhrzeit):
                    ist_duplikat = True
                    print(f"[Keyword-Dedup] '{kandidat.name}' ({kandidat.quelle}) ≈ '{vorhandener.name}' ({vorhandener.quelle})")
                if ist_duplikat:
                    # Eine Absage geht beim Zusammenführen nicht verloren
                    if kandidat.abgesagt:
                        vorhandener.abgesagt = True
                        vorhandener.verschoben_auf = vorhandener.verschoben_auf or kandidat.verschoben_auf
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


_KORREKTUR_MIN_TEILSTRING = 10


def korrektur_name_passt(norm_k: str, norm_t: str) -> bool:
    """Gleich, oder der kürzere Name (ab 10 Zeichen) steckt im längeren.

    Die Mindestlänge verhindert, dass kurze fremde Titel ("Party") mit erfasst werden.
    """
    if not norm_k or not norm_t:
        return False
    if norm_k == norm_t:
        return True
    kurz, lang = sorted((norm_k, norm_t), key=len)
    return len(kurz) >= _KORREKTUR_MIN_TEILSTRING and kurz in lang


KORREKTUREN_PFAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'korrekturen.json')


def lade_korrekturen(pfad: str = KORREKTUREN_PFAD) -> list[dict]:
    """Korrekturen und Absagen für Scraper-Termine (gepflegt von hw_import.py)."""
    try:
        with open(pfad, encoding='utf-8') as f:
            return _json.load(f)
    except (FileNotFoundError, ValueError):
        return []


def wende_korrekturen_an(termine: list[Termin], korrekturen: list[dict], jahr: int, monat: int) -> list[dict]:
    """Wendet freigegebene Korrekturen auf die Termine des Monats an (vor entferne_duplikate()).

    Trifft alle Termine des Tages, deren normalisierter Name gleich ist oder den Namen enthält
    (bzw. darin enthalten ist, siehe korrektur_name_passt()): so wird auch die Dublette eines
    Aggregators mitkorrigiert.
    Datumsänderungen werden nicht angewendet: Eine Verschiebung ("verschoben_auf") markiert den alten Termin,
    den neuen legt hw_import als manuellen Eintrag an.
    Gibt die Korrekturen dieses Monats zurück, die keinen Termin gefunden haben.
    """
    verwaist = []
    for k in korrekturen:
        if not k.get('freigegeben') or not k.get('name_norm'):
            continue
        try:
            tag = datetime.strptime(k['datum'], '%Y-%m-%d').date()
        except (KeyError, ValueError):
            continue
        if (tag.year, tag.month) != (jahr, monat):
            continue
        norm_k = k['name_norm']
        treffer = []
        for t in termine:
            if t.datum.date() == tag and korrektur_name_passt(norm_k, _normalisiere(t.name)):
                treffer.append(t)
        if not treffer:
            verwaist.append(k)
            print(f"  [Korrektur] nicht angewendet, kein Termin gefunden: {k['datum']} {norm_k}")
            continue
        aenderung = k.get('aenderung') or {}
        for t in treffer:
            if k.get('absage'):
                t.abgesagt = True
            if k.get('verschoben_auf'):
                t.abgesagt = True
                t.verschoben_auf = k['verschoben_auf']
            uhrzeit = aenderung.get('uhrzeit', '')
            if re.fullmatch(r'\d{2}:\d{2}', uhrzeit):
                h, m = map(int, uhrzeit.split(':'))
                t.uhrzeit = f"{uhrzeit} Uhr"
                t.datum = t.datum.replace(hour=h, minute=m)
            if aenderung.get('ort'):
                t.ort = aenderung['ort'][:150]
            link = aenderung.get('link', '')
            if re.fullmatch(r'https?://[^\s"\'<>]{3,500}', link):
                t.link = link
    return verwaist


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


# CSS der Monatsseiten (auch für Tages- und Startseite als stil.css)
SEITEN_CSS = r"""        :root {
            --bg-color: #e8e0d8;
            --card-bg: #fcfcfc;
            --text-color: #3b3b3b;
            --text-secondary: #666;
            --border-color: #d8ccbd;
            --accent-color: #d88a2b;
            --accent-light: #343538;
            --hover-color: #f5f0ea;
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --bg-color: #2a2520;
                --card-bg: #3a3530;
                --text-color: #e8e0d8;
                --text-secondary: #a09080;
                --border-color: #4a4035;
                --accent-color: #e8a040;
                --accent-light: #343538;
                --hover-color: #3a3530;
            }
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: "Lucida Grande", Verdana, -apple-system, sans-serif;
            background: var(--bg-color);
            color: var(--text-color);
            line-height: 1.5;
            padding: 20px;
        }

        .container {
            max-width: 1080px;
            margin: 0 auto;
        }

        header {
            text-align: center;
            margin-bottom: 30px;
            position: relative;
        }

        .header-inner {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
        }

        .hebbert {
            width: 360px;
            height: auto;
            opacity: 0.85;
            flex-shrink: 0;
        }

        .hebbert:hover {
            opacity: 1;
        }

        .header-text {
            flex-shrink: 0;
        }

        h1 {
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 6px;
        }

        .header-claim {
            font-size: 0.85rem;
            font-weight: 600;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--accent-color);
            margin-bottom: 10px;
        }

        .nav {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            margin-bottom: 20px;
        }

        .nav-btn {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--accent-color);
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            text-decoration: none;
        }

        .nav-btn:hover {
            background: var(--hover-color);
            color: #00bcff;
        }

        .nav-btn.disabled {
            opacity: 0.3;
            pointer-events: none;
        }

        .monat-titel {
            font-size: 1.2rem;
            font-weight: 500;
        }

        .filter-bar {
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
        }

        @media (prefers-color-scheme: dark) {
            .filter-bar {
                background: rgba(58, 53, 48, 0.5);
            }
        }

        .vhs-toggle {
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: var(--bg-color);
            color: var(--text-color);
            font-size: 14px;
            cursor: pointer;
        }

        .vhs-toggle:hover {
            background: var(--hover-color);
        }

        .vhs-toggle.active {
            background: var(--accent-color);
            color: white;
            border-color: var(--accent-color);
        }

        .filter-bar select {
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: var(--bg-color);
            color: var(--text-color);
            font-size: 14px;
        }

        .stats {
            font-size: 14px;
            color: var(--text-secondary);
        }

        .datum-gruppe {
            margin-bottom: 20px;
        }

        .datum-header {
            font-weight: 600;
            font-size: 1rem;
            padding: 10px 15px;
            background: var(--accent-color);
            color: white;
            border-radius: 10px 10px 0 0;
            margin: 0;
        }

        .termine-liste {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-top: none;
            border-radius: 0 0 10px 10px;
        }

        .termin {
            display: flex;
            padding: 12px 15px;
            border-bottom: 1px solid var(--border-color);
            transition: background 0.2s;
        }

        .termin:last-child {
            border-bottom: none;
        }

        .termin:hover {
            background: var(--hover-color);
        }

        /* Spotlight-Karte (redaktionelle Highlights, z.B. 50 Jahre Holzwurm).
           Goldpalette angelehnt an das Holzwurm-Heftcover. */
        .spotlight-karte {
            margin: 14px;
            border: 2px solid #b8912a;
            border-radius: 12px;
            overflow: hidden;
            background: var(--card-bg);
            box-shadow: 0 3px 12px rgba(184, 145, 42, 0.35);
        }

        .spotlight-kopf {
            position: relative;
            background: linear-gradient(135deg, #c9a227 0%, #a5820f 100%);
            color: #fff;
            padding: 18px 20px;
        }

        .spotlight-hebbert {
            float: right;
            width: 82px;
            height: auto;
            margin-left: 14px;
            background: #fff;
            border: 3px solid #fff;
            border-radius: 8px;
            transform: rotate(3deg);
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
        }

        .spotlight-jahre {
            font-size: 12px;
            letter-spacing: 3px;
            opacity: 0.9;
        }

        .spotlight-titel {
            font-size: 1.5rem;
            font-weight: 700;
            line-height: 1.2;
            margin: 2px 0;
        }

        .spotlight-untertitel {
            font-style: italic;
            font-size: 15px;
            margin-bottom: 8px;
        }

        .spotlight-meta {
            font-size: 13px;
            font-weight: 500;
            opacity: 0.95;
        }

        .spotlight-programm {
            padding: 6px 20px;
        }

        .spotlight-punkt {
            display: flex;
            gap: 14px;
            padding: 10px 0;
            border-bottom: 1px dashed var(--border-color);
        }

        .spotlight-punkt:last-child {
            border-bottom: none;
        }

        .spotlight-zeit {
            width: 52px;
            flex-shrink: 0;
            font-weight: 700;
            color: #a5820f;
            font-size: 14px;
        }

        .spotlight-punkt-info {
            flex: 1;
        }

        .spotlight-name {
            font-weight: 600;
            margin-bottom: 2px;
        }

        .spotlight-beschreibung {
            font-size: 13px;
            color: var(--text-secondary);
        }

        .spotlight-fuss {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 6px 14px;
            padding: 10px 20px;
            font-size: 13px;
            color: var(--text-secondary);
            background: rgba(201, 162, 39, 0.10);
            border-top: 1px solid var(--border-color);
        }

        .spotlight-signatur {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            font-style: italic;
            white-space: nowrap;
        }

        /* multiply blendet den weißen Bildhintergrund in den hellen Fuß ein */
        .spotlight-signatur img {
            height: 26px;
            width: auto;
            mix-blend-mode: multiply;
        }

        .spotlight-fuss a {
            color: #a5820f;
            font-weight: 600;
            text-decoration: none;
        }

        .spotlight-fuss a:hover {
            text-decoration: underline;
        }

        @media (prefers-color-scheme: dark) {
            .spotlight-karte {
                border-color: #d4af37;
                box-shadow: 0 3px 12px rgba(0, 0, 0, 0.4);
            }

            .spotlight-kopf {
                background: linear-gradient(135deg, #8a6d10 0%, #6b540c 100%);
            }

            .spotlight-zeit,
            .spotlight-fuss a {
                color: #d4af37;
            }

            /* invert + screen: Striche werden weiß, der (invertiert schwarze)
               Hintergrund verschwindet auf der dunklen Fläche */
            .spotlight-signatur img {
                filter: invert(1);
                mix-blend-mode: screen;
            }
        }

        @media (max-width: 600px) {
            .spotlight-hebbert {
                width: 60px;
            }
        }

        .termin-zeit {
            width: 110px;
            font-weight: 500;
            color: var(--accent-color);
            flex-shrink: 0;
            font-size: 14px;
        }

        .termin-info {
            flex: 1;
        }

        .termin-name {
            font-weight: 500;
            margin-bottom: 2px;
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }

        .termin-name a {
            color: var(--text-color);
            text-decoration: none;
        }

        .termin-name a:hover {
            color: var(--accent-color);
            text-decoration: underline;
        }

        /* Abgesagt: bleibt sichtbar, Titel und Uhrzeit durchgestrichen */
        .termin[data-abgesagt] .termin-name > a,
        .termin[data-abgesagt] .termin-name > .termin-toggle,
        .termin[data-abgesagt] .termin-zeit {
            text-decoration: line-through;
            opacity: 0.6;
        }

        .badge-abgesagt {
            background: linear-gradient(135deg, #c0392b 0%, #b0291b 100%);
            color: white;
            font-weight: 700;
        }

        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
            white-space: nowrap;
        }

        .badge-regioactive {
            background: linear-gradient(135deg, #d88a2b 0%, #c67a1b 100%);
            color: white;
        }

        .badge-altstadtschmiede {
            background: linear-gradient(135deg, #8B6914 0%, #705210 100%);
            color: white;
        }

        .badge-sternwarte {
            background: linear-gradient(135deg, #343538 0%, #2f3033 100%);
            color: white;
        }

        .badge-kunsthalle {
            background: linear-gradient(135deg, #b05030 0%, #903820 100%);
            color: white;
        }

        .badge-vesterleben {
            background: linear-gradient(135deg, #5a8a3a 0%, #4a7a2a 100%);
            color: white;
        }

        .badge-stadt {
            background: linear-gradient(135deg, #2a7ab5 0%, #1a6a9a 100%);
            color: white;
        }

        .badge-stadtbibliothek {
            background: linear-gradient(135deg, #5a7ab0 0%, #4a6a9a 100%);
            color: white;
        }

        .badge-nlgr {
            background: linear-gradient(135deg, #8a5a8a 0%, #7a4a7a 100%);
            color: white;
        }

        .badge-literaturtage {
            background: linear-gradient(135deg, #a06050 0%, #905040 100%);
            color: white;
        }

        .badge-vhs {
            background: linear-gradient(135deg, #4a8a6a 0%, #3a7a5a 100%);
            color: white;
        }


        .badge-stadtarchiv {
            background: linear-gradient(135deg, #7a7060 0%, #6a6050 100%);
            color: white;
        }

        .badge-geschichte-re {
            background: linear-gradient(135deg, #8a6a40 0%, #7a5a30 100%);
            color: white;
        }

        .badge-gastkirche {
            background: linear-gradient(135deg, #6a8a6a 0%, #5a7a5a 100%);
            color: white;
        }

        .badge-ruhrfestspiele {
            background: linear-gradient(135deg, #c03030 0%, #a02020 100%);
            color: white;
        }

        .badge-backyard {
            background: linear-gradient(135deg, #4a4a4a 0%, #333333 100%);
            color: white;
        }

        .badge-cineworld {
            background: linear-gradient(135deg, #d4391c 0%, #b02010 100%);
            color: white;
        }

        .badge-neue-philharmonie {
            background: linear-gradient(135deg, #1a5276 0%, #154360 100%);
            color: white;
        }

        .badge-ikonen-museum {
            background: linear-gradient(135deg, #7d6608 0%, #6d5600 100%);
            color: white;
        }

        .badge-debut-um-11 {
            background: linear-gradient(135deg, #6c3483 0%, #5b2c6f 100%);
            color: white;
        }

        .badge-adfc {
            background: linear-gradient(135deg, #e2001a 0%, #c0001a 100%);
            color: white;
        }

        .badge-atelierhaus {
            background: linear-gradient(135deg, #7b5ea7 0%, #5e4080 100%);
            color: white;
        }

        .badge-zu-gast-in-re {
            background: linear-gradient(135deg, #1a7a4a 0%, #155f3a 100%);
            color: white;
        }

        .badge-re-leuchtet {
            background: linear-gradient(135deg, #f4a00a 0%, #d4880a 100%);
            color: white;
        }

        .badge-frauenforum {
            background: linear-gradient(135deg, #c0387a 0%, #a02060 100%);
            color: white;
        }
        .badge-josefeich {
            background: linear-gradient(135deg, #8a7050 0%, #7a6040 100%);
            color: white;
        }
        .badge-recklinghaeuser {
            background: linear-gradient(135deg, #b08030 0%, #a07020 100%);
            color: white;
        }
        .badge-subergs {
            background: linear-gradient(135deg, #5a5a7a 0%, #4a4a6a 100%);
            color: white;
        }
        .badge-seniorenbeirat {
            background: linear-gradient(135deg, #8a3a5a 0%, #7a2a4a 100%);
            color: white;
        }
        .badge-zeche-klaerchen {
            background: linear-gradient(135deg, #7a4a30 0%, #6a3a20 100%);
            color: white;
        }
        .badge-stadtlabor {
            background: linear-gradient(135deg, #c06020 0%, #b05010 100%);
            color: white;
        }
        .badge-gegendruck {
            background: linear-gradient(135deg, #8b2252 0%, #6b1242 100%);
            color: white;
        }
        .badge-ev-akademie {
            background: linear-gradient(135deg, #1f6f78 0%, #0f5f68 100%);
            color: white;
        }
        .badge-campus-emscherland {
            background: linear-gradient(135deg, #e0b020 0%, #c09010 100%);
            color: white;
        }
        .badge-ratssitzungen {
            background: linear-gradient(135deg, #1a3a5c 0%, #0a2a4c 100%);
            color: white;
        }
        .badge-moondock {
            background: linear-gradient(135deg, #4a1a6b 0%, #3a0a5b 100%);
            color: white;
        }
        .badge-facebook {
            background: linear-gradient(135deg, #1877F2 0%, #0f65d9 100%);
            color: white;
        }
        .badge-manuell {
            background: linear-gradient(135deg, #2a8a8a 0%, #1a7a7a 100%);
            color: white;
        }
        .badge-agenda21 {
            background: linear-gradient(135deg, #2f7d4f 0%, #1f6a3f 100%);
            color: white;
        }
        .badge-selbsthilfegruppen-re {
            background: linear-gradient(135deg, #c0625a 0%, #a8483f 100%);
            color: white;
        }
        .badge-katholisch-netzwerk {
            background: linear-gradient(135deg, #7a2020 0%, #601818 100%);
            color: white;
        }
        .badge-holzwurm {
            background: linear-gradient(135deg, #9c5a2e 0%, #7c4620 100%);
            color: white;
        }
        .badge-selbsthilfe-kontaktstelle {
            background: linear-gradient(135deg, #d4708a 0%, #b85670 100%);
            color: white;
        }
        .badge-genial-re {
            background: linear-gradient(135deg, #3a9ac0 0%, #2a7fa3 100%);
            color: white;
        }
        .badge-demokratie-werkstadt {
            background: linear-gradient(135deg, #6b8e23 0%, #55731a 100%);
            color: white;
        }
        .badge-attac-re {
            background: linear-gradient(135deg, #cc5500 0%, #a84500 100%);
            color: white;
        }

        .badge-eventim {
            background: linear-gradient(135deg, #3a5a8c 0%, #2a4470 100%);
            color: white;
        }

        .badge-default {
            background: var(--hover-color);
            color: var(--text-secondary);
        }

        .badge-kategorie {
            background: var(--hover-color);
            color: var(--text-secondary);
            border: 1px solid var(--border-color);
        }

        .termin-ort {
            font-size: 13px;
            color: var(--text-secondary);
        }

        .termin-beschreibung {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 4px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .termin-toggle {
            cursor: pointer;
            color: var(--text-color);
            border-bottom: 1px dashed var(--text-secondary);
        }

        .termin-toggle:hover {
            color: var(--accent-color);
        }

        .termin-toggle::after {
            content: ' \25B8';
            font-size: 11px;
            color: var(--text-secondary);
        }

        .termin.expanded .termin-toggle::after {
            content: ' \25BE';
        }

        .termin:has(.termin-toggle) .termin-beschreibung {
            display: none;
        }

        .termin-beschreibung-mehr {
            cursor: pointer;
        }

        .termin-beschreibung-mehr::after {
            content: ' \25B8';
            font-size: 11px;
            color: var(--text-secondary);
        }

        .termin.expanded .termin-beschreibung-mehr::after {
            content: ' \25BE';
        }

        .termin.expanded .termin-beschreibung {
            display: block;
            -webkit-line-clamp: unset;
            overflow: visible;
        }

        .zurueck-link {
            text-align: right;
            padding: 6px 15px;
            font-size: 13px;
        }

        .zurueck-link a {
            color: var(--accent-color);
            text-decoration: none;
            font-weight: 500;
        }

        .keine-termine {
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
        }

        .hidden {
            display: none !important;
        }

        footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            background: #2f3033;
            border-radius: 10px;
            color: #aaa;
            font-size: 12px;
        }

        footer a {
            color: #aaa;
        }

        .kalender {
            width: 100%;
            max-width: 400px;
            margin: 0 auto 25px;
            border-collapse: collapse;
            text-align: center;
        }

        .kalender th {
            padding: 6px;
            font-size: 13px;
            color: var(--text-secondary);
            font-weight: 500;
        }

        .kalender td {
            padding: 6px;
            font-size: 14px;
            border-radius: 6px;
        }

        .kalender .kal-leer {
            color: var(--text-secondary);
            opacity: 0.5;
        }

        .kalender .kal-link {
            display: inline-block;
            width: 32px;
            height: 32px;
            line-height: 32px;
            border-radius: 50%;
            background: var(--accent-color);
            color: white;
            text-decoration: none;
            font-weight: 600;
        }

        .kalender .kal-link:hover {
            opacity: 0.8;
        }

        .kalender .kal-heute {
            outline: 2px solid var(--accent-color);
            outline-offset: -2px;
        }

        .kalender .kal-heute .kal-link {
            box-shadow: 0 0 0 2px white, 0 0 0 4px var(--accent-color);
        }

        .nav-bottom {
            display: flex;
            justify-content: space-between;
            margin: 30px 0 20px;
        }

        @media (max-width: 600px) {
            .termin {
                flex-direction: column;
                gap: 4px;
            }
            .termin-zeit {
                width: auto;
            }
            .hebbert {
                width: 210px;
            }
            .header-inner {
                gap: 10px;
            }
        }"""


BADGE_KLASSEN = {
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
        'campus-emscherland': 'badge-campus-emscherland',
        'ratssitzungen': 'badge-ratssitzungen',
        'moondock': 'badge-moondock',
        'facebook': 'badge-facebook',
        'manuell': 'badge-manuell',
        'agenda21': 'badge-agenda21',
        'selbsthilfegruppen-re': 'badge-selbsthilfegruppen-re',
        'katholisch-netzwerk': 'badge-katholisch-netzwerk',
        'holzwurm': 'badge-holzwurm',
        'selbsthilfe-kontaktstelle': 'badge-selbsthilfe-kontaktstelle',
        'genial-re': 'badge-genial-re',
        'demokratie-werkstadt': 'badge-demokratie-werkstadt',
        'attac-re': 'badge-attac-re',
        'eventim': 'badge-eventim',
}


def _spotlight_html(hl_key: str, punkte: list[Termin]) -> str:
    """Gold-Karte für alle Highlight-Termine eines Tages (Konfiguration in HIGHLIGHTS)."""
    cfg = HIGHLIGHTS[hl_key]
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
    return f'''
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
                    <div class="spotlight-fuss">
                        <span>{cfg['fuss']} · <a href="{cfg['link']}" target="_blank" rel="noopener noreferrer">{cfg['link_label']}</a></span>
                        {f'<span class="spotlight-signatur">{cfg["signatur_text"]} <img src="{cfg["signatur"]}" alt="Hebbert (Unterschrift)" loading="lazy"></span>' if cfg.get('signatur') else ''}
                    </div>
                </div>
            '''



def _termin_html(t: Termin, prefix: str = '') -> str:
    """HTML eines einzelnen Termins (Monats- und Tagesseiten). prefix: Weg zur Wurzel ('../' auf Tagesseiten)."""
    beschreibung_escaped = _html.escape(t.beschreibung)[:1000]

    name_esc = _html.escape(t.name)
    uhrzeit_esc = _html.escape(t.uhrzeit_anzeige())
    ort_esc = _html.escape(t.ort) if t.ort else ''
    link_safe = t.link if t.link and t.link.startswith(('http://', 'https://')) else ''

    # Badge für Quelle
    badge_class = BADGE_KLASSEN.get(t.quelle, 'badge-default')
    quelle_label = QUELLEN.get(t.quelle, t.quelle)
    badge_html = f'<span class="badge {badge_class}">{quelle_label}</span>'
    if t.abgesagt:
        try:
            absage_text = f"Verschoben auf {datetime.strptime(t.verschoben_auf, '%Y-%m-%d'):%d.%m.}"
        except ValueError:
            absage_text = 'Abgesagt'
        badge_html = f'<span class="badge badge-abgesagt">{absage_text}</span> ' + badge_html

    if t.kategorie:
        badge_html += f' <span class="badge badge-kategorie">{_html.escape(t.kategorie)}</span>'

    # Name als Link oder aufklappbar
    if link_safe:
        name_html = f'<a href="{_html.escape(link_safe)}" target="_blank" rel="noopener noreferrer">{name_esc}</a>'
    else:
        name_html = f'<span class="termin-toggle" onclick="this.closest(\'.termin\').classList.toggle(\'expanded\')">{name_esc}</span>'

    # Beschreibung: bei Link-Terminen und langer Beschreibung klickbar aufklappbar
    if beschreibung_escaped and link_safe and len(beschreibung_escaped) > 120:
        beschreibung_html = f'<div class="termin-beschreibung termin-beschreibung-mehr" onclick="this.closest(\'.termin\').classList.toggle(\'expanded\')">{beschreibung_escaped}</div>'
    elif beschreibung_escaped:
        beschreibung_html = f'<div class="termin-beschreibung">{beschreibung_escaped}</div>'
    else:
        beschreibung_html = ''

    return f'''
                <div class="termin" data-quelle="{t.quelle}"{' data-abgesagt="1"' if t.abgesagt else ''}>
                    <div class="termin-zeit">{uhrzeit_esc}</div>
                    <div class="termin-info">
                        <div class="termin-name">
                            {name_html}
                            {badge_html}
                        </div>
                        {f'<div class="termin-ort">{ort_esc}</div>' if ort_esc else ''}
                        {beschreibung_html}
                        {_kalender_link_html(t, prefix)}
                    </div>
                </div>
            '''



def generiere_html(termine: list[Termin], jahr: int, monat: int,
                   verfuegbare_monate: list[tuple[int, int]],
                   dateiname: str = "", tracking: bool = True) -> str:
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
            <h2 class="datum-header"><a href="{tagesseite_pfad(tage[0].datum.date())}">{datum_formatiert}</a></h2>
            <div class="termine-liste">
        '''

        # Spotlight-Karten: alle Highlight-Termine des Tages mit gleichem Key
        # werden zu einer Gold-Karte gebündelt (Konfiguration in HIGHLIGHTS)
        spotlight_keys = []
        for t in tage:
            if t.highlight in HIGHLIGHTS and t.highlight not in spotlight_keys:
                spotlight_keys.append(t.highlight)
        for hl_key in spotlight_keys:
            punkte = sorted((t for t in tage if t.highlight == hl_key), key=lambda x: x.uhrzeit)
            termine_html += _spotlight_html(hl_key, punkte)

        normale_termine = [t for t in tage if t.highlight not in HIGHLIGHTS]
        for t in sorted(normale_termine, key=termin_sortierung):
            termine_html += _termin_html(t)

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
    anzahl_ohne_kino = sum(1 for t in termine if not ist_kino(t))
    beschreibung_meta = (f"Veranstaltungskalender Recklinghausen im {monatsnamen[monat]} {jahr}: {anzahl_ohne_kino} Termine "
                         f"aus {len(SCRAPER)} Quellen, dazu das Kinoprogramm. Konzerte, Theater, Vorträge, Führungen, Politik und mehr.")
    titel = f"Veranstaltungen in Recklinghausen im {monatsnamen[monat]} {jahr} - Veranstaltungskalender | Holzwurm"

    # JSON-LD: Monatsseite verweist auf die Tagesseiten; die Events selbst (mit Status, Zeitzone,
    # Adresse) stehen dort. Alle Events hier würden die ohnehin lange Seite um >100 KB verlängern.
    tage_ld = [{
        "@type": "ListItem",
        "position": i + 1,
        "name": f"Veranstaltungen in Recklinghausen am {datum_lang(d)}",
        "url": f"{BASIS_URL}/{tagesseite_pfad(d)}",
    } for i, d in enumerate(sorted({t.datum.date() for t in termine}))]
    jsonld = _json.dumps({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"Veranstaltungskalender Recklinghausen - {monatsnamen[monat]} {jahr}",
        "description": beschreibung_meta,
        "url": canonical_url,
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(tage_ld),
            "itemListElement": tage_ld
        }
    }, ensure_ascii=False)
    # Gescrapte Texte dürfen den <script>-Block nicht beenden ("</script>" im Titel)
    jsonld = jsonld.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')

    html = f'''<!DOCTYPE html>
<html lang="de">
<head>
    {_UMAMI if tracking else ''}
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
{SEITEN_CSS}{ZUSATZ_CSS}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-inner">
                <img src="hebbert/1984-01-verkleinert.jpg" alt="Hebbert in Aktion" class="hebbert" width="604" height="280" decoding="async">
                <div class="header-text">
                    <h1>Termine und Veranstaltungen in Recklinghausen</h1>
                    <p class="header-claim">Veranstaltungskalender &middot; powered by HOLZWURM</p>
                </div>
                <img src="hebbert/1985-04-verkleinert.jpg" alt="Hebbert's Terminkalender" class="hebbert" width="351" height="276" decoding="async">
            </div>
            <nav class="nav" aria-label="Monatsnavigation">
                <a href="{prev_link}" class="nav-btn{prev_class}">&larr; {monatsnamen[prev_monat]}</a>
                <span class="monat-titel">{monatsnamen[monat]} {jahr}</span>
                <a href="{next_link}" class="nav-btn{next_class}">{monatsnamen[next_monat]} &rarr;</a>
            </nav>
            {_schnellnav('')}
        </header>

        {kalender_html}

        <div class="filter-bar">
            <select id="quelle-filter" onchange="filterTermine()">
                {quellen_filter}
            </select>
            <button id="vhs-toggle" class="vhs-toggle" onclick="toggleVHS()">VHS ausblenden</button>
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

        // Kino ist beim Seitenaufruf ausgeblendet, VHS seit 13.10.2026 sichtbar
        // (meist Einzelveranstaltungen; Kurse sind als „Kurs“ gekennzeichnet)
        let vhsAusgeblendet = false;
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


# ---------------------------------------------------------------------------
# Auffindbarkeit: Tagesseiten, Startseite, iCal-Feed, llms.txt
# (Plan 13.10.2026: Suchmaschinen und KI-Assistenten lesen Seiten, keine Sprungmarken)
# ---------------------------------------------------------------------------

BASIS_URL = "https://termine.holzwurm-recklinghausen.de"
_ZEITZONE = ZoneInfo('Europe/Berlin')
_WOCHENTAGE = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
_MONATE = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
           'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
_UMAMI = '<script defer src="https://cloud.umami.is/script.js" data-website-id="14825bec-c437-48e5-af55-02f181fdb17c"></script>'
_KINO_URL = dict(FOOTER_QUELLEN).get('Cineworld', '')

# Ergänzungen zum Monats-CSS: Schnellnavigation, Tagesseiten-Links, Kino-Zeile
ZUSATZ_CSS = r"""
        .schnellnav {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 8px 18px;
            margin: -6px 0 18px;
            font-size: 0.9rem;
        }
        .schnellnav a { color: var(--accent-color); text-decoration: none; }
        .schnellnav a:hover { text-decoration: underline; }
        .datum-header a { color: inherit; text-decoration: none; }
        .datum-header a:hover { color: var(--accent-color); }
        /* längstes Wort der Überschrift nie brechen, stattdessen schrumpfen die Bilder (Rückmeldung Ralf) */
        .kopf-neu .header-text { flex-shrink: 1; min-width: min-content; }
        .kopf-neu .hebbert { flex-shrink: 1; min-width: 0; }
        .nav-unten { margin: 24px 0 0; }
        .start-abschnitt > h2 a { color: inherit; text-decoration: none; }
        .start-abschnitt > h2 a::after { content: " \2192"; color: var(--accent-color); }
        .start-abschnitt > h2 a:hover { color: var(--accent-color); }
        h1.h1-lang { font-size: 1.6rem; }
        a.monat-titel { color: var(--accent-color); text-decoration: none; }
        a.monat-titel:hover { text-decoration: underline; }
        .tag-intro { margin: 0 0 16px; color: var(--text-secondary); }
        .termin-aktionen { margin-top: 6px; font-size: 0.8rem; }
        .termin-kalender { color: var(--accent-color); text-decoration: none; }
        .termin-kalender::before { content: "+ "; }
        .termin-kalender:hover { text-decoration: underline; }
        .tag-intro a { color: var(--accent-color); }
        .kino-zeile {
            margin: 12px 0 0;
            padding: 12px 15px;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            font-size: 0.9rem;
            color: var(--text-secondary);
        }
        .kino-zeile a { color: var(--accent-color); }
        .start-abschnitt { margin-bottom: 28px; }
        .start-abschnitt > h2 { font-size: 1.3rem; margin: 0 0 12px; }
        .tagesliste { list-style: none; padding: 0; margin: 0; display: grid;
                      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 8px; }
        .tagesliste a { display: block; padding: 10px 14px; background: var(--card-bg);
                        border: 1px solid var(--border-color); border-radius: 8px;
                        color: var(--text-color); text-decoration: none; }
        .tagesliste a:hover { background: var(--hover-color); color: var(--accent-color); }
        .tagesliste .anzahl { color: var(--text-secondary); font-size: 0.85rem; }
        .veraltet-hinweis { padding: 10px 15px; margin-bottom: 16px; border-radius: 8px;
                            background: var(--card-bg); border: 1px solid var(--accent-color); }
        .veraltet-hinweis[hidden] { display: none; }
        @media (max-width: 600px) {
            .header-inner { flex-wrap: wrap; }
            .header-text { order: -1; flex-basis: 100%; }
            .hebbert { width: calc(50% - 5px); }
            h1, h1.h1-lang { font-size: 1.45rem; }
        }
"""


def ist_kino(t: Termin) -> bool:
    return t.quelle == 'cineworld'


def datum_lang(d) -> str:
    """'Dienstag, 13. Oktober 2026'"""
    return f"{_WOCHENTAGE[d.weekday()]}, {d.day}. {_MONATE[d.month]} {d.year}"


def tagesseite_pfad(d) -> str:
    return f"tag/{d.isoformat()}.html"


_ZEIT_TOKEN = re.compile(r'(?<![\d.:])(\d{1,2})(?:[:.](\d{2}))?(?![\d])')


def zeitspanne(uhrzeit: str) -> tuple[str | None, str | None]:
    """Beginn und Ende als 'HH:MM' aus Freitext wie '19:30–21:00 Uhr', 'von 9:30 bis 12 Uhr'.
    Mehrere Vorstellungen ('14:00 / 19:30 Uhr') -> nur Beginn der ersten, kein Ende."""
    if not uhrzeit or uhrzeit in ('ganztägig', 'siehe Website'):
        return None, None
    text = uhrzeit.replace('\xa0', ' ')
    mehrere = '/' in text
    zeiten = []
    for m in _ZEIT_TOKEN.finditer(text):
        h, mi = int(m.group(1)), int(m.group(2) or 0)
        if h > 23 or mi > 59:
            continue
        zeiten.append(f"{h:02d}:{mi:02d}")
    if not zeiten:
        return None, None
    if mehrere or len(zeiten) < 2:
        return zeiten[0], None
    if zeiten[1] <= zeiten[0]:
        return zeiten[0], None
    return zeiten[0], zeiten[1]


def _iso_mit_zone(tag, hhmm: str) -> str:
    h, m = map(int, hhmm.split(':'))
    dt = datetime(tag.year, tag.month, tag.day, h, m, tzinfo=_ZEITZONE)
    return dt.isoformat()


_STRASSE = re.compile(
    r"([A-ZÄÖÜ][\wÄÖÜäöüß.\-]*(?:[ \-][\wÄÖÜäöüß.\-]+)*?"
    r"(?:straße|strasse|str\.|weg|platz|gasse|allee|ring|wall|damm|markt|hof)\s*\d+\s*[a-zA-Z]?)\b")
_PLZ = re.compile(r'\b(4\d{4})\b')
_EINTRITT_FREI = re.compile(r'eintritt\s+(?:ist\s+)?frei|freier\s+eintritt', re.IGNORECASE)


def event_jsonld(t: Termin, mit_beschreibung: bool = True) -> dict:
    """schema.org Event mit Zeitzone, Status und Adresse (soweit aus den Daten ablesbar)."""
    tag = t.datum.date()
    beginn, ende = zeitspanne(t.uhrzeit)
    adresse = {"@type": "PostalAddress", "addressLocality": "Recklinghausen", "addressCountry": "DE"}
    if t.ort:
        strasse = _STRASSE.search(t.ort)
        if strasse:
            adresse["streetAddress"] = strasse.group(1).strip()
        plz = _PLZ.search(t.ort)
        if plz:
            adresse["postalCode"] = plz.group(1)
    obj = {
        "@type": "Event",
        "name": t.name,
        "startDate": _iso_mit_zone(tag, beginn) if beginn else tag.isoformat(),
        "eventStatus": "https://schema.org/EventCancelled" if t.abgesagt else "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": {"@type": "Place", "name": t.ort or "Recklinghausen", "address": adresse},
    }
    if t.verschoben_auf:
        # schema.org: startDate ist der neue Tag, previousStartDate der alte (sonst meldet eine KI „fällt aus“)
        obj["eventStatus"] = "https://schema.org/EventRescheduled"
        obj["previousStartDate"] = obj["startDate"]
        obj["startDate"] = t.verschoben_auf
    if ende:
        obj["endDate"] = _iso_mit_zone(tag, ende)
    if t.link and t.link.startswith(('http://', 'https://')):
        obj["url"] = t.link
    if mit_beschreibung and t.beschreibung:
        obj["description"] = t.beschreibung[:300]
    if _EINTRITT_FREI.search(t.beschreibung or ''):
        obj["isAccessibleForFree"] = True
    return obj


def _jsonld_script(obj) -> str:
    ld = _json.dumps(obj, ensure_ascii=False)
    # Gescrapte Texte dürfen den <script>-Block nicht beenden
    ld = ld.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    return f'<script type="application/ld+json">{ld}</script>'


def termin_sortierung(t: Termin) -> tuple:
    """Nach Beginn sortieren ('9:00' vor '19.30'); ganztägig und 'siehe Website' ans Ende."""
    beginn, _ = zeitspanne(t.uhrzeit)
    return (beginn is None, t.uhrzeit == 'siehe Website', beginn or '', t.uhrzeit, t.name)


def _sortierte_termine(termine: list[Termin]) -> list[Termin]:
    return sorted(termine, key=termin_sortierung)


def _schnellnav(prefix: str) -> str:
    return (f'<nav class="schnellnav" aria-label="Schnellzugriff">'
            f'<a href="{prefix}heute.html">Heute</a>'
            f'<a href="{prefix}morgen.html">Morgen</a>'
            f'<a href="{prefix}wochenende.html">Wochenende</a>'
            f'<a href="{prefix}index.html">Startseite</a>'
            f'</nav>')


def _kino_zeile(kino: list[Termin], einleitung: str) -> str:
    if not kino:
        return ''
    filme = sorted({t.name for t in kino}, key=str.lower)
    link = f' <a href="{_KINO_URL}" target="_blank" rel="noopener noreferrer">Programm und Tickets</a>' if _KINO_URL else ''
    return (f'<div class="kino-zeile"><strong>Kino:</strong> {einleitung} {len(filme)} '
            f'{"Film" if len(filme) == 1 else "Filme"}: {_html.escape(", ".join(filme))}.{link}</div>')


def _tag_block(tag, termine: list[Termin], prefix: str, ueberschrift_link: bool = False) -> str:
    """Termine eines Tages ohne Kino, im Markup der Monatsseiten (Spotlight-Karten inklusive)."""
    key = tag.isoformat()
    titel = _html.escape(datum_lang(tag))
    if ueberschrift_link:
        titel = f'<a href="{prefix}{tagesseite_pfad(tag)}">{titel}</a>'
    teile = [f'<div class="datum-gruppe" id="datum-{key}">',
             f'<h2 class="datum-header">{titel}</h2>', '<div class="termine-liste">']
    spotlight_keys = []
    for t in termine:
        if t.highlight in HIGHLIGHTS and t.highlight not in spotlight_keys:
            spotlight_keys.append(t.highlight)
    for hl_key in spotlight_keys:
        punkte = sorted((t for t in termine if t.highlight == hl_key), key=lambda x: x.uhrzeit)
        teile.append(_spotlight_html(hl_key, punkte).replace('src="hebbert/', f'src="{prefix}hebbert/'))
    normale = [t for t in termine if t.highlight not in HIGHLIGHTS and not ist_kino(t)]
    for t in _sortierte_termine(normale):
        teile.append(_termin_html(t, prefix))
    if not normale and not spotlight_keys:
        teile.append('<div class="keine-termine">Für diesen Tag sind noch keine Termine bekannt.</div>')
    teile.append('</div>')
    kino = [t for t in termine if ist_kino(t)]
    teile.append(_kino_zeile(kino, 'Das Cineworld zeigt an diesem Tag'))
    teile.append('</div>')
    return '\n'.join(teile)


def _seitenrahmen(*, titel: str, beschreibung: str, canonical: str, jsonld: str, h1: str,
                  claim: str, nav_html: str, inhalt: str, prefix: str, tracking: bool,
                  script: str = '', robots: str = 'index, follow') -> str:
    footer_links = ' &middot;\n            '.join(
        f'<a href="{url}" target="_blank" rel="noopener noreferrer">{_html.escape(name)}</a>'
        for name, url in sorted(FOOTER_QUELLEN, key=lambda x: x[0].lower())
    )
    titel_esc = _html.escape(titel)
    besch_esc = _html.escape(beschreibung)
    return f'''<!DOCTYPE html>
<html lang="de">
<head>
    {_UMAMI if tracking else ''}
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titel_esc}</title>
    <meta name="description" content="{besch_esc}"/>
    <meta name="robots" content="{robots}, max-snippet:-1, max-image-preview:large"/>
    <link rel="canonical" href="{canonical}" />
    <link rel="icon" type="image/x-icon" href="{prefix}favicon.ico">
    <link rel="icon" type="image/webp" href="{prefix}favicon-96x96-1.webp">
    <meta property="og:locale" content="de_DE" />
    <meta property="og:type" content="website" />
    <meta property="og:title" content="{titel_esc}" />
    <meta property="og:description" content="{besch_esc}" />
    <meta property="og:url" content="{canonical}" />
    <meta property="og:site_name" content="Holzwurm Recklinghausen" />
    <meta property="og:image" content="{BASIS_URL}/og-image.png" />
    {jsonld}
    <link rel="stylesheet" href="{prefix}stil.css">
</head>
<body>
    <div class="container">
        <header class="kopf-neu">
            <div class="header-inner">
                <img src="{prefix}hebbert/1984-01-verkleinert.jpg" alt="Hebbert in Aktion" class="hebbert" width="604" height="280" decoding="async">
                <div class="header-text">
                    <h1{' class="h1-lang"' if len(h1) > 40 else ''}>{_html.escape(h1)}</h1>
                    <p class="header-claim">{claim}</p>
                </div>
                <img src="{prefix}hebbert/1985-04-verkleinert.jpg" alt="Hebbert's Terminkalender" class="hebbert" width="351" height="276" decoding="async">
            </div>
            {nav_html}
            {_schnellnav(prefix)}
        </header>

        <main id="termine-container">
{inhalt}
        </main>

        <footer>
            Der Veranstaltungskalender des <a href="https://holzwurm-recklinghausen.de" target="_blank" rel="noopener noreferrer">Holzwurm</a>,
            der Zeitschrift für Recklinghausen seit 1976. Die Termine werden täglich automatisch aus den Quellen gesammelt.
            Maßgeblich sind die Angaben der Veranstalter.<br><br>
            Quellen:
            {footer_links}
            <br><br>
            <a href="https://holzwurm-recklinghausen.de/impressum" target="_blank" rel="noopener noreferrer">Impressum</a> &middot;
            <a href="https://holzwurm-recklinghausen.de/datenschutzerklaerung" target="_blank" rel="noopener noreferrer">Datenschutzerklärung</a>
        </footer>
    </div>
    {script}
</body>
</html>
'''


def _sammel_jsonld(name: str, url: str, termine: list[Termin]) -> str:
    events = [event_jsonld(t) for t in _sortierte_termine(termine) if not ist_kino(t)]
    return _jsonld_script({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": name,
        "url": url,
        "isPartOf": {"@type": "WebSite", "name": "Veranstaltungskalender Recklinghausen (Holzwurm)", "url": f"{BASIS_URL}/"},
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(events), "itemListElement": events},
    })


def _anzahl_text(termine: list[Termin]) -> str:
    n = sum(1 for t in termine if not ist_kino(t))
    kino = any(ist_kino(t) for t in termine)
    text = f"{n} {'Termin' if n == 1 else 'Termine'}"
    return text + (", dazu das Kinoprogramm" if kino else "")


def _beschreibung_tag(tag, termine: list[Termin]) -> str:
    namen = [t.name for t in _sortierte_termine([t for t in termine if not ist_kino(t)])][:3]
    text = f"Veranstaltungen in Recklinghausen am {datum_lang(tag)}: {_anzahl_text(termine)}."
    if namen:
        text += " Unter anderem: " + "; ".join(namen) + "."
    return text[:300]


def _weiterleitung_script(ziel_tag, versatz_tage: int, erster, letzter, nur_wenn_nach=None) -> str:
    """Seite wurde morgens gebaut; ist sie veraltet (z. B. nach Mitternacht), zur passenden Tagesseite springen."""
    bedingung = f"k > '{nur_wenn_nach.isoformat()}'" if nur_wenn_nach else f"k !== '{ziel_tag.isoformat()}'"
    return f'''<script>
        (function() {{
            const d = new Date();
            d.setDate(d.getDate() + {versatz_tage});
            const p = n => String(n).padStart(2, '0');
            const k = d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
            if ({bedingung} && k >= '{erster.isoformat()}' && k <= '{letzter.isoformat()}') {{
                window.location.replace('tag/' + k + '.html');
            }}
        }})();
    </script>'''


def generiere_tagesseite(tag, termine: list[Termin], erster, letzter, *, art: str = 'tag',
                         tracking: bool = True) -> str:
    """Seite für einen Tag. art: 'tag' (tag/JJJJ-MM-TT.html), 'heute' oder 'morgen' (Wurzel)."""
    from datetime import timedelta
    prefix = '../' if art == 'tag' else ''
    datum_text = datum_lang(tag)
    if art == 'heute':
        titel = f"Was ist heute los in Recklinghausen? Veranstaltungen am {datum_text} | Holzwurm"
        h1 = "Heute in Recklinghausen"
        canonical = f"{BASIS_URL}/heute.html"
        script = _weiterleitung_script(tag, 0, erster, letzter)
    elif art == 'morgen':
        titel = f"Was ist morgen los in Recklinghausen? Veranstaltungen am {datum_text} | Holzwurm"
        h1 = "Morgen in Recklinghausen"
        canonical = f"{BASIS_URL}/morgen.html"
        script = _weiterleitung_script(tag, 1, erster, letzter)
    else:
        titel = f"Veranstaltungen in Recklinghausen am {datum_text} | Holzwurm"
        h1 = f"Veranstaltungen in Recklinghausen am {datum_text}"
        canonical = f"{BASIS_URL}/{tagesseite_pfad(tag)}"
        script = ''

    vortag, folgetag = tag - timedelta(days=1), tag + timedelta(days=1)
    tag_prefix = '' if art == 'tag' else 'tag/'

    def tag_link(d, text):
        if erster <= d <= letzter:
            return f'<a href="{tag_prefix}{d.isoformat()}.html" class="nav-btn">{text}</a>'
        return f'<a href="#" class="nav-btn disabled">{text}</a>'

    monat_datei = dateiname_fuer_monat(tag.year, tag.month)
    nav_html = f'''<nav class="nav" aria-label="Tagesnavigation">
                {tag_link(vortag, f"&larr; {_WOCHENTAGE[vortag.weekday()][:2]} {vortag.day}.{vortag.month}.")}
                <a href="{prefix}{monat_datei}#datum-{tag.isoformat()}" class="monat-titel">{_MONATE[tag.month]} {tag.year}</a>
                {tag_link(folgetag, f"{_WOCHENTAGE[folgetag.weekday()][:2]} {folgetag.day}.{folgetag.month}. &rarr;")}
            </nav>'''
    verb = 'steht' if sum(1 for t in termine if not ist_kino(t)) == 1 else 'stehen'
    intro = (f'<p class="tag-intro">Am {_html.escape(datum_text)} {verb} {_html.escape(_anzahl_text(termine))} im Kalender. '
             f'Alle Termine des Monats stehen im <a href="{prefix}{monat_datei}#datum-{tag.isoformat()}">Monatskalender</a>.</p>')
    # Navigation auch am Seitenende (Rückmeldung Erich): wer unten ankommt, blättert direkt weiter
    nav_unten = nav_html.replace('<nav class="nav" aria-label="Tagesnavigation">',
                                 '<nav class="nav nav-unten" aria-label="Tagesnavigation unten">', 1)
    inhalt = intro + '\n' + _tag_block(tag, termine, prefix) + '\n' + nav_unten
    claim = "Veranstaltungskalender Recklinghausen &middot; powered by HOLZWURM"
    if art != 'tag':
        claim = f"{_html.escape(datum_text)} &middot; powered by HOLZWURM"
    return _seitenrahmen(
        titel=titel, beschreibung=_beschreibung_tag(tag, termine), canonical=canonical,
        jsonld=_sammel_jsonld(f"Veranstaltungen in Recklinghausen am {datum_text}", canonical, termine),
        h1=h1, claim=claim, nav_html=nav_html, inhalt=inhalt, prefix=prefix, tracking=tracking, script=script)


def wochenend_tage(heute) -> list:
    """Freitag bis Sonntag des laufenden (ab Freitag) bzw. nächsten Wochenendes, ohne vergangene Tage."""
    from datetime import timedelta
    wt = heute.weekday()
    if wt <= 3:
        freitag = heute + timedelta(days=4 - wt)
        return [freitag + timedelta(days=i) for i in range(3)]
    return [heute + timedelta(days=i) for i in range(7 - wt)]


def generiere_wochenendseite(tage: list, termine_nach_tag: dict, erster, letzter, *, tracking: bool = True) -> str:
    alle = [t for d in tage for t in termine_nach_tag.get(d, [])]
    von, bis = tage[0], tage[-1]
    zeitraum = f"{datum_lang(von)} bis {datum_lang(bis)}" if von != bis else datum_lang(von)
    titel = f"Was ist am Wochenende los in Recklinghausen? Veranstaltungen {von.day}. bis {bis.day}. {_MONATE[bis.month]} {bis.year} | Holzwurm"
    canonical = f"{BASIS_URL}/wochenende.html"
    bloecke = '\n'.join(_tag_block(d, termine_nach_tag.get(d, []), '', ueberschrift_link=True) for d in tage)
    intro = f'<p class="tag-intro">{_html.escape(_anzahl_text(alle))} in Recklinghausen von {_html.escape(zeitraum)}.</p>'
    namen = [t.name for t in _sortierte_termine([t for t in alle if not ist_kino(t)])][:3]
    beschreibung = f"Veranstaltungen in Recklinghausen am Wochenende ({zeitraum}): {_anzahl_text(alle)}."
    if namen:
        beschreibung += " Unter anderem: " + "; ".join(namen) + "."
    return _seitenrahmen(
        titel=titel, beschreibung=beschreibung[:300], canonical=canonical,
        jsonld=_sammel_jsonld(f"Veranstaltungen in Recklinghausen am Wochenende ({zeitraum})", canonical, alle),
        h1="Am Wochenende in Recklinghausen", claim=f"{_html.escape(zeitraum)} &middot; powered by HOLZWURM",
        nav_html='', inhalt=intro + '\n' + bloecke, prefix='', tracking=tracking,
        script=_weiterleitung_script(von, 0, erster, letzter, nur_wenn_nach=bis))


def generiere_startseite(heute, termine_nach_tag: dict, monate: list[tuple[int, int]], erster, letzter,
                         *, tracking: bool = True) -> str:
    from datetime import timedelta
    morgen = heute + timedelta(days=1)
    abschnitte = []
    for d, wort in ((heute, 'Heute'), (morgen, 'Morgen')):
        if erster <= d <= letzter:
            termine = termine_nach_tag.get(d, [])
            abschnitte.append(
                f'<section class="start-abschnitt"><h2><a href="{tagesseite_pfad(d)}">{wort}, {_html.escape(datum_lang(d))}</a></h2>\n'
                f'<p class="tag-intro">{_html.escape(_anzahl_text(termine))}.</p>\n'
                f'{_tag_block(d, termine, "").replace(chr(10) + "<h2 class=" + chr(34) + "datum-header", chr(10) + "<h2 hidden class=" + chr(34) + "datum-header", 1)}</section>')
    naechste = []
    for i in range(2, 9):
        d = heute + timedelta(days=i)
        if d > letzter:
            break
        termine = termine_nach_tag.get(d, [])
        naechste.append(f'<li><a href="{tagesseite_pfad(d)}">{_html.escape(datum_lang(d))}<br>'
                        f'<span class="anzahl">{_html.escape(_anzahl_text(termine))}</span></a></li>')
    if naechste:
        abschnitte.append('<section class="start-abschnitt"><h2>Die nächsten Tage</h2>\n'
                          f'<ul class="tagesliste">{"".join(naechste)}</ul></section>')
    monat_links = []
    for j, m in monate:
        n = sum(1 for d, ts in termine_nach_tag.items() if d.year == j and d.month == m for t in ts if not ist_kino(t))
        monat_links.append(f'<li><a href="{dateiname_fuer_monat(j, m)}">{_MONATE[m]} {j}<br>'
                           f'<span class="anzahl">{n} Termine, dazu Kino</span></a></li>')
    abschnitte.append('<section class="start-abschnitt"><h2>Monatskalender</h2>\n'
                      f'<ul class="tagesliste">{"".join(monat_links)}</ul></section>')
    abschnitte.append(
        '<section class="start-abschnitt"><h2>Termine ins Handy</h2>\n'
        '<p class="tag-intro">Bei jedem Termin steht „In meinen Kalender". Ein Tipp darauf übernimmt genau diesen '
        'Termin mit Uhrzeit, Ort und Link in den Kalender von Handy oder Computer.</p></section>')

    canonical = f"{BASIS_URL}/"
    beschreibung = (f"Was ist los in Recklinghausen? Der Veranstaltungskalender des Holzwurm sammelt täglich Termine "
                    f"aus {len(SCRAPER)} Quellen: Konzerte, Theater, Kino, Vorträge, Führungen, Märkte, Politik und mehr.")
    heute_termine = termine_nach_tag.get(heute, []) + termine_nach_tag.get(morgen, [])
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "name": "Veranstaltungskalender Recklinghausen (Holzwurm)", "url": canonical,
             "inLanguage": "de",
             "publisher": {"@type": "Organization", "name": "Holzwurm - Zeitschrift für Recklinghausen",
                           "url": "https://holzwurm-recklinghausen.de"}},
            {"@type": "ItemList", "name": "Veranstaltungen in Recklinghausen heute und morgen",
             "itemListElement": [event_jsonld(t) for t in _sortierte_termine(heute_termine) if not ist_kino(t)]},
        ],
    }
    hinweis = (f'<div class="veraltet-hinweis" id="veraltet" hidden>Diese Übersicht ist vom {heute.day}.{heute.month}. '
               f'<a href="#" id="veraltet-link">Zu den Terminen von heute</a></div>')
    script = f'''<script>
        (function() {{
            const d = new Date();
            const p = n => String(n).padStart(2, '0');
            const k = d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
            if (k !== '{heute.isoformat()}' && k <= '{letzter.isoformat()}') {{
                document.getElementById('veraltet-link').href = 'tag/' + k + '.html';
                document.getElementById('veraltet').hidden = false;
            }}
        }})();
    </script>'''
    return _seitenrahmen(
        titel="Veranstaltungskalender Recklinghausen - Termine heute, morgen und am Wochenende | Holzwurm",
        beschreibung=beschreibung, canonical=canonical, jsonld=_jsonld_script(ld),
        h1="Veranstaltungskalender Recklinghausen",
        claim=f"Täglich aktualisiert aus {len(SCRAPER)} Quellen &middot; powered by HOLZWURM",
        nav_html='', inhalt=hinweis + '\n' + '\n'.join(abschnitte), prefix='', tracking=tracking, script=script)


# --- iCal ---------------------------------------------------------------------

_VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/Berlin
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE"""


def _ics_text(wert: str) -> str:
    return (wert.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,')
            .replace('\r\n', '\\n').replace('\r', '\\n').replace('\n', '\\n'))


def _ics_falten(zeile: str) -> str:
    """Zeilen nach RFC 5545 auf 75 Oktette falten (ohne UTF-8-Zeichen zu zerteilen)."""
    teile, aktuell, laenge = [], '', 0
    for zeichen in zeile:
        b = len(zeichen.encode('utf-8'))
        grenze = 75 if not teile else 74
        if laenge + b > grenze:
            teile.append(aktuell)
            aktuell, laenge = '', 0
        aktuell += zeichen
        laenge += b
    teile.append(aktuell)
    return '\r\n '.join(teile)


_ICS_URL = re.compile(r'https?://[^\s"<>\\\x00-\x1f\x7f]{3,2000}')


def termin_uid(t: Termin) -> str:
    """Stabile Kennung aus Datum, normalisiertem Titel und Quelle (Dateiname und iCal-UID)."""
    import hashlib
    schluessel = f"{t.datum.date().isoformat()}|{_normalisiere(t.name)}|{t.quelle}"
    return hashlib.sha1(schluessel.encode()).hexdigest()[:20]


def hat_kalender_link(t: Termin) -> bool:
    return not ist_kino(t) and not t.abgesagt


def _kalender_link_html(t: Termin, prefix: str = '') -> str:
    if not hat_kalender_link(t):
        return ''
    return (f'<div class="termin-aktionen"><a class="termin-kalender" href="{prefix}kalender/{termin_uid(t)}.ics" '
            f'rel="nofollow" title="Diesen Termin in den eigenen Kalender übernehmen">In meinen Kalender</a></div>')


def generiere_termin_ics(t: Termin) -> str:
    """iCal-Datei für genau einen Termin ("In meinen Kalender").
    DTSTAMP hängt am Termindatum statt an der Uhrzeit des Laufs, damit unveränderte Dateien gleich bleiben."""
    from datetime import timedelta
    tag = t.datum.date()
    beginn, ende = zeitspanne(t.uhrzeit)
    zeilen = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Holzwurm Recklinghausen//Veranstaltungskalender//DE',
              'CALSCALE:GREGORIAN', 'METHOD:PUBLISH'] + _VTIMEZONE.split('\n')
    ev = ['BEGIN:VEVENT', f'UID:{termin_uid(t)}@termine.holzwurm-recklinghausen.de',
          f'DTSTAMP:{tag.strftime("%Y%m%d")}T000000Z']
    if beginn:
        ev.append(f'DTSTART;TZID=Europe/Berlin:{tag.strftime("%Y%m%d")}T{beginn.replace(":", "")}00')
        if ende:
            ev.append(f'DTEND;TZID=Europe/Berlin:{tag.strftime("%Y%m%d")}T{ende.replace(":", "")}00')
    else:
        ev.append(f'DTSTART;VALUE=DATE:{tag.strftime("%Y%m%d")}')
        ev.append(f'DTEND;VALUE=DATE:{(tag + timedelta(days=1)).strftime("%Y%m%d")}')
    ev.append(f'SUMMARY:{_ics_text(t.name)}')
    if t.ort:
        ev.append(f'LOCATION:{_ics_text(t.ort)}')
    beschreibung = t.beschreibung[:500] if t.beschreibung else ''
    if t.uhrzeit and not beginn:
        beschreibung = f"Uhrzeit: {t.uhrzeit}\n{beschreibung}".strip()
    quelle = QUELLEN.get(t.quelle, t.quelle)
    beschreibung = f"{beschreibung}\n\nQuelle: {quelle}, über den Veranstaltungskalender des Holzwurm".strip()
    ev.append(f'DESCRIPTION:{_ics_text(beschreibung)}')
    # Gescrapter Link: nur ohne Leer- und Steuerzeichen, sonst ließen sich iCal-Zeilen einschleusen
    if t.link and _ICS_URL.fullmatch(t.link):
        ev.append(f'URL:{t.link}')
    ev.append('END:VEVENT')
    zeilen += ev + ['END:VCALENDAR']
    return '\r\n'.join(_ics_falten(z) for z in zeilen) + '\r\n'


def generiere_llms_txt(monate: list[tuple[int, int]]) -> str:
    monat_zeilen = '\n'.join(f"- [{_MONATE[m]} {j}]({BASIS_URL}/{dateiname_fuer_monat(j, m)}): alle Termine des Monats inklusive Kino"
                             for j, m in monate)
    return f"""# Veranstaltungskalender Recklinghausen (Holzwurm)

> Täglich aktualisierter Veranstaltungskalender für Recklinghausen. Herausgeber ist der Holzwurm, die Zeitschrift für Recklinghausen (seit 1976). Die Termine werden automatisch aus {len(SCRAPER)} Quellen gesammelt (Stadt, VHS, Kulturorte, Vereine, Kirchen, Ratsinformationssystem, Kino) und redaktionell ergänzt. Maßgeblich sind die Angaben der Veranstalter, jeder Termin verlinkt auf seine Quelle.

Jede Seite enthält die Termine zusätzlich als schema.org-Event in JSON-LD (Beginn mit Zeitzone, Ort, Status abgesagt/geplant).

## Termine nach Tag

- [Heute]({BASIS_URL}/heute.html): Veranstaltungen von heute
- [Morgen]({BASIS_URL}/morgen.html): Veranstaltungen von morgen
- [Wochenende]({BASIS_URL}/wochenende.html): Freitag bis Sonntag
- Einzelne Tage: {BASIS_URL}/tag/JJJJ-MM-TT.html (zum Beispiel {BASIS_URL}/tag/{datetime.now().strftime('%Y-%m-%d')}.html)

## Monate

{monat_zeilen}

## Maschinenlesbar

- [Sitemap]({BASIS_URL}/sitemap.xml)
- Jeder Termin (außer Kino) als einzelne iCal-Datei: {BASIS_URL}/kalender/<id>.ics, verlinkt beim Termin
"""


def schreibe_wenn_geaendert(pfad: str, inhalt: str) -> bool:
    """Nur schreiben, wenn sich der Inhalt geändert hat (hält Git-Diffs der Tagesseiten klein)."""
    try:
        with open(pfad, encoding='utf-8', newline='') as f:
            if f.read() == inhalt:
                return False
    except FileNotFoundError:
        pass
    os.makedirs(os.path.dirname(pfad) or '.', exist_ok=True)
    with open(pfad, 'w', encoding='utf-8', newline='') as f:
        f.write(inhalt)
    return True


def generiere_auffindbarkeit(basis_pfad: str, termine_je_monat: dict, monate: list[tuple[int, int]],
                             heute, *, tracking: bool = True) -> list[str]:
    """Tagesseiten, heute/morgen/wochenende, Startseite, stil.css, kalender/*.ics, llms.txt.
    Gibt die Pfade (relativ) aller Tagesseiten zurück, für die Sitemap."""
    from datetime import date, timedelta
    j0, m0 = monate[0]
    jn, mn = monate[-1]
    erster = date(j0, m0, 1)
    letzter = date(jn, mn, calendar.monthrange(jn, mn)[1])
    termine_nach_tag: dict = {}
    for termine in termine_je_monat.values():
        for t in termine:
            termine_nach_tag.setdefault(t.datum.date(), []).append(t)

    schreibe_wenn_geaendert(os.path.join(basis_pfad, 'stil.css'), SEITEN_CSS + ZUSATZ_CSS)
    tag_pfade, geaendert = [], 0
    d = erster
    while d <= letzter:
        html = generiere_tagesseite(d, termine_nach_tag.get(d, []), erster, letzter, tracking=tracking)
        geaendert += schreibe_wenn_geaendert(os.path.join(basis_pfad, tagesseite_pfad(d)), html)
        tag_pfade.append(tagesseite_pfad(d))
        d += timedelta(days=1)
    print(f"Tagesseiten: {len(tag_pfade)} ({geaendert} geändert)")

    if erster <= heute <= letzter:
        schreibe_wenn_geaendert(os.path.join(basis_pfad, 'heute.html'),
                                generiere_tagesseite(heute, termine_nach_tag.get(heute, []), erster, letzter,
                                                     art='heute', tracking=tracking))
    morgen = heute + timedelta(days=1)
    if erster <= morgen <= letzter:
        schreibe_wenn_geaendert(os.path.join(basis_pfad, 'morgen.html'),
                                generiere_tagesseite(morgen, termine_nach_tag.get(morgen, []), erster, letzter,
                                                     art='morgen', tracking=tracking))
    schreibe_wenn_geaendert(os.path.join(basis_pfad, 'wochenende.html'),
                            generiere_wochenendseite(wochenend_tage(heute), termine_nach_tag, erster, letzter,
                                                     tracking=tracking))
    schreibe_wenn_geaendert(os.path.join(basis_pfad, 'index.html'),
                            generiere_startseite(heute, termine_nach_tag, monate, erster, letzter, tracking=tracking))
    # Einzeltermine als iCal ("In meinen Kalender"); verwaiste Dateien entfernen
    kalender_dir = os.path.join(basis_pfad, 'kalender')
    soll = {}
    for ts in termine_nach_tag.values():
        for t in ts:
            if hat_kalender_link(t):
                soll[f"{termin_uid(t)}.ics"] = generiere_termin_ics(t)
    neu = sum(schreibe_wenn_geaendert(os.path.join(kalender_dir, name), inhalt) for name, inhalt in soll.items())
    entfernt = 0
    if os.path.isdir(kalender_dir):
        for name in os.listdir(kalender_dir):
            if name.endswith('.ics') and name not in soll:
                os.remove(os.path.join(kalender_dir, name))
                entfernt += 1
    print(f"Kalender-Dateien: {len(soll)} ({neu} geändert, {entfernt} entfernt)")
    schreibe_wenn_geaendert(os.path.join(basis_pfad, 'llms.txt'), generiere_llms_txt(monate))
    print("Startseite, heute/morgen/wochenende, stil.css, llms.txt generiert")
    return tag_pfade


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


def _option_wert(argv: list[str], name: str) -> str | None:
    """Wert einer Option der Form `--name wert` (None, wenn nicht gesetzt)."""
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
        raise SystemExit(f"{name} braucht einen Wert")
    return None


_OPTIONEN_MIT_WERT = ('--ausgabe', '--termine-cache')


def _positionsargumente(argv: list[str]) -> list[str]:
    """Jahr, Monat, Anzahl: alles außer Optionen und deren Werten."""
    ergebnis = []
    ueberspringen = False
    for a in argv:
        if ueberspringen:
            ueberspringen = False
        elif a in _OPTIONEN_MIT_WERT:
            ueberspringen = True
        elif not a.startswith('--'):
            ergebnis.append(a)
    return ergebnis


def _termin_zu_dict(t: Termin) -> dict:
    d = dataclasses.asdict(t)
    d['datum'] = t.datum.isoformat()
    return d


def _termin_aus_dict(d: dict) -> Termin:
    d = dict(d)
    d['datum'] = datetime.fromisoformat(d['datum'])
    return Termin(**d)


def lade_termin_cache(pfad: str) -> dict[str, list[Termin]]:
    """Rohe Scraper-Ergebnisse je Monat ("JJJJ-MM"), damit Vorschau-Läufe nicht neu scrapen."""
    try:
        with open(pfad, encoding='utf-8') as f:
            daten = _json.load(f)
    except FileNotFoundError:
        return {}
    return {k: [_termin_aus_dict(d) for d in v] for k, v in daten.items()}


def speichere_termin_cache(pfad: str, cache: dict[str, list[Termin]]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(pfad)), exist_ok=True)
    with open(pfad, 'w', encoding='utf-8') as f:
        _json.dump({k: [_termin_zu_dict(t) for t in v] for k, v in cache.items()},
                   f, ensure_ascii=False, indent=1)


def main():
    import sys

    no_browser = '--no-browser' in sys.argv
    tracking = '--ohne-tracking' not in sys.argv
    ausgabe = _option_wert(sys.argv, '--ausgabe')
    cache_pfad = _option_wert(sys.argv, '--termine-cache')
    args = _positionsargumente(sys.argv[1:])

    jetzt = datetime.now()
    jahr = int(args[0]) if len(args) > 0 else jetzt.year
    monat = int(args[1]) if len(args) > 1 else jetzt.month
    anzahl_monate = int(args[2]) if len(args) > 2 else 5

    monate_liste = berechne_monate(jahr, monat, anzahl_monate)

    print(f"Generiere {anzahl_monate} Monate ab {monat}/{jahr}...")
    print("=" * 50)

    basis_pfad = os.path.abspath(ausgabe) if ausgabe else os.path.dirname(__file__)
    os.makedirs(basis_pfad, exist_ok=True)
    korrekturen = lade_korrekturen()
    termin_cache = lade_termin_cache(cache_pfad) if cache_pfad else {}
    cache_geaendert = False
    erster_dateiname = None
    termine_je_monat = {}

    for idx, (j, m) in enumerate(monate_liste):
        monatsnamen = ['', 'Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
        print(f"\n[{idx+1}/{anzahl_monate}] {monatsnamen[m]} {j}:")

        cache_key = f"{j}-{m:02d}"
        if cache_key in termin_cache:
            alle_termine = termin_cache[cache_key]
            print(f"  -> {len(alle_termine)} Termine aus Cache {cache_pfad}")
        else:
            alle_termine = []
            for scraper_fn, label in SCRAPER:
                events = scraper_fn(j, m)
                print(f"  -> {len(events)} {label}")
                alle_termine.extend(events)
            if cache_pfad:
                termin_cache[cache_key] = [dataclasses.replace(t) for t in alle_termine]
                cache_geaendert = True

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

        wende_korrekturen_an(alle_termine, korrekturen, j, m)

        vor_dedup = len(alle_termine)
        alle_termine = entferne_duplikate(alle_termine)
        alle_termine.sort()
        entfernt = vor_dedup - len(alle_termine)
        print(f"  => Gesamt: {len(alle_termine)} Termine ({entfernt} Duplikate entfernt)")

        dateiname = dateiname_fuer_monat(j, m)
        html = generiere_html(alle_termine, j, m, monate_liste, dateiname, tracking=tracking)
        ausgabe_pfad = os.path.join(basis_pfad, dateiname)
        with open(ausgabe_pfad, 'w', encoding='utf-8') as f:
            f.write(html)

        termine_je_monat[(j, m)] = alle_termine
        if idx == 0:
            erster_dateiname = ausgabe_pfad

    if cache_pfad and cache_geaendert:
        speichere_termin_cache(cache_pfad, termin_cache)
        print(f"Termin-Cache gespeichert: {cache_pfad}")

    # Startseite (eigener Inhalt statt Kopie des Monats), Tagesseiten, Feeds
    tag_pfade = generiere_auffindbarkeit(basis_pfad, termine_je_monat, monate_liste,
                                         datetime.now().date(), tracking=tracking)

    # sitemap.xml
    heute = datetime.now().strftime('%Y-%m-%d')
    basis_url = BASIS_URL

    def sitemap_eintrag(pfad: str, prio: float, freq: str) -> str:
        return (f'  <url>\n    <loc>{basis_url}/{pfad}</loc>\n    <lastmod>{heute}</lastmod>\n'
                f'    <changefreq>{freq}</changefreq>\n    <priority>{prio:.2f}</priority>\n  </url>')

    sitemap_urls = [sitemap_eintrag('', 1.0, 'daily'), sitemap_eintrag('heute.html', 0.9, 'daily'),
                    sitemap_eintrag('morgen.html', 0.8, 'daily'), sitemap_eintrag('wochenende.html', 0.8, 'daily')]
    prioritaeten = [0.70, 0.60, 0.50, 0.40, 0.30]
    for idx, (j, m) in enumerate(monate_liste):
        prio = prioritaeten[min(idx, len(prioritaeten) - 1)]
        sitemap_urls.append(sitemap_eintrag(dateiname_fuer_monat(j, m), prio, 'daily'))
    for pfad in tag_pfade:
        if pfad[4:14] >= heute:  # vergangene Tage bleiben erreichbar, aber nicht in der Sitemap
            sitemap_urls.append(sitemap_eintrag(pfad, 0.5, 'daily'))
    sitemap_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(sitemap_urls)}
</urlset>'''
    sitemap_pfad = os.path.join(basis_pfad, 'sitemap.xml')
    with open(sitemap_pfad, 'w', encoding='utf-8') as f:
        f.write(sitemap_xml)
    print(f"sitemap.xml generiert ({len(sitemap_urls)} URLs)")

    print("\n" + "=" * 50)
    print(f"Fertig! {anzahl_monate} Dateien generiert.")

    if erster_dateiname and not no_browser:
        webbrowser.open(f'file://{erster_dateiname}')


if __name__ == '__main__':
    main()
