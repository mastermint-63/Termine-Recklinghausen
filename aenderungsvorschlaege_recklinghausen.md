# Code-Review: `/Users/fs/claude/Termine/Recklinghausen`

## Befunde (nach Schweregrad)

### 1. Kritisch: Potenzielle Stored-XSS durch ungefilterte externe Daten in HTML
- Fundstellen:
  - `/Users/fs/claude/Termine/Recklinghausen/app.py:219`
  - `/Users/fs/claude/Termine/Recklinghausen/app.py:221`
  - `/Users/fs/claude/Termine/Recklinghausen/app.py:233`
  - `/Users/fs/claude/Termine/Recklinghausen/app.py:239`
  - `/Users/fs/claude/Termine/Recklinghausen/app.py:256`
- Problem:
  - `t.name`, `t.ort`, `t.uhrzeit`, `t.link` und teilweise Labels werden direkt in HTML eingesetzt.
  - Diese Werte stammen aus externen Webseiten/APIs (Scraping) und sind damit nicht vertrauenswürdig.
  - Ein manipulierter Quellinhalt kann HTML/JS einschleusen.
- Empfehlung:
  - Zentralen Escape-Helper einführen (`html.escape(..., quote=True)`) für alle Textfelder.
  - URL-Felder strikt validieren (nur `http`/`https` erlauben, sonst auf `#` oder leer setzen).
  - HTML nur aus strikt kontrollierten Template-Bausteinen zusammensetzen.

### 2. Hoch: `target="_blank"` ohne `rel="noopener noreferrer"`
- Fundstellen:
  - `/Users/fs/claude/Termine/Recklinghausen/app.py:219`
  - `/Users/fs/claude/Termine/Recklinghausen/app.py:864`
- Problem:
  - Externe Links mit `target="_blank"` ohne `rel` erlauben Tabnabbing über `window.opener`.
- Empfehlung:
  - Bei allen externen Links immer `rel="noopener noreferrer"` ergänzen.

### 3. Mittel: Fehlerrobustheit in `update.sh` ist lückenhaft
- Fundstellen:
  - `/Users/fs/claude/Termine/Recklinghausen/update.sh:1`
  - `/Users/fs/claude/Termine/Recklinghausen/update.sh:22`
  - `/Users/fs/claude/Termine/Recklinghausen/update.sh:48`
- Problem:
  - Kein `set -euo pipefail`.
  - Exit-Code von `python3 app.py` wird nicht hart ausgewertet; das Skript läuft auch bei Teilfehlern weiter.
  - `git commit`-Fehler werden nicht sauber behandelt (nur Ausgabe).
- Empfehlung:
  - `set -euo pipefail` aktivieren.
  - Kritische Schritte mit expliziten Prüfungen absichern (Scrape, Commit, Push).
  - Bei Fehlern klaren Status setzen und in Notification ausgeben.

### 4. Mittel: Abhängigkeiten nicht versioniert (Supply-Chain/Build-Reproduzierbarkeit)
- Fundstelle:
  - `/Users/fs/claude/Termine/Recklinghausen/requirements.txt:1`
- Problem:
  - Ungepinntes `requests`, `beautifulsoup4`, `lxml` führt zu nicht reproduzierbaren Builds und erhöhtes Risiko bei Breaking Changes.
- Empfehlung:
  - Versionen pinnen (`==`) oder mindestens obere Grenzen setzen.
  - Optional: getrennte `requirements.in` + lock-Datei (z. B. via `pip-tools`).

### 5. Mittel: Keine Retry-/Backoff-Strategie bei Netzwerkzugriffen
- Fundstellen:
  - `/Users/fs/claude/Termine/Recklinghausen/scraper.py:93`
  - `/Users/fs/claude/Termine/Recklinghausen/scraper.py:173`
  - `/Users/fs/claude/Termine/Recklinghausen/scraper.py:1844`
- Problem:
  - Viele direkte `requests.get(..., timeout=...)`-Aufrufe ohne Retry.
  - Temporäre 429/5xx/Netzfehler reduzieren Datenqualität und Stabilität.
- Empfehlung:
  - Eine gemeinsame `requests.Session` mit `HTTPAdapter` + Retry (exponentielles Backoff) nutzen.
  - Einheitliches Error-Logging mit Quelle, Statuscode, URL und Laufzeit.

### 6. Niedrig: Eingabevalidierung in `app.py` fehlt
- Fundstellen:
  - `/Users/fs/claude/Termine/Recklinghausen/app.py:997`
  - `/Users/fs/claude/Termine/Recklinghausen/app.py:998`
  - `/Users/fs/claude/Termine/Recklinghausen/app.py:999`
- Problem:
  - CLI-Parameter werden per `int(...)` geparst, aber nicht auf Wertebereiche geprüft (z. B. Monat 0/13, negative Monatsanzahl).
- Empfehlung:
  - `argparse` mit validierten Bereichen verwenden (Monat 1-12, Monate >0).
  - Benutzerfreundliche Fehlermeldungen statt Stacktrace.

### 7. Niedrig: Deduplizierung kann fachlich zu aggressiv sein
- Fundstellen:
  - `/Users/fs/claude/Termine/Recklinghausen/app.py:112`
  - `/Users/fs/claude/Termine/Recklinghausen/app.py:113`
- Problem:
  - Duplikatlogik nutzt Teilstring-Matches (`norm_k in norm_v`), dadurch können verschiedene Veranstaltungen am selben Tag zusammenfallen.
- Empfehlung:
  - Ähnlichkeitsprüfung enger fassen (z. B. normalisierter Titel + Uhrzeitfenster + Ort).
  - Optional: konservativer Modus mit manueller Review-Liste für fragliche Merges.

## Eleganz- und Architekturverbesserungen

1. HTML-Generierung von String-Konkatenation auf Template-Engine umstellen (z. B. Jinja2), um Escape/Rendering zu zentralisieren.
2. Quellenkonfiguration als Datenstruktur (Liste/Dict) statt langer, manueller `main()`-Aufrufkette; reduziert Copy/Paste-Fehler.
3. Scraper-Aufrufe parallelisieren (z. B. `concurrent.futures.ThreadPoolExecutor`), um Laufzeit deutlich zu reduzieren.
4. Gemeinsame Helfer für Logging, Request-Handling und Parsing-Wiederholungen schaffen, um Redundanz in `scraper.py` zu senken.
5. Tests ergänzen: Parser-Smoke-Tests mit gespeicherten HTML/JSON-Fixtures plus XSS-Regressionstest für HTML-Ausgabe.

## Kurzfazit
- Funktional ist das Projekt gut strukturiert und produktionsnah automatisiert.
- Größter Handlungsbedarf liegt bei Output-Sanitizing (XSS) und Link-Härtung (`noopener noreferrer`).
- Danach lohnen sich Robustheitsmaßnahmen in `update.sh` und beim Netzwerk-Layer.
