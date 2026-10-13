# Plan: Termineseite für Suchmaschinen und KI-Assistenten auffindbar machen

## Kontext

FS hat eine KI gefragt, was heute und morgen in Recklinghausen los ist. Ohne Hinweis hat sie den Holzwurm-Kalender nicht gefunden. Erst mit der Adresse kamen gute Antworten. Danach hat sie Verbesserungen vorgeschlagen. Dieser Plan ordnet die Vorschläge nach einer Prüfung am Code und an der Live-Seite (13.10.2026) ein. Er dient dem Holzwurm-Team als Entscheidungsgrundlage. Gebaut wird erst nach der Entscheidung.

## Stand 13.10.2026 (nach dem Testlauf)

- Vorschau für das HW-Team: https://seminar.reporter.ruhr/holzwurm-vorschau/ (noindex, befristete CSP-Ausnahme auf dem Seminarserver, siehe dortige `BETRIEB.md`).
- **iCal geändert (Entscheidung FS):** kein Abo-Feed `termine.ics` (562 Termine in 60 Tagen waren zu viel), sondern pro Termin eine eigene Datei `kalender/<id>.ics` mit Link „In meinen Kalender" (nicht bei Kino und Absagen). Paket 5 unten ist insoweit überholt.
- JSON-LD der Monatsseiten listet die Tagesseiten statt Events (Seite sonst über 100 KB länger); die Events stehen auf den Tagesseiten.
- Sortierung nach Beginn statt nach Text (vorher stand „19.30" vor „9:00").
- Offen vor Livegang: `update.sh` (neue Pfade committen), `deploy.yml`-Trigger, `CLAUDE.md`, Search Console/Bing, Rückmeldungen des Teams.

## Testlauf (Entscheidung FS, 13.10.2026)

Zuerst wird **eine Vorschau der Pakete 2-5** gebaut. Erst nach intensiver Begutachtung (FS, dann das Team) geht etwas live. Paket 1 (Datenqualität) folgt danach als eigener Schritt.

**Abschottung von der Live-Seite:**
- Arbeit auf einem Feature-Branch `auffindbarkeit` in `~/ki/dev/termine/re`. `main` und `prod` bleiben unberührt, kein Push auf `main`, kein `deploy`. `update.sh` läuft in `prod` und ist nicht betroffen.
- `app.py` bekommt die Option `--ausgabe <ordner>`. Ohne Option bleibt das Verhalten exakt wie heute, damit der nächtliche Lauf nach einem späteren Deploy nicht anders reagiert. Die Vorschau landet in `vorschau/` (git-ignoriert). Die versionierten `termine_re_*.html`, `index.html` und `sitemap.xml` im Projekt werden **nicht** überschrieben.
- Die Option `--termine-cache <datei>` speichert die gescrapten Termine nach dem ersten Lauf und lädt sie bei weiteren Läufen. So kosten Korrekturrunden während der Begutachtung keinen erneuten Abruf von 45 Quellen (und kein Apify-Guthaben).

**Damit die Vorschau auf dem Laptop ohne Server funktioniert:**
- Flache Dateien statt Ordner-URLs: `heute.html`, `morgen.html`, `wochenende.html`, `tag/2026-10-13.html`. GitHub Pages liefert sie später auch unter `/heute` aus *(beim Livegang verifizieren)*. Ordner-URLs würden lokal nur ein Verzeichnis zeigen.
- Alle internen Links relativ (`../termine_re_2026_10.html`). Nur Canonical, og:url, Sitemap und JSON-LD-URLs bleiben absolut auf `termine.holzwurm-recklinghausen.de`.
- Übergabe: `vorschau/` plus `vorschau.zip`. FS holt sich das Zip per Hermes auf den Laptop, entpackt es und öffnet `index.html` im Browser.
- Umami in der Vorschau abschalten (der Vorschau-Ordner bekommt kein Tracking-Skript), sonst verfälscht die Begutachtung die Statistik.

**Vorläufige Annahmen für die offenen Teamfragen** (in der Vorschau sichtbar, später änderbar):
- Kino: Monatsseiten unverändert. Auf den Tagesseiten nur eine Sammelzeile mit Link zur Monatsseite.
- Beschreibungen: unverändert 800 Zeichen. Kürzen ist eine eigene Teamentscheidung.

**Umsetzungsschritte (TDD, Tests ohne Netz):**
1. Branch, `vorschau/` in `.gitignore`, Optionen `--ausgabe` und `--termine-cache` in `main()` (`app.py` ab Zeile 1833, `basis_pfad` Zeile 1849).
2. Darstellung eines einzelnen Termins aus `generiere_html()` (Zeilen 582-1821) in eine Hilfsfunktion herauslösen, die Monats- und Tagesseiten gemeinsam nutzen. Danach müssen die Monatsseiten byte-gleich bleiben (Vergleich mit dem Stand vor dem Umbau, gleicher Termin-Cache).
3. Tagesseiten-Generator: Titel nach Suchmuster, Vortag/Folgetag/Monat, Kino-Sammelzeile, Spotlight-Karten, Absage-Darstellung wie heute, schlankes HTML mit gemeinsamer `stil.css`.
4. `heute.html`/`morgen.html`/`wochenende.html` mit Datums-Weiterleitung per JavaScript, falls die Seite älter als der aktuelle Tag ist.
5. Startseite mit eigenem Inhalt („Heute und die nächsten Tage", Links zu Monaten und Tagen), neue Titel und Beschreibungen (Paket 2).
6. JSON-LD (Paket 4): Absagen mit `EventCancelled`, Adresse und Veranstalter wo bekannt, Kino auf den Tagesseiten nicht als Einzel-Events.
7. `termine.ics` (kommende 60 Tage, ohne Kino) und `llms.txt` (Paket 5). Sitemap mit Tagesseiten.
8. Vorschau bauen, selbst prüfen (Links, Größen, JSON-LD-Validierung, iCal-Import), Zip erstellen, Pfade nennen.

Nicht im Testlauf: `update.sh`, `deploy.yml`, IndexNow, Search Console. Das kommt erst mit dem Livegang.

## Was die KI richtig sieht und was nicht (geprüft am 13.10.2026)

| Aussage der KI | Befund |
|---|---|
| Sitemap hat nur 6 Adressen | **Stimmt.** Startseite plus 5 Monatsseiten (`app.py` ab Zeile 1904) |
| Monatsseiten sind sehr lang | **Stimmt.** Oktober: 582 KB, 610 Termine. KI-Werkzeuge kürzen solche Seiten (die KI brach am 27.10. ab) |
| Kino dominiert | **Stimmt.** 318 von 610 Terminen im Oktober (52 %) sind Cineworld. Ausgeblendet wird nur per JavaScript. Im HTML und im JSON-LD stehen alle Filme, und Crawler sehen sie |
| Startseite und Oktoberseite sind doppelt | **Stimmt.** `index.html` ist eine Kopie der Monatsseite mit eigenem Canonical. Damit konkurrieren zwei gleiche Seiten |
| Fahrradcodierung 12:00 statt 14-17 Uhr | **Stimmt** (ADFC-Daten, Beschreibung sagt 14.00 bis 17.00) |
| Speichengeflüster 16:30 statt 18:30 | **Stimmt** (ADFC-Daten, Beschreibung sagt 18.30) |
| Rathausshow steht bei 18:00, im Text 20 und 21 Uhr | **Nur zum Teil.** Der Kurztext „am Eröffnungsabend: 20 und 21 Uhr" steht bei *jedem* Vorkommen, auch an den anderen Tagen. Ob 18:00 dort stimmt, muss an der Quelle geprüft werden. Wahrscheinlich ist der Kurztext falsch zugeordnet, nicht die Uhrzeit |
| Sternwarten-Vortrag 12.10. entfällt | **Stimmt.** Im Text steht „entfällt", der Termin ist aber nicht als abgesagt markiert |
| Altstadtschmiede-Session auf 20.12. verschoben | **Nicht gefunden** in unseren Daten. Muss an der Quelle geprüft werden |
| Abgeschnittener Titel „Zwangsarbeiter … in" | **Stimmt** (vesterleben.de) |
| KI-Crawler geblockt? | **Nein.** GitHub Pages ohne CDN. GPTBot und ClaudeBot bekommen eine 200, und `robots.txt` erlaubt alles. Getestet nur von hier aus |
| Verlinkung | Die Holzwurm-Hauptseite verlinkt den Kalender. Andere Verweise sind nicht geprüft |
| „Der Holzwurm ist ein Veranstaltungskalender" | Verkürzt. Das zeigt aber gerade das Markenproblem |

Grenzen der KI-Aussagen: Ihre Suchmaschine war nach eigener Angabe nicht Google, und es war ein Einzeltest. Das Muster ist trotzdem plausibel, denn Assistenten lesen ganze Seiten und keine Sprungmarken.

## Maßnahmen, nach Wirkung pro Aufwand sortiert

### Paket 1: Datenqualität (Empfehlung: ja, zuerst)
Hilft allen Lesern und nicht nur Maschinen. Die Grundlagen dafür gibt es schon (`Termin.abgesagt`, `korrekturen.json`, Signal-Bericht).
- **1a Absagen im Text erkennen:** Beschreibung und Titel nach „entfällt", „fällt aus", „abgesagt" und „verschoben" durchsuchen. Bei klaren Formulierungen („Dieser Vortrag entfällt") wird der Termin als abgesagt markiert, sonst kommt nur ein Hinweis in den Signal-Bericht. Ort: `app.py` vor `entferne_duplikate()`, wie `wende_korrekturen_an()`.
- **1b Uhrzeit-Plausibilität:** Uhrzeiten im Text mit dem Uhrzeit-Feld abgleichen. Abweichungen kommen in den Signal-Bericht und werden nicht automatisch geändert. Für ADFC klären, ob die API ein anderes Zeitfeld liefert (`_adfc_fetch`), und dann im Scraper beheben.
- **1c RE-leuchtet:** Den Kurztext nur beim passenden Vorkommen zeigen oder weglassen (`hole_re_leuchtet`), vorher an der Quelle prüfen.
- **1d vesterleben:** Abgeschnittene Titel und den Ort „nur Recklinghausen" prüfen, gegebenenfalls die Detailseite nachladen (`hole_vesterleben`).
- Aufwand: mittel, ca. 150-300k Token, Sonnet reicht.

### Paket 2: Startseite und Marke (Empfehlung: ja, klein)
- Die Startseite bekommt eigenen Inhalt (siehe Paket 3: „Heute und die nächsten Tage" mit Links zu Monaten und Tagen) statt einer Kopie des Monats. Wird Paket 3 abgelehnt, zeigt der Canonical der Startseite auf die aktuelle Monatsseite.
- Titel nach dem, was Leute suchen: „Veranstaltungen in Recklinghausen im Oktober 2026 - Veranstaltungskalender | Holzwurm". „Veranstaltungskalender Recklinghausen" gehört in die Überschrift.
- Aufwand: klein, ca. 30-60k Token.

### Paket 3: Tagesseiten (Empfehlung: ja, die eigentliche Hebelmaßnahme)
- Jeder Tag bekommt eine eigene Seite unter `/tag/2026-10-13/` (Ordner mit `index.html`, damit die Adresse sauber bleibt). Dazu kommen `/heute/`, `/morgen/` und `/wochenende/`. Titel: „Veranstaltungen in Recklinghausen am Dienstag, 13. Oktober 2026".
- Inhalt: die Termine des Tages **ohne Einzelfilme**. Stattdessen steht dort eine Zeile „Kino: Cineworld zeigt heute 14 Filme" mit Link. Dazu Event-JSON-LD (siehe Paket 4), Links zum Vortag, zum Folgetag und zum Monat. Schlankes HTML, CSS als gemeinsame Datei statt eingebettet.
- Die Sitemap enthält alle Tagesseiten, ca. 150.
- **Stolpersteine:**
  - `/heute/` wird um 06:30 neu gebaut und zeigt zwischen 0 und 6:30 Uhr den Vortag. Lösung: Ein kleines Skript auf der Seite prüft das Datum und springt auf den richtigen Tag. Ein zusätzlicher Job um 00:05 wäre die Alternative, braucht aber Absprache (neuer launchd-Job).
  - Repo-Wachstum: Nur Dateien schreiben, deren Inhalt sich geändert hat. Sonst ändert jeder Lauf 150 Dateien, nur weil „Stand: heute" drinsteht.
- Optional später: Kategorieseiten (Konzerte, Kinder, Politik). Dafür müssen die Kategorien vereinheitlicht werden, das ist ein eigenes Paket.
- Aufwand: groß, ca. 400-800k Token, Sonnet für die Umsetzung, Opus für das Design. Die Konvention dafür sind Spec und Plan unter `docs/superpowers/`.

### Paket 4: Besseres JSON-LD (Empfehlung: ja, zusammen mit Paket 3)
Heute steht pro Monatsseite eine `ItemList` mit allen Events, Kino eingeschlossen, Absagen ausgelassen.
- Abgesagte Termine aufnehmen, mit `eventStatus: EventCancelled`. Das ist genau die Information, die KIs brauchen.
- `eventAttendanceMode`, Ort mit Straße, wo sie bekannt ist, `organizer` aus der Quelle, `url` zur Originalquelle.
- Auf den Monatsseiten Kino aus dem JSON-LD nehmen oder kürzen.
- Ob Google Event-Rich-Results 2026 noch so anzeigt wie früher, ist *(Quelle zu verifizieren)*. Für KIs lohnt es sich unabhängig davon.

### Paket 5: Feeds (Empfehlung: iCal ja, llms.txt optional)
- Ein **iCal-Abo** (`termine.ics`, kommende 60 Tage, ohne Kino). Das ist auch für Menschen nützlich (Abo in der Kalender-App). Die ICS-Logik ist zum Lesen schon vorhanden.
- `llms.txt`: kurze Beschreibung plus Links zu `/heute/` und den Feeds. Der Nutzen ist nicht belegt, der Aufwand winzig.
- Aufwand: klein bis mittel, ca. 80-150k Token.

### Paket 6: Indexierung und Messung (vor allem Arbeit des Teams, wenig Code)
- **Google Search Console und Bing Webmaster Tools** anmelden. Die Verifizierung geht per DNS-TXT-Eintrag beim Domain-Inhaber oder per HTML-Datei im Repo (das kann ich vorbereiten).
- **IndexNow** (Bing, Yandex u. a., Google nicht): Schlüsseldatei ins Repo, neue oder geänderte Tagesseiten nach dem Push aus `update.sh` melden. Ergibt erst mit Paket 3 Sinn.
- **Messen:** Umami ist eingebunden (`app.py` Zeile 838). Verweise von chatgpt.com, perplexity.ai, bing.com und gemini.google.com dort beobachten. Dazu alle 2 Wochen ein fester Testsatz in 4 Assistenten mit Protokoll.

### Paket 7: Verlinkung (nur Team, kein Code)
Um Links bitten bei Stadt, VHS, Altstadtschmiede, Sternwarte und Lokalmedien. Laut der KI bringt das mehr als jede Technik. Das ist plausibel, aber nicht belegt.

### Bewusst nicht empfohlen (vorerst)
- **Eine eigene Seite pro Termin:** Bei ca. 300 Terminen ohne Kino pro Monat wären das mehrere tausend dünne Seiten, viele mit fast nur übernommenem Text. Hohe Repo-Last, Gefahr von Duplicate Content. Die Tagesseiten mit JSON-LD decken den Bedarf großteils ab. Über eine Neubewertung nach 3 Monaten Messung entscheiden.
- **KI-Zusammenfassungen statt Originaltexten:** API-Kosten pro Termin und neue Fehlerquelle (erfundene Details). Günstiger ist es, die Beschreibungen von heute 800 auf ca. 300 Zeichen zu kürzen, mit Link zur Quelle. Zur Rechtslage nur so viel: Reine Termin-Fakten sind kaum schutzfähig, längere Werbetexte womöglich schon *(Quelle zu verifizieren, keine Rechtsberatung)*.

## Entscheidungsfragen für das Holzwurm-Team

1. Welche Pakete? Meine Empfehlung: 1, 2, 3+4 zusammen, dann 5. Paket 6 und 7 parallel durch das Team.
2. Kino: Bleibt Kino auf den Monatsseiten wie heute (sichtbar per Schalter), oder bekommt es eine eigene Kinoseite? Auf den Tagesseiten empfehle ich die Sammelzeile.
3. Absagen: automatisch durchstreichen bei klarer Formulierung (Risiko: Fehlalarm) oder nur melden und von Hand bestätigen?
4. Beschreibungen kürzen (800 auf ca. 300 Zeichen)?
5. Wer meldet die Domain bei Google und Bing an, und wer hat Zugriff auf die DNS-Einträge von holzwurm-recklinghausen.de?

## Kritische Dateien

- `app.py`: `generiere_html()` (ab ca. Zeile 785), `main()` mit Index- und Sitemap-Erzeugung (ca. 1896-1920), JSON-LD-Block, `_QUELLEN_TIER`, `wende_korrekturen_an()` als Muster für 1a
- `scraper.py`: `hole_adfc`/`_adfc_fetch`, `hole_re_leuchtet`, `hole_vesterleben`
- `update.sh`: committet bisher nur `termine_re_*.html`, `index.html` und `sitemap.xml`. Für Tagesseiten, Feeds und IndexNow muss das erweitert werden
- `.github/workflows/deploy.yml`: Der Trigger reagiert bisher nur auf `termine_re_*.html`/`index.html` und muss neue Pfade kennen
- `hw_bericht.py`: neue Zeilen für Plausibilitätswarnungen
- Tests: neue Dateien unter `tests/` nach dem Muster `test_korrekturen_app.py`, ohne Netz

## Verifikation (je Paket)

- `.venv/bin/python -m pytest tests/ -v` (heute 249 Tests grün, die müssen bleiben)
- `.venv/bin/python app.py --no-browser` lokal, dann Tagesseiten, `/heute/` und Sitemap ansehen und die Größe einer Tagesseite messen
- JSON-LD mit dem Schema.org-Validator bzw. dem Google Rich Results Test prüfen
- Vor dem Push: `git diff --stat` nach einem zweiten Lauf ohne Datenänderung. Dabei dürfen keine Tagesseiten-Diffs entstehen
- Nach Livegang: `curl` auf `/heute/` und eine Tagesseite, in der Search Console die Sitemap einreichen, nach 2-4 Wochen den Testsatz und die Umami-Verweise auswerten

## Nach Freigabe

Diesen Plan als `docs/termineseite-auffindbarkeit-plan.md` ins Projekt legen (für das Team als Markdown). Für Paket 3 vorher eine eigene Spec unter `docs/superpowers/specs/`.
