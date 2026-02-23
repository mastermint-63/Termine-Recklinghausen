# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Ausführung

```bash
python3 app.py                    # 5 Monate ab heute, öffnet Browser
python3 app.py 2026 2             # 5 Monate ab Februar 2026
python3 app.py 2026 2 6           # 6 Monate ab Februar 2026
python3 app.py --no-browser       # Ohne Browser öffnen

./update.sh                       # Aktualisieren + Git Push + macOS-Benachrichtigung
./oeffne_aktuell.sh               # Aktuellen Monat im Browser öffnen
```

## GitHub Pages

- **Repository:** https://github.com/mastermint-63/Termine-Recklinghausen
- **Live URL:** https://mastermint-63.github.io/Termine-Recklinghausen/ (keine Custom Domain)
- **Deploy:** GitHub Actions (`deploy.yml`) triggert bei Push von `termine_re_*.html` oder `index.html`

## Architektur

```
21 Webquellen → scraper.py (Termin-Objekte) → app.py (HTML-Generierung) → GitHub Pages
```

**scraper.py** — 21 Scraper-Funktionen, jede gibt `list[Termin]` zurück. Gemeinsamer `Termin`-Dataclass mit Feldern: name, datum, uhrzeit, ort, link, beschreibung, quelle, kategorie. Wichtige Shared Helpers: `_im_monat(datum, jahr, monat)` prüft ob ein Termin im Zielmonat liegt; `_hole_events_calendar(url, quelle, kategorie, jahr, monat)` extrahiert JSON-LD Events (The Events Calendar / MEC Plugin) — wird von NLGR, Literaturtage, Altstadtschmiede und Backyard genutzt; `_adfc_fetch(unit_key, event_type)` holt ADFC-Events per JSON-API.

**app.py** — Generiert standalone HTML-Dateien (`termine_re_YYYY_MM.html`) mit eingebettetem CSS + JS. Kein Build-System. Holzwurm-Design (warme Beige-/Orange-Töne), Dark Mode via `prefers-color-scheme`. Jeder Termin hat `data-quelle` Attribut für JavaScript-Filterung: Quellen-Dropdown + Toggle-Buttons (VHS, Kino) zum Ausblenden dominanter Quellen. VHS und Kino sind standardmäßig ausgeblendet; Zustand wird per `localStorage` gespeichert. Filterleiste ist `position: sticky` mit Milchglas-Effekt (`backdrop-filter: blur`). Beim Seitenaufruf springt JS automatisch zum ersten heutigen oder zukünftigen Termin (sofern kein Anker in der URL). Kalender markiert den heutigen Tag per JS (`kal-heute`-Klasse). Deduplizierung über `entferne_duplikate()`: gleiches Datum + normalisierter Name (exakt oder Teilstring) → Termin mit besserem Info-Score behalten.

**update.sh** — Tägliche Automation: Scraping → Event-Count-Diff → bedingter Git Push → macOS-Benachrichtigung via terminal-notifier. Nutzt Python 3.14 Framework-Pfad.

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

## Abhängigkeiten

```bash
pip install requests beautifulsoup4 lxml pymupdf   # pymupdf = PyMuPDF (fitz), für Stadtarchiv-PDF
# requirements.txt enthält nur requests/beautifulsoup4/lxml — pymupdf bewusst ausgelassen (optional)
```

## Quellen und Parsing-Details

| Funktion | Quelle | Parsing-Methode |
|----------|--------|-----------------|
| `hole_regioactive()` | regioactive.de | JSON-LD `ItemList` — zuverlässigste Quelle |
| `hole_stadt_re()` | recklinghausen.de | ASP-Tabelle `<tr><td>`, Uhrzeit nur auf Detailseiten |
| `hole_altstadtschmiede()` | altstadtschmiede.de | JSON-LD `Event` (MEC WordPress Plugin) |
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

**Wartungshinweis:** Parser sind fragil gegenüber HTML-Strukturänderungen. Bei 0 Events aus einer Quelle: erst echte HTML-Struktur mit Debug-Script prüfen, nie auf Vermutungen basieren.

## Neue Quelle hinzufügen

1. Funktion in `scraper.py`: `hole_neue_quelle(jahr, monat) -> list[Termin]`
2. In `app.py` importieren und in `main()` aufrufen
3. `quelle`-String für Filterung setzen
4. Label in `QUELLEN`-Dict in `app.py` eintragen
5. Badge-CSS-Klasse `.badge-neuequelle` mit Farbgradient in `generiere_html()` ergänzen
6. Badge-Zuordnung in `badge_classes`-Dict in `generiere_html()` eintragen
7. Footer-Link in `generiere_html()` ergänzen
8. Optional: Toggle-Button falls Quelle viele Termine liefert — `toggleXyz()`-Funktion + `xyzAusgeblendet`-Variable + `xyzMatch`-Check in `filterTermine()` (Muster: siehe VHS/Kino-Toggle)
9. Quellentabelle in dieser CLAUDE.md aktualisieren
