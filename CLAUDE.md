# Termine Recklinghausen

Veranstaltungskalender für Recklinghausen aus 6 Quellen, automatisch aktualisiert.

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

## Automatische Aktualisierung

**Warum lokal?** Regionale Websites blockieren häufig Cloud-IPs (siehe Erfahrung mit Ratstermine und Veranstaltungen_MS).

```
06:30 Uhr: launchd startet update.sh
     → Scraping (6 Quellen, ~30 Sek)
     → HTML generieren
     → git push (falls Änderungen)
     → GitHub Actions → Pages Deployment
     → macOS-Benachrichtigung
```

### launchd-Konfiguration

```bash
launchctl list | grep termine-re           # Status prüfen
launchctl start de.termine-re.update       # Manuell auslösen
tail -f launchd.log                        # Live-Log
```

## Architektur

```
6 Webquellen → scraper.py → app.py → HTML-Dateien → GitHub Pages
```

### Quellen

| Funktion | Quelle | Methode | Events |
|----------|--------|---------|--------|
| `hole_regioactive()` | regioactive.de | JSON-LD ItemList | ~16/Monat |
| `hole_stadt_re()` | recklinghausen.de | ASP-Tabelle | ~40/Monat |
| `hole_altstadtschmiede()` | altstadtschmiede.de | JSON-LD Events | ~5/Monat |
| `hole_vesterleben()` | vesterleben.de | HTML + Stadtfilter | ~20/Monat |
| `hole_sternwarte()` | sternwarte-recklinghausen.de | `<p><u>/<strong>` Parsing | ~15/Monat |
| `hole_kunsthalle()` | kunsthalle-recklinghausen.de | Text-Parsing (DD.MM.) | ~4/Monat |

### Dateinamenmuster

- `termine_re_YYYY_MM.html` — Monatsdateien
- `index.html` — Redirect zum aktuellen Monat

## Neue Quelle hinzufügen

1. Funktion in `scraper.py`: `hole_neue_quelle(jahr, monat) -> list[Termin]`
2. In `app.py` importieren und in `main()` aufrufen
3. `quelle`-String für Filterung setzen
4. Label in `QUELLEN`-Dict in `app.py` eintragen
