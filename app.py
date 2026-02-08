#!/usr/bin/env python3
"""
Termine in Recklinghausen — Dashboard
Sammelt Veranstaltungen aus mehreren Quellen und generiert ein HTML-Dashboard.

Verwendung:
    python3 app.py              # Generiert aktuellen + 2 weitere Monate
    python3 app.py 2026 2       # Generiert ab Februar 2026 (3 Monate)
    python3 app.py 2026 2 6     # Generiert 6 Monate ab Februar 2026
    python3 app.py --no-browser # Ohne Browser öffnen
"""

import os
import re
import webbrowser
import calendar
from datetime import datetime

from scraper import (
    hole_regioactive, hole_stadt_re, hole_altstadtschmiede,
    hole_vesterleben, hole_sternwarte, hole_kunsthalle, Termin,
)


QUELLEN = {
    'regioactive': 'regioactive.de',
    'stadt-re': 'Stadt RE',
    'altstadtschmiede': 'Altstadtschmiede',
    'vesterleben': 'Vesterleben.de',
    'sternwarte': 'Sternwarte',
    'kunsthalle': 'Kunsthalle',
}


def _normalisiere(name: str) -> str:
    """Normalisiert einen Eventnamen für Vergleiche."""
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', '', name)  # Sonderzeichen entfernen
    name = re.sub(r'\s+', ' ', name)     # Mehrfach-Leerzeichen
    return name


def _termin_score(t: Termin) -> int:
    """Bewertet die Informationsqualität eines Termins (höher = besser)."""
    score = 0
    if t.link:
        score += 2
    if t.uhrzeit and t.uhrzeit not in ('ganztägig', 'siehe Website'):
        score += 2
    if t.beschreibung:
        score += 1
    if t.ort:
        score += 1
    return score


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
                # Exakt gleich oder einer ist Teilstring des anderen
                if norm_k == norm_v or norm_k in norm_v or norm_v in norm_k:
                    ist_duplikat = True
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
                html += f'<td><a href="#datum-{datum_key}" class="kal-link">{tag}</a></td>'
            else:
                html += f'<td class="kal-leer">{tag}</td>'
        html += '</tr>\n'

    html += '</table>'
    return html


def generiere_html(termine: list[Termin], jahr: int, monat: int,
                   verfuegbare_monate: list[tuple[int, int]]) -> str:
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
            <div class="datum-header">{datum_formatiert}</div>
            <div class="termine-liste">
        '''

        for t in sorted(tage, key=lambda x: (x.uhrzeit == 'ganztägig', x.uhrzeit == 'siehe Website', x.uhrzeit, x.name)):
            beschreibung_escaped = t.beschreibung.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')[:200]

            # Badge für Quelle
            badge_classes = {
                'regioactive': 'badge-regioactive',
                'altstadtschmiede': 'badge-altstadtschmiede',
                'sternwarte': 'badge-sternwarte',
                'kunsthalle': 'badge-kunsthalle',
                'vesterleben': 'badge-vesterleben',
                'stadt-re': 'badge-stadt',
            }
            badge_class = badge_classes.get(t.quelle, 'badge-default')
            quelle_label = QUELLEN.get(t.quelle, t.quelle)
            badge_html = f'<span class="badge {badge_class}">{quelle_label}</span>'

            if t.kategorie:
                badge_html += f' <span class="badge badge-kategorie">{t.kategorie}</span>'

            # Name als Link oder aufklappbar
            if t.link:
                name_html = f'<a href="{t.link}" target="_blank">{t.name}</a>'
            else:
                name_html = f'<span class="termin-toggle" onclick="this.closest(\'.termin\').classList.toggle(\'expanded\')">{t.name}</span>'

            termine_html += f'''
                <div class="termin" data-quelle="{t.quelle}">
                    <div class="termin-zeit">{t.uhrzeit}</div>
                    <div class="termin-info">
                        <div class="termin-name">
                            {name_html}
                            {badge_html}
                        </div>
                        {f'<div class="termin-ort">{t.ort}</div>' if t.ort else ''}
                        {f'<div class="termin-beschreibung">{beschreibung_escaped}</div>' if beschreibung_escaped else ''}
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

    prev_link = dateiname_fuer_monat(prev_jahr, prev_monat) if prev_verfuegbar else "#"
    next_link = dateiname_fuer_monat(next_jahr, next_monat) if next_verfuegbar else "#"

    prev_class = "" if prev_verfuegbar else " disabled"
    next_class = "" if next_verfuegbar else " disabled"

    # Kalenderblatt
    tage_mit_events = set(int(k.split('-')[2]) for k in nach_datum.keys())
    kalender_html = generiere_kalender(jahr, monat, tage_mit_events)

    html = f'''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Termine Recklinghausen — {monatsnamen[monat]} {jahr}</title>
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
            background: var(--card-bg);
            border-radius: 10px;
            border: 1px solid var(--border-color);
            flex-wrap: wrap;
            gap: 10px;
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
                <img src="hebbert/1984-01.jpg" alt="Hebbert" class="hebbert">
                <div class="header-text">
                    <h1>Termine in Recklinghausen</h1>
                </div>
                <img src="hebbert/1985-04.jpg" alt="Hebbert am Terminplan" class="hebbert">
            </div>
            <div class="nav">
                <a href="{prev_link}" class="nav-btn{prev_class}">&larr; {monatsnamen[prev_monat]}</a>
                <span class="monat-titel">{monatsnamen[monat]} {jahr}</span>
                <a href="{next_link}" class="nav-btn{next_class}">{monatsnamen[next_monat]} &rarr;</a>
            </div>
        </header>

        {kalender_html}

        <div class="filter-bar">
            <select id="quelle-filter" onchange="filterTermine()">
                {quellen_filter}
            </select>
            <div class="stats">
                <span id="termine-count">{len(termine)}</span> Termine
            </div>
        </div>

        <main id="termine-container">
            {termine_html if termine else '<div class="keine-termine">Keine Termine gefunden</div>'}
        </main>

        <footer>
            Generiert am {datetime.now().strftime('%d.%m.%Y um %H:%M Uhr')}<br>
            Quellen:
            <a href="https://www.regioactive.de/events/22868/recklinghausen/veranstaltungen-party-konzerte" target="_blank">regioactive.de</a> &middot;
            <a href="https://www.recklinghausen.de/inhalte/startseite/_veranstaltungskalender/" target="_blank">Stadt RE</a> &middot;
            <a href="https://www.altstadtschmiede.de/aktuelle-veranstaltungen" target="_blank">Altstadtschmiede</a> &middot;
            <a href="https://vesterleben.de/termine" target="_blank">Vesterleben.de</a> &middot;
            <a href="https://sternwarte-recklinghausen.de/programm/veranstaltungskalender/" target="_blank">Sternwarte</a> &middot;
            <a href="https://kunsthalle-recklinghausen.de/en/program/calendar" target="_blank">Kunsthalle</a>
        </footer>
    </div>

    <script>
        function filterTermine() {{
            const quelleFilter = document.getElementById('quelle-filter').value;
            const termine = document.querySelectorAll('.termin');
            let sichtbar = 0;

            termine.forEach(t => {{
                const quelleMatch = !quelleFilter || t.dataset.quelle === quelleFilter;

                if (quelleMatch) {{
                    t.classList.remove('hidden');
                    sichtbar++;
                }} else {{
                    t.classList.add('hidden');
                }}
            }});

            document.getElementById('termine-count').textContent = sichtbar;

            document.querySelectorAll('.datum-gruppe').forEach(g => {{
                const sichtbareTermine = g.querySelectorAll('.termin:not(.hidden)');
                g.classList.toggle('hidden', sichtbareTermine.length === 0);
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
    anzahl_monate = int(args[2]) if len(args) > 2 else 3

    monate_liste = berechne_monate(jahr, monat, anzahl_monate)

    print(f"Generiere {anzahl_monate} Monate ab {monat}/{jahr}...")
    print("=" * 50)

    basis_pfad = os.path.dirname(__file__)
    erster_dateiname = None

    for idx, (j, m) in enumerate(monate_liste):
        monatsnamen = ['', 'Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
        print(f"\n[{idx+1}/{anzahl_monate}] {monatsnamen[m]} {j}:")

        alle_termine = []

        # 1. RegioActive
        events = hole_regioactive(j, m)
        print(f"  -> {len(events)} regioactive.de")
        alle_termine.extend(events)

        # 2. Stadt RE
        events = hole_stadt_re(j, m)
        print(f"  -> {len(events)} Stadt RE")
        alle_termine.extend(events)

        # 3. Altstadtschmiede
        events = hole_altstadtschmiede(j, m)
        print(f"  -> {len(events)} Altstadtschmiede")
        alle_termine.extend(events)

        # 4. Vesterleben
        events = hole_vesterleben(j, m)
        print(f"  -> {len(events)} Vesterleben.de")
        alle_termine.extend(events)

        # 5. Sternwarte
        events = hole_sternwarte(j, m)
        print(f"  -> {len(events)} Sternwarte")
        alle_termine.extend(events)

        # 6. Kunsthalle
        events = hole_kunsthalle(j, m)
        print(f"  -> {len(events)} Kunsthalle")
        alle_termine.extend(events)

        vor_dedup = len(alle_termine)
        alle_termine = entferne_duplikate(alle_termine)
        alle_termine.sort()
        entfernt = vor_dedup - len(alle_termine)
        print(f"  => Gesamt: {len(alle_termine)} Termine ({entfernt} Duplikate entfernt)")

        html = generiere_html(alle_termine, j, m, monate_liste)

        dateiname = dateiname_fuer_monat(j, m)
        ausgabe_pfad = os.path.join(basis_pfad, dateiname)
        with open(ausgabe_pfad, 'w', encoding='utf-8') as f:
            f.write(html)

        if idx == 0:
            erster_dateiname = ausgabe_pfad

    # index.html
    erster_monat_datei = dateiname_fuer_monat(monate_liste[0][0], monate_liste[0][1])
    index_html = f'''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url={erster_monat_datei}">
    <title>Termine Recklinghausen</title>
</head>
<body>
    <p>Weiterleitung zu <a href="{erster_monat_datei}">{erster_monat_datei}</a>...</p>
</body>
</html>'''
    index_pfad = os.path.join(basis_pfad, 'index.html')
    with open(index_pfad, 'w', encoding='utf-8') as f:
        f.write(index_html)
    print(f"index.html -> {erster_monat_datei}")

    print("\n" + "=" * 50)
    print(f"Fertig! {anzahl_monate} Dateien generiert.")

    if erster_dateiname and not no_browser:
        webbrowser.open(f'file://{erster_dateiname}')


if __name__ == '__main__':
    main()
