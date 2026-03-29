# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Ausführung

```bash
# Python-Pfad (System nutzt 3.14 Framework-Installation)
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 app.py --no-browser

python3 app.py                    # 5 Monate ab heute, öffnet Browser
python3 app.py 2026 2             # 5 Monate ab Februar 2026
python3 app.py 2026 2 6           # 6 Monate ab Februar 2026
python3 app.py --no-browser       # Ohne Browser öffnen

./update.sh                       # Aktualisieren + Git Push + macOS-Benachrichtigung
./oeffne_aktuell.sh               # Aktuellen Monat im Browser öffnen
```

## GitHub Pages

- **Repository:** https://github.com/mastermint-63/Termine-Recklinghausen
- **Live URL:** https://termine.holzwurm-recklinghausen.de (Custom Domain via `CNAME`)
- **Deploy:** GitHub Actions (`deploy.yml`) triggert bei Push von `termine_re_*.html` oder `index.html`

## Architektur

```
29 Quellen → scraper.py (Termin-Objekte) → app.py (HTML-Generierung) → GitHub Pages
```

**scraper.py** — 28 Funktionen, jede gibt `list[Termin]` zurück. Gemeinsamer `Termin`-Dataclass mit Feldern: name, datum, uhrzeit, ort, link, beschreibung, quelle, kategorie. Wichtige Shared Helpers: `_im_monat(datum, jahr, monat)` prüft ob ein Termin im Zielmonat liegt; `_hole_events_calendar(url, quelle, kategorie, jahr, monat)` extrahiert JSON-LD Events (The Events Calendar / MEC Plugin) — wird von NLGR, Literaturtage, Altstadtschmiede und Backyard genutzt; `_adfc_fetch(unit_key, event_type)` holt ADFC-Events per JSON-API; `_ics_unfold/wert/datum` parsen ICS-Feeds.

**app.py** — Generiert standalone HTML-Dateien (`termine_re_YYYY_MM.html`) mit eingebettetem CSS + JS. Kein Build-System. Holzwurm-Design (warme Beige-/Orange-Töne), Dark Mode via `prefers-color-scheme`. Jeder Termin hat `data-quelle` Attribut für JavaScript-Filterung: Quellen-Dropdown + Toggle-Buttons (VHS, Kino) zum Ausblenden dominanter Quellen. VHS und Kino sind **beim Seitenaufruf immer ausgeblendet** (kein localStorage). Filterleiste ist `position: sticky` mit Milchglas-Effekt (`backdrop-filter: blur`). Beim Direktaufruf springt JS automatisch zum ersten heutigen oder zukünftigen Termin (sofern kein Anker in der URL); Monatsnavigation-Links tragen `#top` → Browser scrollt nach oben, Auto-Sprung wird unterdrückt. Canonical-URL und og:url zeigen auf die jeweilige Monatsdatei (`/termine_re_YYYY_MM.html`), nicht auf die Root-URL. `generiere_html()` erwartet `dateiname`-Parameter für die Canonical-URL. Kalender markiert den heutigen Tag per JS (`kal-heute`-Klasse). Deduplizierung über `entferne_duplikate()` (`app.py`): gleiches Datum + normalisierter Name (exakt oder Teilstring) → Eintrag mit besserem Info-Score wird behalten, **fehlende Felder (beschreibung, uhrzeit, ort) werden aus dem Duplikat ergänzt** (link wird nie überschrieben). **`_QUELLEN_TIER`** unterscheidet Aggregatoren (Tier 2: `stadt-re`, `vesterleben`, `recklinghaeuser`) von Veranstaltern (Tier 1 = Default): Aggregatoren bekommen −10 Score-Malus, sodass spezifische Veranstalter (NLGR, Altstadtschmiede usw.) immer gewinnen, auch wenn der Aggregator mehr Felder gefüllt hat. (z.B. Stadtarchiv-PDF liefert Uhrzeit, stad-re-Kalender liefert Beschreibung). Beschreibungen werden auf 800 Zeichen begrenzt; bei Terminen mit Link und langer Beschreibung (>120 Zeichen) erscheint ein aufklappbarer Text mit `termin-beschreibung-mehr`-Klasse und `onclick`-Toggle.

**update.sh** — Tägliche Automation: Scraping → Löschroutine für alte Dateien → Event-Count-Diff → bedingter Git Push → macOS-Benachrichtigung via terminal-notifier. Nutzt Python 3.14 Framework-Pfad. Dateien älter als der Vormonat werden automatisch per `git rm` entfernt und im gleichen Commit mitgepusht (1-Monats-Puffer: Vormonat bleibt erhalten).

### Automatische Aktualisierung

Lokales Scraping via launchd (Cloud-IPs werden von regionalen Websites blockiert).

```
06:30 Uhr: launchd (de.termine-re.update) → update.sh → git push → GitHub Actions → Pages
```

```bash
launchctl list | grep termine-re           # Status prüfen
launchctl start de.termine-re.update       # Manuell auslösen
tail -f launchd.log                        # Live-Log
```

## Tests

```bash
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest tests/ -v   # alle Tests
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest tests/test_dedup.py -v  # einzelne Datei
```

`tests/test_dedup.py` — testet `_termin_score()` und `entferne_duplikate()` aus `app.py`. Kein Mock-Framework nötig; Termin-Objekte werden direkt instanziiert.

## Abhängigkeiten

```bash
pip install requests beautifulsoup4 lxml pymupdf   # pymupdf = PyMuPDF (fitz), für Stadtarchiv-PDF
# requirements.txt enthält nur requests/beautifulsoup4/lxml — pymupdf bewusst ausgelassen (optional)
```

## Quellen und Parsing-Details

| Funktion | Quelle | Parsing-Methode |
|----------|--------|-----------------|
| `hole_regioactive()` | regioactive.de | JSON-LD `ItemList` — zuverlässigste Quelle |
| `hole_stadt_re()` | recklinghausen.de | ASP-Tabelle `<tr><td>` (Übersicht) + selfdb-Detailseiten für Uhrzeit, Beschreibung, Veranstaltungsstätte; Feldklassen: `selfdb_fieldZeiten`, `selfdb_fieldInhalt`, `selfdb_fieldVeranstaltungssttte` (ä fehlt in Klassenname) |
| `hole_altstadtschmiede()` | altstadtschmiede.de/events/ | JSON-LD `Event` (MEC WordPress Plugin); URL auf `/events/` (zeigt auch Fremdveranstaltungen) |
| `hole_vesterleben()` | vesterleben.de | Link-Text-Parsing, PLZ-Zeile `NNNNN \| Stadt` für Stadtfilter |
| `hole_sternwarte()` | sternwarte-recklinghausen.de | `<p><u>Datum</u><strong>Titel</strong>` Struktur |
| `hole_kunsthalle()` | kunsthalle-recklinghausen.de | Zeilenweise: DD.MM. → Titel → Uhrzeit |
| `hole_stadtbibliothek()` | recklinghausen.de/stadtbibliothek | GKD-selfdb: `div.selfdb_reportentry` mit Felddivs |
| `hole_nlgr()` | nlgr.de | JSON-LD `Event` (The Events Calendar Plugin) |
| `hole_literaturtage()` | literaturtage-recklinghausen.de | JSON-LD `Event` (The Events Calendar Plugin) |
| `hole_vhs()` | vhs-recklinghausen.de | KuferWeb: 7 Kategorieseiten mit Paginierung, `h4.kw-ue-title` + `div.row`, interne Duplikat-Erkennung über Name+Datum |
| `hole_akademie()` | ahademie.com | TYPO3: `div.col-md-4` mit `a.box-hov`, `p.eventdate-big`, `p.subheadline` |
| `hole_stadtarchiv()` | recklinghausen.de (PDF) | PyMuPDF: Halbjahres-PDFs, Regex für deutsche Datumsformate |
| `hole_geschichte_re()` | geschichte-recklinghausen.de | ECT-Timeline: `div.ect-timeline-post`, Datum aus `content`-Attribut (Stunde%12-Bug: 1–8→+12) |
| `hole_gastkirche()` | gastkirche.de | JEvents (Joomla): Wochenansicht, Kat. 68+70, `li.ev_td_li` mit `a.ev_link_row` |
| `hole_ruhrfestspiele()` | ruhrfestspiele.de | Zweistufig: /programm → Produktions-Links → Detailseiten, `article.production-schedule-item` |
| `hole_backyard()` | backyard-club.de | TEC JSON-LD (doppelt auf Seite → interne Deduplizierung + HTML-Entity-Bereinigung) |
| `hole_cineworld()` | cineworld-recklinghausen.de | Cineamo API (`api.cineamo.com`), Cinema-ID 877, pro Tag abgefragt, Vorstellungen pro Film gruppiert |
| `hole_neue_philharmonie()` | neue-philharmonie-westfalen.de | HTML `div.c-event`, Datum `span.c-event__date-date` ("10. März" ohne Jahr), Stadtfilter auf "Recklinghausen" |
| `hole_ikonen_museum()` | ikonen-museum.com | HTML `div.event-list-item`, Datum `div.event-startdate` ("01.03." ohne Jahr), Uhrzeit aus `div.info` |
| `hole_debut_um_11()` | debut-um-11.de | WordPress `article.post-item`, Termin aus `h2.entry-title a` Link-Text ("15. März 2026, 11:00 Uhr") |
| `hole_adfc()` | recklinghausen.adfc.de | JSON-API `api-touren-termine.adfc.de`, unitKey 164420 (Termine) + 16442006 (Radtouren), Stadtfilter "Recklinghausen", ein Request für alle Events |
| `hole_atelierhaus()` | atelierhaus-recklinghausen.de | ICS-Feed (ai1ec Plugin); mehrtägige Ausstellungen erscheinen in jedem überlappenden Monat mit `kategorie='Ausstellung'`; iCal DTEND bei Ganztages-Events = exklusiver Folgetag (−1 Tag korrigieren) |
| `hole_zu_gast_in_re()` | zu-gast-in-re.de/programm | Text-Parsing: Website-Builder (DM), Datum-Spans per Regex, ein Termin pro Festival-Tag; Seite enthält nur Vorjahresprogramm bis neues veröffentlicht wird |
| `hole_re_leuchtet()` | re-leuchtet.de/programm | TEC REST-API (`wp-json/tribe/events/v1/events`); Jahresfestival, meist nur wenige Termine |
| `hole_frauenforum()` | — (kein Scraping) | Programmatisch: 3. Dienstag/Monat, 17 Uhr, Familienbüro Große Geldstraße 19; Pause Juli + Dezember |
| `hole_josefeich()` | josefeich.de | JSON-LD `Event` (The Events Calendar Plugin); Kirchenmusik-Termine |
| `hole_recklinghaeuser()` | der-recklinghaeuser.de | Fließtext-Parsing: deutsche Datumsformate ("Sa. 14. März 2026"), Titel + Uhrzeit aus Folgezeilen |
| `hole_subergs()` | subergs.de/events/ | WordPress-Blogposts: Datum im h3-Titel ("DD.MM.YYYY – Titel"), Elementor-Layout |
| `hole_stadtlabor()` | stadtlabor-re.de | Armadillo-Blog: `div.blog-entry`, Vernissage-Datum/Uhrzeit aus Titel+Body per Regex (DE/EN-Monate, DD.MM.YYYY) |

**Wartungshinweis:** Parser sind fragil gegenüber HTML-Strukturänderungen. Bei 0 Events aus einer Quelle: erst echte HTML-Struktur mit Debug-Script prüfen, nie auf Vermutungen basieren.

## Code-Konventionen

- **HTML-Escaping:** `import html as _html` (Alias nötig, weil `generiere_html()` intern eine lokale Variable `html` verwendet — direktes `import html` führt zu `UnboundLocalError`). Alle gescrapten Textfelder werden mit `_html.escape()` escaped.
- **URL-Validierung:** Externe Links als `link_safe = t.link if t.link and t.link.startswith(('http://', 'https://')) else ''` validieren — nur dann als `<a href>` rendern, sonst `<span>`.
- **Alle `target="_blank"`-Links** müssen `rel="noopener noreferrer"` tragen.

## Bekannte Probleme / offene Punkte

### regioactive.de — Cloudflare-Block seit 26.02.2026
- Seit 26.02.2026 liefert regioactive.de 403 (Cloudflare Bot-Schutz)
- `curl` und Playwright headless werden geblockt ("Just a moment..."-Challenge)
- Letzter erfolgreicher Abruf: 25.02.2026 (3 Termine)
- **TODO:** Prüfen ob Cloudflare-Sperre temporär oder dauerhaft; ggf. API-Endpunkt suchen oder Quelle ersetzen

### Beschreibungen aufklappen — CSS-Problem (offen seit 01.03.2026)
- Termine mit Link + Beschreibung >120 Zeichen: Klasse `termin-beschreibung-mehr` + `onclick` → Pfeil ▸/▾ wechselt korrekt (JS/`.expanded` funktioniert), aber Text klappt nicht auf
- CSS-Regel: `.termin.expanded .termin-beschreibung { -webkit-line-clamp: 50; overflow: visible; }` scheint nicht zu greifen
- **Nächster Ansatz:** Browser DevTools → Element inspizieren wenn `.expanded` gesetzt → prüfen welche CSS-Regel tatsächlich für die Höhe verantwortlich ist

## Neue Quelle hinzufügen

1. Funktion in `scraper.py`: `hole_neue_quelle(jahr, monat) -> list[Termin]`
2. In `app.py` importieren und in `main()` aufrufen
3. `quelle`-String für Filterung setzen
4. Label in `QUELLEN`-Dict eintragen — **modulweite Konstante in `app.py` Zeile ~30**, nicht innerhalb einer Funktion
5. Falls die Quelle ein Aggregator ist (listet auch fremde Events auf): `quelle`-Key in `_QUELLEN_TIER` mit Wert `2` eintragen — sonst verdrängt sie spezifische Veranstalter im Dedup
6. Badge-CSS-Klasse `.badge-neuequelle` mit Farbgradient in `generiere_html()` ergänzen — Konvention: `linear-gradient(135deg, #HELL 0%, #DUNKEL 100%)`, zweite Farbe ca. 10 Einheiten dunkler; alle 25 vorhandenen Farben sind in der Funktion dokumentiert, keine Doppelung wählen
7. Badge-Zuordnung in `badge_classes`-Dict in `generiere_html()` eintragen
8. Footer-Link in `generiere_html()` ergänzen
9. Optional: Toggle-Button falls Quelle viele Termine liefert — `toggleXyz()`-Funktion + `xyzAusgeblendet`-Variable + `xyzMatch`-Check in `filterTermine()` (Muster: siehe VHS/Kino-Toggle)
10. Quellentabelle in dieser CLAUDE.md aktualisieren

**`hebbert/`** — Maskottchen-Bilder für den Seitenheader. Aktiv: `1984-01-verkleinert.jpg` (links) und `1985-04-verkleinert.jpg` (rechts). Originals liegen als Fallback daneben, nicht mehr referenziert.

**`favicon.ico` / `favicon-96x96-1.webp`** — Beide Formate nötig: `.ico` als Browser-Fallback (wird automatisch als `/favicon.ico` abgerufen), `.webp` für moderne Browser. Beide sind im HTML-`<head>` eingebunden, `.ico` zuerst.
