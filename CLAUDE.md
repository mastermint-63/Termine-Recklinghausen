# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Ausführung

```bash
python3 app.py                    # 3 Monate ab heute, öffnet Browser
python3 app.py 2026 2             # 3 Monate ab Februar 2026
python3 app.py 2026 2 6           # 6 Monate ab Februar 2026
python3 app.py --no-browser       # Ohne Browser öffnen

./update.sh                       # Aktualisieren + Git Push + macOS-Benachrichtigung
./oeffne_aktuell.sh               # Aktuellen Monat im Browser öffnen
```

## GitHub Pages

- **Repository:** https://github.com/mastermint-63/Termine-Recklinghausen
- **Live URL:** https://mastermint-63.github.io/Termine-Recklinghausen/

## Architektur

```
6 Webquellen → scraper.py (Termin-Objekte) → app.py (HTML-Generierung) → GitHub Pages
```

**scraper.py** — Sechs unabhängige Scraper-Funktionen, jede gibt `list[Termin]` zurück. Gemeinsamer `Termin`-Dataclass mit Feldern: name, datum, uhrzeit, ort, link, beschreibung, quelle, kategorie.

**app.py** — Generiert standalone HTML-Dateien (`termine_re_YYYY_MM.html`) mit eingebettetem CSS + JS. Kein Build-System. Holzwurm-Design (warme Beige-/Orange-Töne), Dark Mode via `prefers-color-scheme`, Quellen-Filter per JavaScript.

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

## Quellen und Parsing-Details

| Funktion | Quelle | Parsing-Methode |
|----------|--------|-----------------|
| `hole_regioactive()` | regioactive.de | JSON-LD `ItemList` — zuverlässigste Quelle |
| `hole_stadt_re()` | recklinghausen.de | ASP-Tabelle `<tr><td>`, Uhrzeit nur auf Detailseiten |
| `hole_altstadtschmiede()` | altstadtschmiede.de | JSON-LD `Event` (MEC WordPress Plugin) |
| `hole_vesterleben()` | vesterleben.de | Link-Text-Parsing, PLZ-Zeile `NNNNN \| Stadt` für Stadtfilter |
| `hole_sternwarte()` | sternwarte-recklinghausen.de | `<p><u>Datum</u><strong>Titel</strong>` Struktur |
| `hole_kunsthalle()` | kunsthalle-recklinghausen.de | Zeilenweise: DD.MM. → Titel → Uhrzeit |

**Wartungshinweis:** Parser sind fragil gegenüber HTML-Strukturänderungen. Bei 0 Events aus einer Quelle: erst echte HTML-Struktur mit Debug-Script prüfen, nie auf Vermutungen basieren.

## Neue Quelle hinzufügen

1. Funktion in `scraper.py`: `hole_neue_quelle(jahr, monat) -> list[Termin]`
2. In `app.py` importieren und in `main()` aufrufen
3. `quelle`-String für Filterung setzen
4. Label in `QUELLEN`-Dict in `app.py` eintragen
5. Badge-CSS-Klasse `.badge-neuequelle` mit Farbgradient in `generiere_html()` ergänzen
