"""Einheitliche Art für alle Termine (Paket B, 14.10.2026).

Jede Quelle liefert eigene Kategorien (rund 34, die Stadt gar keine). Die Art
fasst sie zu einer festen Liste zusammen, als Grundlage für Suche, Filter und
JSON-LD. Sie wird beim Bauen berechnet, nicht im Stand gespeichert, damit
Regeländerungen ohne neuen Abruf wirken. Die Rohkategorie bleibt unverändert.

Reihenfolge der Zuordnung:
1. eindeutige Quelle (Backyard, Ratssitzungen, Cineworld, mOOndock, Sternwarte,
   VHS-Kurse mit mehreren Terminen)
2. Stichworte im Titel, an Wortgrenzen, in der Reihenfolge von TITEL_REGELN
3. eindeutige Stichworte in der Beschreibung
4. Übersetzung der Rohkategorie
5. sonst Sonstiges

Neue Stichworte oder Fehlalarme nur mit Fall in tests/test_art.py.
"""
import re

ARTEN = [
    'Konzert', 'Party', 'Theater/Kabarett', 'Lesung/Vortrag', 'Ausstellung/Kunst',
    'Kurs/Workshop', 'Führung', 'Fest/Markt', 'Kinder/Familie', 'Begegnung/Treffen',
    'Politik', 'Sport/Bewegung', 'Kino', 'Sonstiges',
]
SONSTIGES = 'Sonstiges'

# 1. Quellen, die nur eine Art anbieten
QUELLEN_ART = {
    'backyard': 'Konzert',
    'debut-um-11': 'Konzert',
    'moondock': 'Party',
    'ratssitzungen': 'Politik',
    'cineworld': 'Kino',
}


def _muster(*teile: str) -> re.Pattern:
    return re.compile('|'.join(teile), re.IGNORECASE)


# Eindeutige Musikwörter: Konzert auch in Zusammensetzungen (Familienkonzert)
_MUSIK_STARK = _muster(
    r'konzert', r'\bjazz', r'(?:jazz|akusti\w*|aktusik|jam|blues|pop|rock|musik|music)[- ]?session\b',
    r'live[- ]?musik', r'\bchor', r'chor\b', r'orchest', r'sinfoni', r'symphoni', r'philharmoni',
    r'oratorium', r'unplugged', r'liederabend', r'\bblues\b', r'mitsing',
    r'(?:advents|weihnachts|rudel)singen', r'offenes singen',
)
# Mehrdeutigere Musikwörter, erst nach Lesung, Theater und Kurs geprüft
_MUSIK_SCHWACH = _muster(
    r'musik\b', r'musikalisch', r'melodie', r'\bband\b', r'\btrio\b', r'duo\b', r'\bquartett',
    r'\bquintett', r'ensemble', r'\bakusti', r'\brock\b', r'rock.?n.?roll', r'\bpop\b', r'\bpunk(?!t)',
    r'\bsoul\b', r'\bfolk\b', r'\bgospel', r'\bsongs?\b',
)
_AUSSTELLUNG = _muster(r'vernissage', r'finissage', r'ausstellung')
_KURS = _muster(
    r'workshop', r'(?<!dis)(?<!kon)(?<!ex)kurse?\b', r'seminar', r'training\b', r'schnupper',
    r'bildungsurlaub', r'bastel', r'makramee', r'bemalen', r'(?:selber|selbst) herstellen', r'\bnähen\b',
)
_LESUNG = _muster(
    r'lesung', r'vortrag(?!en\b)', r'vorträg', r'vorlese', r'leseshow', r'lesebühne', r'literatur',
    r'hörspiel', r'silent reading', r'poetry', r'\bslam\b', r'info-?\s?abend', r'infonabend',
    r'informationsabend', r'info-?veranstaltung', r'podium', r'diskussion', r'gesprächsabend',
)
_PARTY = _muster(r'party', r'partys\b', r'\bdisco', r'\bdj\b', r'clubnacht', r'\bü\s?\d\d\b', r'halloween', r'\brave\b')
_KINO = _muster(
    r'\bfilm\b', r'\bfilme\b', r'filmabend', r'filmvorführung', r'filmreihe', r'dokumentarfilm',
    r'kinofilm', r'stummfilm', r'kurzfilm',
)
_THEATER = _muster(
    r'(?<!lichtspiel)(?<!kino-)(?<!kino)theat(?:er|re)', r'kabarett', r'comedy', r'komödie', r'musicals?\b',
    r'variet[ée]', r'zaubershow', r'zauberer', r'puppen', r'marionett', r'krimi\w*[- ]?dinner', r'\boper\b', r'operette', r'ballett',
)
# Führung: Zusammensetzungen (Rathausführung) außer Leitungsthemen, oder „Führung durch …“
_FUEHRUNG = _muster(
    r'(?<![\w-])(?!vereins|unternehmens|mitarbeiter|buch|geschäfts|menschen|team|personal|gesprächs'
    r'|selbst|lebens|betriebs|praxis|haushalts)\w+führung(?:en)?\b',
    r'\w-führung', r'öffentliche\s+führung', r'\bführung(?:en)?\s+(?:durch|über|im|in|zum|zur|am|auf|mit)\b',
    r'rundgang', r'stadtgang', r'spaziergang', r'besichtigung', r'exkursion',
)
_KINDER = _muster(
    r'kinder', r'\bkind\b', r'-kind\b', r'\bkind-', r'familie', r'eltern', r'baby', r'bilderbuch',
    r'\bkita\b', r'kulturrucksack', r'ferienprogramm', r'\bmütter', r'\bväter', r'jugendliche',
    r'alleinerziehend',
)
_KUNST = _muster(r'kunst', r'malerei', r'galerie', r'licht[- ]?art\b', r'skulptur', r'graffiti', r'atelier')
_FEST = _muster(
    r'(?<!mani)fest\b', r'festival', r'\bfeier\b',
    r'(?<!arbeits)(?<!wohnungs)(?<!immobilien)(?<!finanz)(?<!aktien)(?<!kapital)(?<!strom)(?<!energie)markt\b',
    r'mittelalterm', r'trödel', r'basar', r'kirmes', r'tauschbörse', r'kleidertausch', r'verkaufsoffen',
    r'verkauf\b',
)
_SPORT = _muster(
    r'radtour', r'radeln\b', r'feierabend-?\s?tour', r'\bwander', r'(?:rad|herbst|winter|natur|nacht)wanderung',
    r'pilger', r'yoga', r'meditation', r'(?<!dis)(?<!ins)(?<!subs)(?<!kons)tanz', r'\bdance\b',
    r'(?<!tran)sport', r'fitness', r'gymnastik', r'schwimm', r'turnier',
    r'(?:stadt|volks|spenden|lichter|staffel|nacht)lauf\b', r'lauftreff', r'walking',
)
_POLITIK = _muster(
    r'(?<!karnevals)(?<!prunk)(?<!damen)sitzung', r'ausschuss', r'bürgermeister', r'demokratie',
    r'kundgebung', r'mahnwache', r'\bdemo\b', r'gedenk', r'pogrom', r'wehrpflicht', r'antisemitismus',
)
_TREFFEN = _muster(
    r'(?<=[\w-])treff', r'\btreff\b', r'^treffen\b', r'stammtisch', r'caf[eé]\b', r'begegnung', r'frühstück',
    r'gesprächskreis', r'selbsthilfe', r'repair', r'offene schmiede', r'gruppe\b', r'forum\b', r'küfa\b', r'(?<=\w)essen\b', r'\bdinner\b',
    r'fondue', r'(?:miteinander|gemeinsam(?:es)?) singen', r'singkreis',
)

# 2. Titel: erste passende Regel gewinnt. Bühnenformate vor Zielgruppe vor Rest.
TITEL_REGELN = [
    ('Konzert', _MUSIK_STARK),
    ('Ausstellung/Kunst', _AUSSTELLUNG),
    ('Kurs/Workshop', _KURS),
    ('Lesung/Vortrag', _LESUNG),
    ('Party', _PARTY),
    ('Kino', _KINO),
    ('Theater/Kabarett', _THEATER),
    ('Führung', _FUEHRUNG),
    ('Konzert', _MUSIK_SCHWACH),
    ('Kinder/Familie', _KINDER),
    ('Ausstellung/Kunst', _KUNST),
    ('Fest/Markt', _FEST),
    ('Sport/Bewegung', _SPORT),
    ('Politik', _POLITIK),
    ('Begegnung/Treffen', _TREFFEN),
]

# 3. Beschreibung: nur Wörter, die kaum etwas anderes bedeuten
# (Die Stadt nennt bei Gastspielen das Ensemble: „Ohnsorg Theater“, „Burghofbühne“.)
BESCHREIBUNG_REGELN = [
    ('Konzert', _muster(r'konzert', r'oratori')),
    ('Theater/Kabarett', _muster(
        r'(?<!lichtspiel)(?<!kino-)(?<!kino)theater', r'kabarett', r'komödie', r'comedy', r'musical\b', r'burghofbühne',
        r'landesbühne', r'choreogra')),
    ('Lesung/Vortrag', _muster(r'vortrag\b')),
    # nicht jeder Rundgang: „Lichtjonglage auf einem Rundgang durch das Kulturquartier“
    ('Führung', _muster(r'\b(?:die|eine) führung\b', r'beim rundgang', r'historische\w* rundgang')),
]

# 4. Rohkategorien der Quellen; Kultur, Veranstaltungen, Freizeit u. Ä. sagen nichts
ROHKATEGORIEN = {
    'Musik': 'Konzert', 'Konzert': 'Konzert',
    'Party': 'Party',
    'Theater': 'Theater/Kabarett',
    'Literatur': 'Lesung/Vortrag', 'Lesung': 'Lesung/Vortrag', 'Vortrag': 'Lesung/Vortrag',
    'Bildung': 'Lesung/Vortrag', 'Geschichte': 'Lesung/Vortrag', 'Astronomie': 'Lesung/Vortrag',
    'Bibliothek': 'Lesung/Vortrag',
    'Kunst': 'Ausstellung/Kunst', 'Ausstellung': 'Ausstellung/Kunst',
    'Kurs': 'Kurs/Workshop',
    'Fest': 'Fest/Markt',
    'Familie': 'Kinder/Familie', 'Familien': 'Kinder/Familie',
    'Begegnung': 'Begegnung/Treffen', 'Treffen': 'Begegnung/Treffen', 'Senioren': 'Begegnung/Treffen',
    'Selbsthilfe': 'Begegnung/Treffen', 'Ehrenamt': 'Begegnung/Treffen', 'Gruppentermine': 'Begegnung/Treffen',
    'Politik': 'Politik',
    'Radtour': 'Sport/Bewegung',
    'Kino': 'Kino', 'Film': 'Kino',
}


def art_mit_grund(t) -> tuple[str, str]:
    """Art eines Termins und die Regel, die gegriffen hat (für Prüftabellen)."""
    if t.quelle in QUELLEN_ART:
        return QUELLEN_ART[t.quelle], 'Quelle'
    if t.quelle == 'sternwarte':
        # Planetarium und Vorträge, ab und zu ein Livekonzert unter der Kuppel. Die
        # Musikprogramme („Musik im Sternenzelt“, „Keltika“) laufen vom Band, kein Konzert.
        treffer = _MUSIK_STARK.search(t.name)
        if treffer:
            return 'Konzert', f'Quelle, Titel „{treffer.group(0)}“'
        return 'Lesung/Vortrag', 'Quelle'
    if t.quelle == 'vhs' and t.kategorie == 'Kurs':
        # Mehrere Termine laut VHS-Detailseite, auch bei Yoga oder Schauspiel im Titel
        return 'Kurs/Workshop', 'Quelle (VHS-Kurs)'
    for art, muster in TITEL_REGELN:
        treffer = muster.search(t.name)
        if treffer:
            return art, f'Titel „{treffer.group(0)}“'
    for art, muster in BESCHREIBUNG_REGELN:
        treffer = muster.search(t.beschreibung or '')
        if treffer:
            return art, f'Beschreibung „{treffer.group(0)}“'
    if t.kategorie in ROHKATEGORIEN:
        return ROHKATEGORIEN[t.kategorie], f'Kategorie „{t.kategorie}“'
    return SONSTIGES, '-'


def bestimme_art(t) -> str:
    """Art eines Termins aus Quelle, Titel, Beschreibung und Rohkategorie."""
    return art_mit_grund(t)[0]


def setze_arten(termine: list) -> None:
    for t in termine:
        t.art = bestimme_art(t)
