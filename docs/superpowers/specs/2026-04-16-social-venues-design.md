# Social-Media-Venues-Scraper — Design

**Datum:** 2026-04-16
**Status:** Entwurf → User-Review
**Projekt:** `Recklinghausen/`
**Follow-up:** Implementierungsplan via `writing-plans`

## Kontext

Sieben Veranstaltungsorte in Recklinghausen kommunizieren ihre Events ausschließlich über Facebook und Instagram — sie haben keine eigene Terminseite, erscheinen nicht in den bisher angebundenen Aggregatoren und fehlen dadurch auf der Seite `termine.holzwurm-recklinghausen.de`.

**Betroffene Venues:**

- SKANDAL Club (~9.500 IG-Follower) — größter Club in RE
- AKZ (Alternatives Kulturzentrum)
- UnFassBar
- Stadthafen / Strandbar
- Drübbelken
- Ratskeller
- Murphy's Pub

## Ziele

- Events dieser Venues erscheinen automatisiert auf der Terminseite
- Architektur ist replizierbar: neue Venue = Konfig-Eintrag, kein neuer Scraper-Code
- Qualität > Vollständigkeit: lieber Events verlieren als falsche publizieren
- Passt in bestehende `scraper.py`/`app.py`-Pipeline ohne Bruch

## Nicht-Ziele

- Keine Crowdsourcing-UI
- Kein Staging-Review vor Publikation (Direkt-Publish, vertrauend auf strikten Extraktions-Gate)
- Keine eigene Datenbank — Termine leben wie alle anderen nur im generierten HTML
- Keine Metriken-Erfassung über Extraktions-Qualität im POC
- Keine bezahlten Drittanbieter-Scraping-Dienste

## Constraints

- **Kosten:** Kostenlos / self-hosted; Wartungsbudget ~30 min/Monat
- **Plattformen:** Meta (Facebook/Instagram) blockt aktiv Scraper — Ausfälle einplanen
- **Rechtslage:** IG/FB-Scraping bleibt Grauzone; keine authentifizierten Sessions, keine Login-Simulation
- **Python 3.14** (Framework-Installation, Pfad `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`)
- **Bestehendes Muster:** Scraper folgen dem `hole_<quelle>(jahr, monat) -> list[Termin]`-Schema aus `scraper.py`

## Ansatzwahl

Playwright (headless Chromium) als Scraping-Engine, plus Claude Haiku für die Extraktion aus Instagram-Captions. Gesteuert über Venue-Profile (JSON), damit neue Venues per Konfig statt Code angebunden werden.

Begründet durch:

- Playwright existiert bereits im Workspace (`zeitungen_lesen/`) → bekannte Codebasis
- Gleiche Engine für IG und Facebook-Pages (mbasic.facebook.com-Pfad)
- Realistischer Browser-Fingerprint umgeht einfache Bot-Detection
- Facebook-Events-Pfad liefert strukturierte Daten (kein Claude nötig), Instagram-Pfad nutzt Claude nur als Fallback

Verworfen:

- **instaloader pur:** zu fragil gegen Meta-Blocks, kein FB-Support
- **RSS-Bridge:** zusätzliche Infrastruktur (Docker/PHP), überproportionaler Aufwand für POC
- **Bezahlte Services (Apify, ScraperAPI):** durch Kosten-Constraint ausgeschlossen
- **Meta Graph API:** App-Review-Pflicht, nur für eigene Seiten praktikabel

## Architektur

```
launchd 06:30 → update.sh → app.py::main()
                              │
                              ▼
                scraper.py::hole_social_venues(jahr, monat)
                              │
                              ▼
                iteriert über Recklinghausen/venue_profiles/*.json
                              │
      ┌───────────────────────┼───────────────────────┐
      ▼                       ▼                       ▼
_fetch_fb_events()     _fetch_ig_posts()       (weitere types
(Playwright,           (Playwright,             möglich, z.B.
strukturierte          anonym, max 30           "website")
Event-Cards)           Posts)
      │                       │
      │                       ▼
      │              _extract_event_from_caption()
      │              Claude Haiku, strict gate
      │                       │
      └───────────┬───────────┘
                  ▼
           list[Termin]
                  ▼
     bestehende Dedup + HTML-Pipeline
     in app.py (unverändert)
```

## Komponenten

| Komponente | Ort | Zweck |
|------------|-----|-------|
| `venue_profiles/<key>.json` | `Recklinghausen/venue_profiles/` | Pro-Venue-Konfiguration (Quellen, Defaults, Claude-Kontext) |
| `social_scraper.py` | `Recklinghausen/` | Playwright-Aufrufe + Claude-Extraktion gekapselt |
| `hole_social_venues()` | `Recklinghausen/scraper.py` | Dünner Wrapper, iteriert Profile, ruft `social_scraper.py` |
| `tests/test_caption_extraction.py` | `Recklinghausen/tests/` | Golden-Caption-Testfälle, deterministisch |
| `social_scraper.log` | `Recklinghausen/` (gitignored) | Fehler- und Aktivitäts-Log, 7 Tage rotierend |
| `social_scraper_state.json` | `Recklinghausen/` (gitignored) | 24h-Skip-Marker pro Venue nach Meta-Block |
| `venv/` | `Recklinghausen/venv/` | Eigenes Python-venv mit Playwright + `anthropic` |
| `.env` | `Recklinghausen/.env` (gitignored) | `ANTHROPIC_API_KEY` |

## Venue-Profil-Schema

```json
{
  "venue_key": "skandal",
  "label": "SKANDAL Club",
  "kategorie": "Party",
  "ort": "SKANDAL Club, Königswall 2, 45657 Recklinghausen",
  "default_uhrzeit": "22:00",
  "sources": [
    {
      "type": "facebook_events",
      "url": "https://www.facebook.com/skandalclub/events",
      "priority": 1
    },
    {
      "type": "instagram",
      "url": "https://www.instagram.com/skandalclub/",
      "priority": 2
    }
  ],
  "max_posts_to_scan": 30,
  "claude_context": "SKANDAL ist ein Club in Recklinghausen. Events fast ausschließlich Freitag- oder Samstagabend ab 22 Uhr. Ignoriere Rückblicke, Reposts, Merch-Werbung."
}
```

**Feldbedeutung:**

- `venue_key`: interner Schlüssel, wird zu `Termin.quelle` (für Filter-Dropdown, Badges, Dedup)
- `label`: Anzeigename in `QUELLEN`-Dict und Footer
- `kategorie`, `ort`, `default_uhrzeit`: Fallback-Werte, wenn Extraktion unvollständig
- `sources[]`: sortiert nach `priority`, erster erfolgreicher Treffer gewinnt
- `max_posts_to_scan`: Obergrenze pro IG-Lauf (Meta-Blockrisiko minimieren)
- `claude_context`: Venue-spezifischer Hintergrund für Extraktions-Prompt

## Datenfluss

Pro Venue-Profil:

1. **Profil laden**, `sources` nach `priority` sortieren
2. **Priorität 1 — Facebook Events:**
   - Playwright öffnet `facebook.com/<seite>/events` (ggf. mbasic-Variante)
   - Wenn Events-Section sichtbar und parsbar: `name`, `datum`, `uhrzeit`, `link` direkt aus strukturiertem Markup
   - `list[Termin]` → Schritt 4
   - Bei Login-Wall / Exception / 0 Events: → Priorität 2
3. **Priorität 2 — Instagram:**
   - Playwright öffnet Profilseite anonym
   - Scrollt bis `max_posts_to_scan` Posts geladen sind oder Login-Wall erscheint
   - Für jeden Post: `caption` extrahieren
   - Pro Caption: Claude Haiku mit `claude_context` + Gate-Prompt:

     > „Nur `ist_event: true` wenn Caption ein **zukünftiges** Datum (DD.MM.YYYY, oder deutscher Wochentag+Datum, oder eindeutiger Monat+Jahr) **und** einen erkennbaren Titel enthält. Rückblicke, Teaser ohne Datum, Merch, Reposts → `ist_event: false`."

   - Antwortformat: `{ist_event: bool, datum: ISO|null, name: str|null, uhrzeit: HH:MM|null}`
4. **Mapping zu `Termin`:** `ort` + `kategorie` aus Profil, `quelle` = `venue_key`, `beschreibung` = erste 400 Zeichen der Caption (HTML-escaped), `link` = Post-URL
5. **Rückgabe** an `hole_social_venues()` → bestehende Pipeline

## Fehlerbehandlung

| Fehlerquelle | Reaktion | Begründung |
|---|---|---|
| Playwright-Timeout / Navigation-Fehler | Log, überspringe Venue, return `[]` | Wie bestehende Quellen — keine Unterbrechung anderer Scraper |
| Login-Wall (Redirect auf `/accounts/login`) | Log mit Warnung, return `[]`, Priorität 2 probieren | Normaler IG-Zustand; Fallback hat ggf. noch Glück |
| Claude-API-Fehler / Rate-Limit | Log, überspringe diesen Post (nicht die ganze Venue) | Einzel-Fehler dürfen nicht alles killen |
| JSON-Parse-Fehler bei Claude-Antwort | Log, überspringe Post | Claude liefert manchmal abweichendes JSON-Format |
| Datum in Vergangenheit | Stiller Skip | Gate-Regel: nur Zukunfts-Events |
| Claude sagt `ist_event: false` | Stiller Skip | Normalfall, kein Log-Noise |
| Meta-Block (HTTP 429/403) | Log-Warnung, return `[]`, setze 24h-Skip-Marker in `social_scraper_state.json` | Verhindert dass wiederholte Läufe den Block verschärfen |
| `ANTHROPIC_API_KEY` fehlt | Fatal-Error mit klarer Meldung | Konfigurationsproblem, muss auffallen |

**Logging:** `social_scraper.log` (rotierend, 7 Tage), Kurz-Zusammenfassung in `launchd.log` (z.B. „SKANDAL: 3 Events, 12 Posts gescannt" oder „SKANDAL: Login-Wall, 0 Events").

## Testing

**Unit-Tests** (`tests/test_caption_extraction.py`) — deterministisch, ohne Netzwerk:

```python
CAPTIONS_POSITIV = [
    ("Freitag 29.03.2026, 22 Uhr: Abba Night 🎉 Einlass 21 Uhr, 10€",
     {"ist_event": True, "datum": "2026-03-29", "uhrzeit": "22:00", "name_contains": "Abba"}),
    ("Sa 05.04. — Techno im Keller mit DJ Xyz ab 23 Uhr",
     {"ist_event": True, "datum": "2026-04-05", "uhrzeit": "23:00", "name_contains": "Techno"}),
]

CAPTIONS_NEGATIV = [
    "Last summer! 🔥 Unvergessliche Abba-Night — wer war dabei?",
    "Bald geht's wieder los, Details folgen",
    "Neues Merch im Shop: T-Shirts 25€",
    "Freitag Party!",
]
```

Ansatz: gespeicherte Claude-Responses als Fixtures → Tests laufen ohne API-Key. Echter API-Call nur bei `pytest -m integration`. Bei jedem Scraper-Update: neue Real-World-Caption + erwartetes Ergebnis als Testfall aufnehmen.

**Integration-Test** (manuell, nicht in CI):

```bash
./venv/bin/python3 -m social_scraper skandal --dry-run
# Gibt extrahierte Events als JSON aus, schreibt nichts.
```

## Integration in bestehende Infrastruktur

**Python-Environment:**

- Eigenes venv in `Recklinghausen/venv/` (analog `zeitungen_lesen/venv/`)
- `requirements.txt` erweitern: `playwright`, `anthropic`
- Einmalig: `pip install -r requirements.txt && playwright install chromium`

**API-Key:**

- `Recklinghausen/.env` mit `ANTHROPIC_API_KEY` (nutzt existierenden Key aus `ki-ratsinfo/.env`)
- `.gitignore` prüfen: `.env` darf nicht committed werden

**`scraper.py`-Integration** (folgt der 10-Schritt-Checkliste aus `Recklinghausen/CLAUDE.md`):

1. `hole_social_venues(jahr, monat) -> list[Termin]` als dünner Wrapper
2. Import + Aufruf in `app.py::main()`
3. `quelle`-Strings pro Venue (`"skandal"`, später `"akz"` etc.)
4. `QUELLEN`-Dict: neue Einträge
5. `_QUELLEN_TIER`: bleibt Default (Tier 1) — Venues sind Veranstalter
6. Badge-CSS: **eine** gemeinsame Klasse `.badge-social` mit dunkelviolett→schwarz-Gradient für alle Social-Venues; im `badge_classes`-Dict werden alle `venue_key`s auf diese Klasse gemappt. (Abweichung vom Standard-Muster „ein Badge pro Quelle", bewusst, weil Social-Venues visuell als Gruppe erkennbar sein sollen und 7 neue Farbgradienten den Farbraum sprengen würden — nur 25 sind bisher belegt und müssen unterscheidbar bleiben.)
7. Footer-Link pro Venue (zeigt auf IG-/FB-Profil)

**launchd-Integration:**

- Kein neuer Job — `de.termine-re.update` (06:30) ruft `update.sh`, das ruft `app.py`, das ruft `hole_social_venues()`
- Einmal täglich, passt zum „free, may break monthly"-Budget
- Bei Problem: 24h-Skip-Marker in `social_scraper_state.json`

**`update.sh`-Anpassung:**

- Nutzt `./venv/bin/python3` statt System-Python

## Staging-Pfad (POC)

| Tag | Schritt |
|---|---|
| 1 | venue_profiles-Struktur, `social_scraper.py`, SKANDAL-Profil, Unit-Tests grün |
| 1 | `--dry-run` gegen echtes SKANDAL-Profil, Ergebnis manuell prüfen |
| 2 | Integration in `scraper.py` + `app.py`, ein produktiver Lauf, generiertes HTML prüfen |
| 3+ | Wenn stabil: AKZ-Profil dazu, dann schrittweise weitere Venues |

## Risiken & offene Punkte

- **Meta-Verhalten unklar:** Ob und wie oft Login-Wall oder Block zuschlägt, ist erst im POC-Lauf messbar. Worst case: Pipeline liefert dauerhaft 0 Events → dann Re-Evaluation, ob C-Wahl (vollautomatisch) überhaupt haltbar ist
- **Tool-Aktualität:** Playwright, `anthropic`-SDK, Meta-Seitenstruktur — 2026er Zustand nicht vorab verifiziert. Erste Sichtung vor Implementierung nötig
- **Hat SKANDAL eine FB-Events-Seite?** Wenn ja, Pfad Priorität 1 trivial; wenn nein, sofort auf IG-Caption-Parsing angewiesen. **Verifikationsschritt vor Implementierung**
- **Claude-Extraktions-Qualität:** Erst an echten SKANDAL-Captions messbar. Gate-Prompt wird iterativ nachgeschärft werden müssen
- **Badge-Farben:** Erst 25 Gradienten vergeben, neue Farbe darf keine Duplikat-Kollision haben (siehe `generiere_html()`)
