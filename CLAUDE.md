# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Ausführung

```bash
# Python-Pfad (System nutzt 3.14 Framework-Installation)
.venv/bin/python app.py --no-browser

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
rund 35 Quellen → scraper.py (Termin-Objekte) → app.py (HTML-Generierung) → GitHub Pages
```

(Die genaue Quellenzahl driftet mit jeder neuen Quelle — maßgeblich ist die `SCRAPER`-Liste in `app.py`, nicht die Zahl in dieser Doku.)

**scraper.py** — rund 35 `hole_*()`-Scraper-Funktionen, jede gibt `list[Termin]` zurück. Gemeinsamer `Termin`-Dataclass mit Feldern: name, datum, uhrzeit, ort, link, beschreibung, quelle, kategorie. Wichtige Shared Helpers: `_im_monat(datum, jahr, monat)` prüft ob ein Termin im Zielmonat liegt; `_hole_events_calendar(url, quelle, kategorie, jahr, monat)` extrahiert JSON-LD Events (The Events Calendar / MEC Plugin) — wird von NLGR, Literaturtage, Altstadtschmiede und Backyard genutzt; `_adfc_fetch(unit_key, event_type)` holt ADFC-Events per JSON-API; `_ics_unfold/wert/datum` parsen ICS-Feeds.

**app.py** — Generiert standalone HTML-Dateien (`termine_re_YYYY_MM.html`) mit eingebettetem CSS + JS. Kein Build-System. Holzwurm-Design (warme Beige-/Orange-Töne), Dark Mode via `prefers-color-scheme`. Jeder Termin hat `data-quelle` Attribut für JavaScript-Filterung: Quellen-Dropdown + Toggle-Buttons (VHS, Kino) zum Ausblenden dominanter Quellen. VHS und Kino sind **beim Seitenaufruf immer ausgeblendet** (kein localStorage). Filterleiste ist `position: sticky` mit Milchglas-Effekt (`backdrop-filter: blur`). Beim Direktaufruf springt JS automatisch zum ersten heutigen oder zukünftigen Termin (sofern kein Anker in der URL); Monatsnavigation-Links tragen `#top` → Browser scrollt nach oben, Auto-Sprung wird unterdrückt. Canonical-URL und og:url zeigen auf die jeweilige Monatsdatei (`/termine_re_YYYY_MM.html`), nicht auf die Root-URL. `generiere_html()` erwartet `dateiname`-Parameter für die Canonical-URL. Kalender markiert den heutigen Tag per JS (`kal-heute`-Klasse). Deduplizierung über `entferne_duplikate()` (`app.py`): gleiches Datum + normalisierter Name (exakt oder Teilstring) → Eintrag mit besserem Info-Score wird behalten, **fehlende Felder (beschreibung, uhrzeit, ort) werden aus dem Duplikat ergänzt** (link wird nie überschrieben). **`_QUELLEN_TIER`** unterscheidet Aggregatoren (Tier 2: `stadt-re`, `vesterleben`, `recklinghaeuser`, `facebook`) von Veranstaltern (Tier 1 = Default): Aggregatoren bekommen −10 Score-Malus, sodass spezifische Veranstalter (NLGR, Altstadtschmiede usw.) immer gewinnen, auch wenn der Aggregator mehr Felder gefüllt hat. (z.B. Stadtarchiv-PDF liefert Uhrzeit, stad-re-Kalender liefert Beschreibung). Die **Footer-Quellenlinks** stammen aus der modulweiten Konstante `FOOTER_QUELLEN` (Liste von `(Anzeigename, URL)`-Tupeln) und werden in `generiere_html()` alphabetisch (case-insensitiv) gerendert — beim Hinzufügen einer Quelle dort eintragen, Reihenfolge egal.

**Spotlight-Karten (redaktionelle Highlights):** Einträge in `manuelle_termine.json` mit Feld `"highlight": "<key>"` (z.B. `holzwurm50` — 50 Jahre Holzwurm am 18.09.2026) werden pro Tag zu **einer** Gold-Karte gebündelt statt als Einzeltermine zu erscheinen. Kartentexte (Jahre, Titel, Untertitel, Meta, Fußzeile, Link, Bild) stehen in der modulweiten Konstante `HIGHLIGHTS` in `app.py`; die Timeline-Punkte kommen aus den Terminen selbst (uhrzeit/name/beschreibung). Highlight-Termine bekommen **+100 in `_termin_score()`** und gewinnen damit jedes Duplikat (z.B. wenn die Altstadtschmiede dieselben Events später selbst listet). Die Karte ist von der Quellen-Filterung **ausgenommen** (immer sichtbar, kein `.termin`-Element); ihre Termine zählen über `data-events` in den Sichtbar-Zähler, und eine `datum-gruppe` mit Spotlight-Karte wird nie ausgeblendet. Die Karten-Bilder `hebbert/hebbert-winkend.png` (Original-Hebbert) und `hebbert/hebbert-signatur.png` (handschriftliche Unterschrift in der Fußzeile; hell via `mix-blend-mode: multiply`, dunkel via `invert(1)` + `screen` eingeblendet) sind aus der Jubiläumseinladung per PyMuPDF extrahiert und müssen im Repo getrackt sein. In JSON-LD und Termin-Gesamtzahl erscheinen die Events weiterhin einzeln.

**Redaktionelle Inhaltsfilter** (in `app.py`, **vor** der Deduplizierung in `main()` aufgerufen, greifen über alle Quellen): `entferne_ausgeschlossene()` filtert AfD/demokratiefeindliche Gruppierungen (`_AUSGESCHLOSSENE_MUSTER`), `entferne_werbung()` filtert kommerzielle Einzelhandelswerbung aus Facebook-Terminen (`ist_werbung()`, nur `quelle == 'facebook'`). Details + Erweiterungsregeln (Wortgrenzen, Fehlalarm-Gegenprobe): siehe `../CLAUDE.md` (Abschnitte „Redaktioneller Inhaltsfilter" + „Werbefilter").

**Deduplizierung ist 3-stufig** (alle Stufen in `entferne_duplikate()` in `app.py`): Stufe 2 und 3 greifen **nur zwischen verschiedenen Quellen** — eine Quelle listet keine Termine doppelt, sonst verschmolzen z. B. „Rathausshow“ und „Drohnenshow am Rathaus“ (beide RE leuchtet). Regressionstests mit echten Paaren: `tests/test_dedup_fehlalarme.py`.
1. **Exakt/Teilstring** — normalisierter Name identisch oder einer enthält den anderen (gleicher Tag)
2. **Fuzzy** — beide Namen ≥4 Wörter + SequenceMatcher ≥0.75 + Jaccard-Koeffizient ≥0.70
3. **Markantes Schlüsselwort** (`_hat_markantes_schluesselwort()`) — mindestens ein Wort ≥5 Zeichen, das nicht in der ~175-Wörter-Stoppwortliste steht, kommt in beiden Namen vor; Zusammenschreibungen (`discofox` ≈ `disco fox`) zählen nur, wenn der Treffer an Wortgrenzen beginnt und endet (`_an_wortgrenzen()`, lange Wörter dürfen am Ende gebeugt sein: `seniorenbeirat` ≈ `seniorenbeirates`) — vorher traf `gustav` in `gustave`; Stoppwörter umfassen Artikel, Präpositionen, Event-Generika (party, workshop, live, show, night) und VHS-Generika (anfänger, fortgeschrittene) Beschreibungen werden auf 800 Zeichen begrenzt; bei Terminen mit Link und langer Beschreibung (>120 Zeichen) erscheint ein aufklappbarer Text mit `termin-beschreibung-mehr`-Klasse und `onclick`-Toggle.

**update.sh** — Tägliche Automation: Scraping → Löschroutine für alte Dateien → Event-Count-Diff → bedingter Git Push → macOS-Benachrichtigung via terminal-notifier. Nutzt Python 3.14 Framework-Pfad. Dateien älter als der Vormonat werden automatisch per `git rm` entfernt und im gleichen Commit mitgepusht (1-Monats-Puffer: Vormonat bleibt erhalten).

> ⚠️ **Wichtig:** `update.sh` committet **nur die generierten HTML-Dateien** (`termine_re_*.html`, `index.html`, `sitemap.xml`), **nicht** den Quellcode. Nach Änderungen an `app.py`/`scraper.py`/`CLAUDE.md` diese **separat** committen und pushen — sonst zeigt die Live-Seite zwar den neuen Stand, aber der erzeugende Code bleibt unversioniert (Repo-Drift).

### Automatische Aktualisierung

Lokales Scraping via launchd (bestimmte Cloud-IPs werden blockiert, z.B. GitHub Actions/Azure → 503; Hetzner Falkenstein war 04/2026 OK – kann sich ändern).

```
06:30 Uhr: launchd (de.termine-re.update) → update.sh → git push → GitHub Actions → Pages
```

```bash
launchctl list | grep termine-re           # Status prüfen
launchctl start de.termine-re.update       # Manuell auslösen
tail -f launchd.log                        # Live-Log
```

## HW-Import (Kalender-Eingang, eM-Client-Kategorie „HW" und automatische Presse-Erkennung)

Die Redaktion (FS, Ralf, Erich, Klaus) schickt Termine, Korrekturen, Absagen, Plakatfotos und Terminseiten per Mail. `hw_import.py` liest sie nachts aus und pflegt sie ein. Drei Quellen:

1. **Kalender-Eingang (seit 10/2026, Spec `docs/superpowers/specs/2026-10-10-kalender-eingang-design.md`):** Die Redaktion schreibt an einen iCloud-Alias von FS. Eine iCloud-Serverregel verschiebt diese Mails in den IMAP-Ordner `Kalender-Eingang`. Merkmal ist der **Ordner**, nicht die Empfängerzeile (iCloud setzt kein `Delivered-To`). Gelesen wird direkt per IMAP (`kalender_eingang.py`, eigenes `imaplib`-Modul, keine Abhängigkeit von `prod/mail`), weil eM Client Ordner außerhalb des Posteingangs teils tagelang verspätet synchronisiert. Lesen ohne Flags: `SELECT … readonly`, `BODY.PEEK[]` (iCloud liefert bei `RFC822` leer), Suche `UNDELETED`, Fenster 30 Tage, State-Schlüssel `kalender:<Message-ID>`. Seit 13.10.2026 wandern ausgewertete Mails nach `Kalender-Eingang/bearbeitet` und vertraute Absender bekommen eine Rückmeldung (siehe unten „Ablage und Rückmeldung“). Der Mail-Organizer arbeitet nur im Posteingang und fasst den Ordner nicht an.
2. **eM Client, Kategorie „HW":** FS markiert Mails anderer Absender (Vereine, externe Veranstalter) in eM Client.
3. **eM Client, Presse-Erkennung:** siehe unten.

> **Öffentliches Repo:** Alias und Absenderadressen stehen **nur** in `prod/termine/secrets/termine-hw.env` (`ICLOUD_USER`, `ICLOUD_APP_PASSWORD` = eigenes app-spezifisches Passwort nur für diesen Job, `KALENDER_ALIAS` = die Sammeladresse, `HW_REDAKTION` = kommagetrennte Absenderliste). Nie in Code, Tests, Fixtures, Commits oder diese Datei.

**Vertrauensstufen im Kalender-Eingang** (`kalender_eingang.vertrauensstufe()`):

| Stufe | Bedingung | Folge |
|---|---|---|
| `vertraut` | Absender in `HW_REDAKTION`, `KALENDER_ALIAS` in To/Cc (Schutz gegen weitergeleitete signierte Altmails) **und** `dkim=pass` (`header.d` = Absenderdomain) oder `dmarc=pass` (`header.from` = Absenderdomain) laut iCloud | **Redaktion direkt** (`ist_redaktion_direkt()`, seit 13.10.2026): alles ohne Prüfliste, siehe unten |
| `redaktion_unauth` | in der Liste, aber ohne DKIM/DMARC-Pass | alles zur Prüfung; zählt zum Limit von 5 pro Lauf |
| `unbekannt` | nicht in der Liste (oder mehrere From-Adressen) | alles zur Prüfung, max. 5 pro Lauf; Massenmails (`List-Id`/`List-Unsubscribe`) werden übersprungen |

Gewertet werden nur die Prüfergebnisse von iCloud (`dkim-verifier.icloud.com`, `dmarc.icloud.com`), und je Prüfart nur der erste Eintrag bis zum ersten `spf.icloud.com`. iCloud setzt seinen Block oberhalb der Absender-Header; ein vom Absender eingeschmuggelter `dkim=pass`-Header stünde darunter und zählt nicht; fehlt die SPF-Zeile, wird gar nichts gewertet. Außerdem: Nennt `header.i` ein anderes Postfach als From (fremdes Konto derselben Freemail-Domain) oder trägt eine DKIM-Signatur ein `l=`-Tag (nur Teil des Texts signiert), ist der Absender nicht authentifiziert (Test mit echten Headern am 11.10.2026: GMX `dkim=pass`, `dmarc=pass`). Die VestReporter-Domain hat kein SPF/DKIM/DMARC, FS schreibt den Alias deshalb von GMX an. HW-markierte und Presse-Mails gelten weiter als `vertraut`; **Änderungen aus automatisch erkannten Presse-Mails** (nur Absender/Anzeigename geprüft, fälschbar) gehen aber immer zur Prüfung (`Mail.presse_auto`).

**Seit 26.09.2026 zusätzlich automatische Erkennung** von Pressemitteilungen der Pressestellen von Stadt und Kreis Recklinghausen (`_ist_presse_mail()`, `finde_presse_mail_ids()`) — **ohne** manuelle „HW"-Markierung. Hintergrund: Die manuelle Markierung war der eigentliche Flaschenhals (der Import selbst funktionierte, bekam aber tagelang keine Mails zugewiesen). Kriterium: Absenderadresse `PressestelleRecklinghausen@recklinghausen.de`, Anzeigename exakt „Kreis Recklinghausen" (die Adresse `info@presse-service.de` ist eine geteilte Presseservice-Adresse, die auch andere Kommunen wie Hamm nutzen — deshalb zählt dort nur der Anzeigename, nicht die Adresse), oder eine beliebige `@recklinghausen.de`-Adresse mit Betreff `PM:`/`PT:`/`Pressemitteilung:` (deckt einzelne Pressesprecher wie Hermann Böckmann ab). Rückblickfenster `AUTO_PRESSE_TAGE` (21 Tage). Die „HW"-Kategorie bleibt für alle anderen Absender (Vereine, externe Veranstalter) der Weg.

Bewusst **kein regelbasierter (KI-freier) Filter** für „ist das ein echter Termin": Presse-Mails der Stadt enthalten strukturell ähnliche, aber inhaltlich zu unterscheidende Fälle (z.B. Bürgerkoffer-Termine oder Geburtsbäumchen-Aktionen mit Datum/Uhrzeit/Ort, aber kein Kalendertermin) — diese Unterscheidung übernimmt weiterhin das Modell. Bei ~4-6 Presse-Mails/Tag bleiben die API-Kosten vernachlässigbar.

**Reine Presse-Fototermine ausgeschlossen:** Termine, die im Mailtext ausdrücklich als „Fototermin" bezeichnet sind (z.B. die wöchentliche Übersicht „Pressetermine für die Woche …"), meldet das Modell nicht (SYSTEM-Prompt-Regel 6) — das sind Zugangstermine für Fotografen, keine Publikumsveranstaltungen.

```
00:30 launchd (termine-holzwurm) → hw_import.sh → hw_import.py → manuelle_termine.json, korrekturen.json, hw_bericht.json
06:30 launchd (termine-re)       → update.sh → HTML → git push → Signal-Bericht (hw_bericht.py)
```

Die Uhrzeit des Imports steht im Manifest `~/ki/infra/launchd/jobs.toml` (Umstellung von 05:30 auf 00:30 mit der Einführung des Kalender-Eingangs). Folge von 00:30: Mails zwischen 00:30 und 06:30 warten einen Tag länger, auch Pressemitteilungen.

- **Lesen:** Kalender-Eingang per IMAP (siehe oben); eM-Client-SQLite nur lesend (`MailCategoryNames.categoryName = 'HW'` ODER automatische Presse-Erkennung, alle 5 Konten). Beide Wege zerlegen die Mailteile mit derselben Funktion `werte_teile_aus()` (Text, HTML, ICS, Bilder, PDF, `.docx`). Bilder/PDFs werden dem Modell mitgegeben (Bilder ab 20 KB, max. 4; PDFs bis 4 MB, max. 2), große Fotos per `sips` auf 2000 px verkleinert. **HEIC** (iPhone-Fotos, auch als `application/octet-stream` angehängt) wird an den Magic Bytes erkannt und per `sips` in JPEG umgewandelt, weil das Modell HEIC nicht liest. Termine nur aus Anhängen tragen als Beleg „BILD“/„PDF“: Zitat- und Wochentagsprüfung greifen dort nicht. **Word-Anhänge (`.docx`)** werden per `python-docx` in Text umgewandelt und an den Mailtext angehängt — ca. 1 von 6 Presse-Mails der Stadt liefert den eigentlichen Text nur als `.docx`-Anhang, nicht im Mailbody (der Body enthält oft nur eine kurze Weiterleitungsnotiz).
- **Extraktion:** ein Modellaufruf pro Mail (`claude-sonnet-5`, Fallback Haiku 4.5; `HW_MODEL` überschreibt) mit **erzwungenem Tool-Schema** (`termine`, `aenderungen`, `terminseiten`). Mailinhalt gilt als Daten; für den Kalender-Eingang ergänzt `SYSTEM_KALENDER` den Hinweis, dass weitergeleitete fremde Inhalte darin stecken können. API-Key aus der Env (`HW_ENV_FILE`, wird nie geloggt).
- **Validierung im Code, nicht im Modell:** gültiges Datum, nicht vergangen, **Beleg-Zitat muss im Mailtext stehen** (oder „BILD"/„PDF" bei Anhang), Wochentag im Beleg muss zum Datum passen, Link nur wenn im Mailtext, AfD-Filter (`app._AUSGESCHLOSSENE_MUSTER`), Ort in Recklinghausen, Ort oder Uhrzeit vorhanden, Vertrauensstufe `vertraut`.
- **Redaktion direkt (Entscheidung FS, 13.10.2026, Testwoche bis ca. 21.10.):** Für Kalender-Mails mit Stufe `vertraut` gibt es keine Prüfliste. Verworfen wird nur, was vergangen ist, schon im Kalender steht oder der AfD-Filter trifft. Weiche Zweifel (Modell unklar, Ort außerhalb, Konflikt-Check, weder Ort noch Uhrzeit, weit in der Zukunft) stehen nur im Log. **Anzeichen für einen Modellfehler** (Beleg-Zitat fehlt, Wochentag passt nicht) werden eingetragen, am Eintrag als `hw_warnung` vermerkt und im Signal-Bericht mit „bitte ansehen“ markiert. Korrekturen und Absagen ohne eindeutiges Ziel (keins oder mehrere) und mit unbrauchbaren Angaben (Link, neues Datum) werden verworfen, der Absender erfährt es per Rückmeldung („bitte genauer angeben“). `redaktion_unauth`, `unbekannt`, HW-markierte und Presse-Mails laufen wie bisher über die Prüfliste.
- **Dubletten:** gegen die zuletzt generierten Monatsseiten mit `app.entferne_duplikate()`. **Konflikt-Check:** ähnlicher Termin einer Scraper-Quelle an anderem Tag (±60 Tage) → zur Prüfung (fängt widersprüchliche Daten, z.B. Mail 24.10. vs. Website 20.10.). Manuelle Serien sind ausgenommen.
- **Ergebnis neue Termine:** eindeutig → `freigegeben: true`; sonst `freigegeben: false` + `hinweis` + Eintrag in `hw_pruefliste.md`. Zum Freigeben `freigegeben` auf `true` setzen oder Eintrag löschen. Jeder Eintrag trägt `hw_mail` (Konto:Message-ID).
- **Korrekturen und Absagen** (`aenderungen`, `bewerte_aenderung()`): Ziel ist genau **ein** Termin am bisherigen Datum, gesucht unter den freigegebenen Einträgen in `manuelle_termine.json` und den Scraper-Terminen der zuletzt generierten Monatsseite (`finde_ziele()`, Logik der Dublettenprüfung; Gleichheit/Teilstring hat Vorrang vor markantem Schlüsselwort). Kein oder mehrere Treffer, Beleg nicht im Text, Absender nicht vertraut → Prüfliste. Verteilung:

  | Ziel | Uhrzeit/Ort | Datum verschoben | Absage |
  |---|---|---|---|
  | manueller Eintrag | direkt im Eintrag | direkt im Eintrag | `"abgesagt": true` |
  | Scraper-Termin | Eintrag in `korrekturen.json` | Redaktion direkt: `korrekturen.json` mit `verschoben_auf` (alter Tag durchgestrichen, Badge „Verschoben auf TT.MM.“) **plus** neuer manueller Eintrag am neuen Tag; sonst Prüfliste | Eintrag in `korrekturen.json` |

  Jede automatische Änderung an einem manuellen Eintrag hinterlässt `hw_aenderungen: [{mail, feld, alt, neu}]`. `quellfehler: true` (Mail sagt, eine Website hat falsche Angaben) → Hinweis im Bericht, der Scraper wird **nicht** angefasst.
- **`korrekturen.json`** (versioniert, `update.sh` committet sie mit): `{datum, name, name_norm, quelle, aenderung: {uhrzeit|ort}, absage, [verschoben_auf], hw_mail, freigegeben, angelegt}`, zur Prüfung zusätzlich `bezug_name` und `hinweis`. `app.wende_korrekturen_an()` wendet freigegebene Einträge **nach dem Scrapen und vor `entferne_duplikate()`** an, auf alle Termine des Tages, deren normalisierter Name gleich ist oder den anderen enthält, Teilstring erst ab 10 Zeichen (`app.korrektur_name_passt()`, damit kurze fremde Titel wie „Party“ nicht mit abgesagt werden; erwischt so die Dublette eines Aggregators). Datumsänderungen wendet der Generator nie an (Verschiebungen über `verschoben_auf`, siehe Tabelle; solche Einträge gelten nie als verwaist, weil der alte Termin verschwindet, sobald die Quelle nachzieht). Greift ein Eintrag nicht, druckt `app.py` „[Korrektur] nicht angewendet“, und der nächste Import meldet ihn im Bericht („Korrektur greift nicht mehr“). Einträge mit Datum älter als 14 Tage räumt der Import ab.
- **Darstellung von Absagen:** Termin bleibt sichtbar, `data-abgesagt="1"` am `.termin`-Element, Badge **„Abgesagt“** (`.badge-abgesagt`), Titel und Uhrzeit durchgestrichen. Nicht im JSON-LD. Bei der Dublettenprüfung geht eine Absage nicht verloren (`Termin.abgesagt` wird auf den behaltenen Termin übertragen).
- **Neue Terminseiten** landen in `hw_neue_quellen.md` mit Vorab-Befund (JSON-LD, ICS, TEC, EventPrime …). **Es wird bewusst kein Scraper automatisch geschrieben** — Entwicklung mit Claude Code an echten Daten (Spur B, später). Bereits bekannte Hosts (Scraper-URLs + in dieser Doku erwähnte, z.B. verworfene Seiten) werden nicht erneut gemeldet. **SSRF-Schutz:** Abruf nur für vertraute Absender (nicht bei automatisch erkannten Presse-Mails) und nur zu öffentlichen Adressen (`_url_erlaubt()`, auch bei jeder Weiterleitung geprüft), denn den Kalender-Eingang kann jeder anschreiben. Restrisiko DNS-Rebinding bewusst akzeptiert (blinder GET, Antwort fließt nur als Format-Befund in den Bericht).
- **Bericht per Signal:** `hw_import.py` schreibt `hw_bericht.json` (eingetragen, geändert, abgesagt, zur Prüfung, neue Seiten, Quellfehler, verwaiste Korrekturen, Kalender-Mails ohne Ergebnis, Fehler). `update.sh` ruft nach dem Push `hw_bericht.py --status live|unveraendert|fehler` auf, das per `hermes send --to signal` an FS schickt (Muster `mail_meldung.py`): nur Titel und Datum, bereinigt und gekürzt, keine Mailtexte, kein Versand ohne Inhalt, danach als `gesendet` markiert. Bei Push-Fehler kommt der Bericht mit „NICHT live“. Hermes-Pfad: `HW_HERMES_BIN`, sonst `~/.local/bin/hermes`. Die frühere iMessage entfällt. Verworfene Termine und Änderungen aus dem Kalender-Eingang (vergangen, schon im Kalender, AfD-Filter …) stehen mit Grund unter „Nicht übernommen“, damit eine Mail nicht spurlos verschwindet (Presse-Mails bewusst nicht, sonst wird der Bericht zu lang). Mails aus dem Kalender-Eingang, aus denen das Modell nichts erkannt hat, stehen unter „Ohne Ergebnis“ (Aussetzer des Modells fallen so auf, im Test ca. 1 von 4 Läufen bei einer kurzen Absage).
- **State:** `hw_state.db` (verarbeitete Mails nach Message-ID, Tabelle `rueckmeldungen`). Geschrieben wird erst **nach** dem Speichern von JSON und Prüfliste, in einer Transaktion (vorher galt eine Mail nach einem Absturz als erledigt, ihre Einträge waren aber weg). Erneut verarbeiten: `--force`; Einzeltest ohne Flag/State: `--mail konto:id` bzw. `--mail kalender:<IMAP-UID>`, für schon verschobene Mails mit `--ordner bearbeitet`; nur Kalender-Eingang: `--nur-kalender`; nichts schreiben: `--dry-run`. `hw_state.db`, `hw_pruefliste.md`, `hw_neue_quellen.md`, `hw_bericht.json` sind git-ignoriert (enthalten Mail-Betreffs).
- **Grenzen:** max. 15 Auswertungen pro Lauf, Fehlschläge eingeschlossen (sonst lösen präparierte Mails unbegrenzt viele Modellaufrufe aus), davon max. 5 aus dem Kalender-Eingang von nicht vertrauten Absendern (`unbekannt` **und** `redaktion_unauth`, denn eine Redaktionsadresse ohne DKIM lässt sich fälschen). Alle Grenzen greifen **vor** der teuren Arbeit: Anhänge werden nur bis zur Höchstzahl umgewandelt (`MAX_BILDER`, `MAX_PDFS`, 2 Word-Dateien), und Mails aus dem Kalender-Eingang werden erst zerlegt, wenn State, Massenmail-Prüfung und Limit sie zur Verarbeitung durchlassen (jeder kann den Eingang anschreiben); wird eine Mail nicht verarbeitet (API-Fehler), bleibt sie unmarkiert und kommt in der nächsten Nacht erneut. IMAP-Fehler (Login, Ordner) brechen den Lauf nicht ab, die eM-Client-Quellen laufen weiter, der Fehler steht im Bericht. Die Modellantwort ist nicht deterministisch (gleiche Mail kann unterschiedlich viele Termine liefern) — deshalb die Code-Validierung und der State.
- **Ablage und Rückmeldung (live seit 13.10.2026, Spec `docs/superpowers/specs/2026-10-12-kalender-eingang-rueckmeldung-design.md`):**
  - *Ablage:* Am Ende jedes Laufs verschiebt `kalender_eingang.raeume_eingang()` jede Mail, deren Schlüssel im State steht (auch Massenmails und automatische Mails), nach `Kalender-Eingang/bearbeitet`. iCloud kennt kein `MOVE`: je Mail `UID COPY`, dann `UID STORE \Deleted`, dann `UID EXPUNGE <uid>`. **Nie `close()` oder nacktes `expunge()`**, beides entfernt alle als gelöscht markierten Mails des Ordners. Die Mails werden in der Schreibsitzung neu ermittelt (keine UIDs aus dem Lesedurchgang), Mails ohne Message-ID nie verschoben. Nicht ausgewertete Mails (Limit, API-Fehler) bleiben im Eingang. Mails älter als 30 Tage im Eingang stehen im Bericht. Von Hand: `--nur-verschieben [--dry-run]`.
  - *Vorfilter ohne Modell* (`ist_automatisch()`): Zustellberichte, `Auto-Submitted`, `X-Autoreply`, `Precedence: auto_reply|bulk|junk|list`, eigene Kopfzeile `X-Holzwurm-Rueckmeldung`, Alias oder Login als Absender → State `automatisch`, nie beantwortet. Text ab der Markerzeile „Automatische Rückmeldung des Holzwurm-Kalenders“ wird vor der Auswertung abgeschnitten (zitierte Rückmeldung samt Original).
  - *Rückmeldung:* **Bewusste Ausnahme** von der globalen Regel „E-Mails niemals selbst senden“ (Entscheidung FS, 12.10.2026). Nur an `vertraut`, nur Kalender-Eingang, nicht bei `--force`/`--dry-run`/`--mail` und nicht, wenn das Modell nichts erkannt hat (Abwesenheitsnotizen). `hw_import.py` merkt den Inhalt je Mail vor (`rueckmeldungen`), Gründe nur aus fester Liste (`kurzgrund()`). `update.sh` ruft nach dem Push `rueckmeldung.py --status … --bis <Startzeit>` **vor** `hw_bericht.py`: eine Sammelmail je Adresse, fester Text in Du-Form (Anrede mit Vorname aus `HW_VORNAMEN` in der Env, `adresse=Vorname,…`, sonst „Hallo,“; Link springt auf den Tag des ersten Termins), per `smtp.mail.me.com:587` vom Alias (Anzeigename „Holzwurm-Kalender“), mit `In-Reply-To`, `Auto-Submitted: auto-replied`, `X-Auto-Response-Suppress: All`. Höchstens 10 Mails pro Lauf, Verfall nach 7 Tagen, Empfängerablehnung nach 3 Versuchen geschlossen, Login- und Absenderfehler zählen nicht hoch, `laeuft` gilt als gesendet. Ergebnis als Zeile im Signal-Bericht. Der Job `termine-re` braucht dafür `HW_ENV_FILE` im Manifest (`env`, **nicht** `env_files`, sonst hätten alle Scraper API-Key und App-Passwort in der Umgebung). Test 13.10.2026: iCloud nimmt den Alias als Absender an.
- `update.sh` committet `manuelle_termine.json` (seit 21.09.2026) und `korrekturen.json` mit. Beide werden in prod nachts geschrieben: **in dev vor jeder Änderung daran erst `git pull`**.

```bash
python3 hw_import.py --dry-run                    # alle Quellen prüfen, nichts schreiben
python3 hw_import.py --dry-run --nur-kalender     # nur den Kalender-Eingang
python3 hw_import.py --dry-run --mail gmx:16529   # gezielt eine eM-Client-Mail testen
python3 hw_bericht.py --status live --dry-run     # Signal-Text zeigen, nicht senden
python3 hw_import.py --nur-verschieben --dry-run  # zeigen, was nach Kalender-Eingang/bearbeitet wandern würde
python3 rueckmeldung.py --status live --bis "$(date +%Y-%m-%dT%H:%M:%S)" --dry-run  # offene Rückmeldungen als Text
tail -f ~/Library/Logs/ki/termine/holzwurm.log
```

## Tests

```bash
.venv/bin/python -m pytest tests/ -v   # alle Tests
.venv/bin/python -m pytest tests/test_dedup.py -v  # einzelne Datei
```

`tests/test_dedup.py` — testet `_termin_score()` und `entferne_duplikate()` aus `app.py`. Kein Mock-Framework nötig; Termin-Objekte werden direkt instanziiert.

Kalender-Eingang: `tests/test_redaktion_direkt.py` (Regeln ohne Prüfliste, Verschiebung von Scraper-Terminen, Warnungen im Bericht), `tests/test_kalender_eingang.py` (MIME-Zerlegung, Vertrauensstufen inkl. gefälschter Header), `tests/test_hw_aenderungen.py` (Zielsuche, Korrekturen, Absagen), `tests/test_korrekturen_app.py` (Generator: Korrektur vor Dedup, Absage-Darstellung, JSON-LD), `tests/test_hw_bericht.py` (Signal-Text), `tests/test_kalender_ablage.py` (Verschieben mit Fake-IMAP, Vorfilter, Zitat-Schnitt, Alias), `tests/test_hw_rueckmeldung_import.py` (Bericht pro Mail, Speicherreihenfolge, Vormerken), `tests/test_rueckmeldung.py` (Versand mit Fake-SMTP, Text). Ohne Netz und ohne echte Adressen (nur `.example`/`.test`).

## Abhängigkeiten

```bash
pip install requests beautifulsoup4 lxml pymupdf   # pymupdf = PyMuPDF (fitz), für Stadtarchiv-PDF
# requirements.txt enthält nur requests/beautifulsoup4/lxml — pymupdf bewusst ausgelassen (optional)
# python-docx (für hw_import.py, Word-Anhänge in Presse-Mails) ebenfalls nicht in requirements.txt
```

## Apify-Integration (Facebook / „Weitere Tipps")

Token in `.env` im Projektverzeichnis (nicht versioniert, in `.gitignore`):
```
APIFY_TOKEN=apify_api_...
```

`hole_facebook()` liest den Token via `_lese_apify_token()` — kein Absturz wenn Token fehlt, gibt still `[]` zurück. Timeouts: Apify-Sync-Endpunkt `timeout=300`, `requests`-Client `timeout=360` (Client muss länger warten als Apify). Kosten: ~$0,05 pro Lauf; Free-Tier $5 einmalig. Bei 402-Fehler: Guthaben in Apify-Einstellungen aufladen.

**Cache:** Apify wird max. 1× pro Woche aufgerufen. Ergebnisse landen in `.facebook_cache.json` (nicht versioniert). Cache älter als 7 Tage → neuer API-Aufruf. Cache löschen um manuell zu erzwingen: `rm .facebook_cache.json`.

Testskript: `test_apify_facebook.py` — ruft den Actor direkt auf und zeigt Rohdaten inkl. Feldnamen (nützlich bei Actor-Updates).

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
| `hole_stadtarchiv()` | recklinghausen.de (PDF) | PyMuPDF: Halbjahres-PDFs, Regex für deutsche Datumsformate |
| `hole_geschichte_re()` | geschichte-recklinghausen.de | TEC REST-API (`wp-json/tribe/events/v1/events`, seit 08/2026 — vorher fragiles ECT-Timeline-Parsing mit Stunde%12-Bug); Verein pflegt halbjahresweise → 0 Events heißt meist nur „Halbjahresprogramm noch nicht eingetragen" |
| `hole_gastkirche()` | gastkirche.de | JEvents (Joomla): Wochenansicht, Kat. 68+70, `li.ev_td_li` mit `a.ev_link_row` |
| `hole_ruhrfestspiele()` | ruhrfestspiele.de | Zweistufig: /programm → Produktions-Links → Detailseiten, `article.production-schedule-item` |
| `hole_backyard()` | backyard-club.de | TEC JSON-LD (doppelt auf Seite → interne Deduplizierung + HTML-Entity-Bereinigung) |
| `hole_cineworld()` | cineworld-recklinghausen.de | Cineamo API (`api.cineamo.com`), Cinema-ID 877, pro Tag abgefragt; **ein Eintrag pro Film und Tag**, alle Vorstellungszeiten des Tages im Uhrzeit-Feld (`14:00 / 19:30 Uhr`). Von 02/2026 bis 09/2026 gab es nur einen Eintrag pro Film und Monat (Commit `a76a284`, damals Kino standardmäßig sichtbar); aufgehoben, weil Kino per Toggle beim Seitenaufruf ausgeblendet ist. Kino-Einträge zählen nicht im Seitenzähler der Sichtbaren, solange der Toggle aus ist |
| `hole_neue_philharmonie()` | neue-philharmonie-westfalen.de | HTML `div.c-event`, Datum `span.c-event__date-date` ("10. März" ohne Jahr), Stadtfilter auf "Recklinghausen" |
| `hole_ikonen_museum()` | ikonen-museum.com | HTML `div.event-list-item`, Datum `div.event-startdate` ("01.03." ohne Jahr), Uhrzeit aus `div.info` |
| `hole_debut_um_11()` | debut-um-11.de | WordPress `article.post-item`, Termin aus `h2.entry-title a` Link-Text ("15. März 2026, 11:00 Uhr") |
| `hole_adfc()` | recklinghausen.adfc.de | JSON-API `api-touren-termine.adfc.de`, unitKey 164420 (Termine) + 16442006 (Radtouren), Stadtfilter "Recklinghausen", ein Request für alle Events |
| `hole_atelierhaus()` | atelierhaus-recklinghausen.de | ICS-Feed (ai1ec Plugin); mehrtägige Ausstellungen erscheinen in jedem überlappenden Monat mit `kategorie='Ausstellung'`; iCal DTEND bei Ganztages-Events = exklusiver Folgetag (−1 Tag korrigieren) |
| `hole_zu_gast_in_re()` | zu-gast-in-re.de/programm | Text-Parsing: Website-Builder (DM), Datum-Spans per Regex, ein Termin pro Festival-Tag; Seite enthält nur Vorjahresprogramm bis neues veröffentlicht wird |
| `hole_re_leuchtet()` | re-leuchtet.de/programm | Seit 10/2026 **ohne** The Events Calendar (REST-Route 404). Programmseite mit `article.rel-card`; jedes Vorkommen als JSON im Attribut `data-events` (`start` ISO mit Zeitzone, `venue`), Titel `h3 a`, Link `?rel_event=<slug>`, Kurztext `[data-excerpt]`. Ein Termin pro Vorkommen, Seite wird pro Lauf nur einmal geholt. Festival 23.10.-08.11.2026 (ca. 100 Vorkommen). Tests: `tests/test_re_leuchtet.py` |
| `hole_frauenforum()` | — (kein Scraping) | Programmatisch: 3. Dienstag/Monat, 17 Uhr, Familienbüro Große Geldstraße 19; Pause Juli + Dezember |
| `hole_josefeich()` | josefeich.de | JSON-LD `Event` (The Events Calendar Plugin); Kirchenmusik-Termine |
| `hole_recklinghaeuser()` | der-recklinghaeuser.de | Fließtext-Parsing: deutsche Datumsformate ("Sa. 14. März 2026"), Titel + Uhrzeit aus Folgezeilen |
| `hole_subergs()` | subergs.de/events/ | WordPress-Blogposts: Datum im h3-Titel ("DD.MM.YYYY – Titel"), Elementor-Layout |
| `hole_stadtlabor()` | stadtlabor-re.de | Armadillo-Blog: `div.blog-entry`, Vernissage-Datum/Uhrzeit aus Titel+Body per Regex (DE/EN-Monate, DD.MM.YYYY) |
| `hole_gegendruck()` | theater-gegendruck.de | ICS-Feed (The Events Calendar Plugin); Theater im Atelierhaus, Königstraße 49a |
| `hole_ev_akademie()` | akademie-re.de/veranstaltungen/ | HTML `article.event-card`: `.event-card-date-badge` (`.day`/`.month`, **ohne Jahr** → aus Ziel-Monat abgeleitet), `.event-card-meta-item` (Uhrzeit per Regex, sonst Ort), `h3 a` (Titel + relativer Link); `past-event`-Klasse übersprungen. Ort in Liste serverseitig gekürzt → bei `…`/leer gezielt von Detailseite (`.location-name`) nachgeladen; `kategorie='Bildung'`. Neue Domain seit 06/2026 (ersetzt ahademie.com) |
| `hole_ratssitzungen()` | stadt-recklinghausen.gremien.info | JSON-API (more!rubin/gremien.info): `api.php?id=calendar&action=get&from=YYYY-MM&to=YYYY-MM`; alle Ausschüsse, Beiräte, Rat; `kategorie='Politik'` |
| `hole_moondock()` | moondock.tv/page/Events | HTML-Scraping: `article.post-item`, `span.day`/`span.month` (EN-Monate), `h3.title.post`; `verify=False` (SSL); Uhrzeit aus Beschreibung ("ab 21 Uhr") |
| `hole_campus_emscherland()` | campus-emscherland.eu (Das Gelbe Haus, RE-Süd) | JSON-API von kalender.digital (`api.kalender.digital/event`, capabilityId in `scraper.py`); Serien bereits aufgelöst; Filter: `imported=True` (Feiertags-Feed) + „geschlossen" im `who`-Feld; mehrtägige Termine → `kategorie='Ausstellung'`, ein Eintrag pro überlappendem Monat; Kategorie aus Unterkalender-ID (`_CAMPUS_KATEGORIEN`). **Achtung:** Ausstellungen, die nur im Blog auf der Startseite stehen, aber nicht im Kalender eingetragen sind, sieht der Scraper nicht |
| `hole_facebook()` | Facebook Events (via Apify) | Apify-Actor `apify~facebook-events-scraper`; Start-URLs: Explore-Suche + Altstadtschmiede-Seite; Filter: `countryCode == 'DE'` + "recklinghausen" in location; `utcStartDate` → Europe/Berlin; Token aus `.env` (`APIFY_TOKEN=...`); Tier 2; im UI als **"Weitere Tipps"** beschriftet |
| `hole_eventim()` | eventim.de (via Apify) | eventim.de sperrt direkte Abrufe per Akamai (Seite und interne Such-API, Test 10.10.2026). Apify-Actor `zen-studio~eventim-scraper` mit `city=Recklinghausen` (Freitext), Header-Auth, **ein** Aufruf pro Woche für alle Monate (Cache `.eventim_cache.json`, 7 Tage; bei Fehler pro Prozess kein zweiter Versuch). Filter `venue.city == Recklinghausen` (Umkreis liefert sonst Oer-Erkenschwick/Herten), abgesagte übersprungen, Ortsnamen in Versalien normalisiert. Stand 10/2026 ca. 5 Events (Gastspiele Ruhrfestspielhaus, Ratskeller, Kirchen), ca. 0,04 $ pro Lauf. Verworfen: `techforce.global` (feste Liste von 50 Großstädten), `lentic_clockss` (ignorierte den Stadt-Slug), `abotapi` (Proxy im Free-Plan abgewiesen). Tier 2; Tests gegen gesicherte Antwort: `tests/test_eventim.py` |
| `hole_agenda21()` | lokale-agenda21-re.de/termine/ | Google-Kalender-ICS (`_google_kalender_termine()`, gemeinsam mit `hole_selbsthilfegruppen_re()`): Seite bettet 11 öffentliche Google-Kalender per iframe ein, Kalender-IDs aus Base64-kodierten iframe-`src`-Parametern extrahiert und fest in `_AGENDA21_KALENDER` hinterlegt (Foren, Lenkungskreis, Agendaforum, Sonstige Termine); deutscher Feiertagskalender bewusst ausgeschlossen; `kategorie='Ehrenamt'` |
| `hole_selbsthilfegruppen_re()` | selbsthilfegruppen-recklinghausen.de/?page_id=33 | Gleiches Google-Kalender-ICS-Muster wie Agenda21, 8 Kalender in `_SHG_RE_KALENDER` (Adipositas, Depression, Intoleranzen, ReN, Schlafapnoe, SHG Sport, Veranstaltungen, Ü100); `Feiertage`/`NRW Ferien`/`Geburtstage`-Kalender bewusst ausgeschlossen. **Stand 08/2026: liefert 0 zukünftige Termine** — alle 8 Kalender sind faktisch unbeplegt (jüngster Eintrag über alle Kalender: 20.07.2026), kein Scraper-Bug. Analog zu VOHR (`hole_geschichte_re`) greift der Scraper automatisch, sobald die Gruppen wieder pflegen |
| `hole_katholisch_netzwerk()` | katholisch-re.de/aktuelles-termine/netzwerk | Statische HTML-Liste unter Überschrift „Aktuelles": pro `<li>` eine Datums-/Zeit-/Ort-Zeile (`Wochentag, DD. Monat YYYY, HH.MM bis HH.MM Uhr, Ort`) + Titel-Absatz + optionale Beschreibungs-Absätze; Sonderfall „anschl." (Folgetermin direkt im Anschluss) → `uhrzeit='im Anschluss'`; `kategorie='Kirche'` |
| `hole_holzwurm()` | holzwurm-recklinghausen.de/veranstaltungen | JSON-LD/TEC REST-API (`wp-json/tribe/events/v1/events`) wie Heimatkunde, RE-leuchtet, Josef P. Eich; `_HOLZWURM_AUSGESCHLOSSENE_SLUGS` filtert `'50-jahre-holzwurm'` heraus, da das Jubiläum bereits als redaktionelle Spotlight-Karte (`highlight='holzwurm50'`) in `manuelle_termine.json` gepflegt wird — sonst würde es doppelt erscheinen; `kategorie='Bildung'`. TEC-Beschreibungstexte enthalten eine leere `tribe-events-schedule`-Platzhalter-Box (clientseitig per JS gefüllt) sowie weiche Trennzeichen (`\xad`) aus der WordPress-Silbentrennung — beides wird vor der Textextraktion entfernt (Letzteres global in `_html_zu_text()`) |
| `hole_selbsthilfe_kontaktstelle()` | paritaetischer-recklinghausen.de/…/selbsthilfe-kontaktstelle/aktuelles-und-termine | TYPO3-Seite **ohne JSON-LD/ICS**, Termine als Fließtext in CMS-Blöcken (`div.t3el-textmedia`, Überschrift h2/h3 + `.ce-bodytext`). Text wird absatzweise gelesen (`<br>` = Zeilenumbruch, damit `<strong>Ort:</strong> …` eine Zeile bleibt). Ein Termin entsteht nur aus Zeilen, die **mit** dem Datum (ggf. nach „Termin:/Datum:/Vernissage:“) **beginnen**, mit Jahr: `Mittwoch, 23. September 2026, 16–17:30 Uhr` oder `Datum: 31.10.2026 und 28.11.2026, jeweils 14:00 bis 18:00 Uhr`. **Bewusst nicht übernommen:** Termine ohne Jahr (z.B. „Nächster Termin: Mittwoch, 14.10.“), Blöcke „exklusiv an Gruppenleitungen“ (Supervision), Termine ohne oder mit Ort außerhalb Recklinghausens (z.B. Oer-Erkenschwick). Das monatliche Ehrenamts- und Selbsthilfe-Café steht ohne Jahr auf der Seite und wird über `manuelle_termine.json` gepflegt. Ohne eigene „Ort:“-Zeile (z.B. Vernissage) wird der Ort des Blocks mit Hinweis übernommen. Tests gegen gesicherten Seitenausschnitt: `tests/test_selbsthilfe_kontaktstelle.py` (Fixture ohne Kontaktdaten). **Fragil:** Prosa-Seite, bei Layout- oder Formulierungsänderungen prüfen; `kategorie='Selbsthilfe'`, Quelle `selbsthilfe-kontaktstelle` |
| `hole_genial_re()` | genial.re/all-events/ (ge·ni·al e.V., Begegnungsstätte Limperstraße 11) | WordPress + EventPrime, Monatsansicht per **AJAX** `ep_get_calendar_event` (POST an `wp-admin/admin-ajax.php`, Felder `security`=Nonce, `start`, `end`, `args='[]'`). Die **Nonce** steht im Seitenquelltext (`"_nonce":"…"`, `em_front_event_object`) und wird mit Cache-Buster geholt. Kein offizielles API; die REST-Route `eventprime/v1/events` liefert nur ID+Name. **Typfilter (redaktionelle Entscheidung):** übernommen werden nur `event_type` 8 (Offenes Café), 9 (Offenes Angebot), 11 (Veranstaltung); **nicht** 10 (Gruppen, Angebote für bestimmte Zielgruppen), 25 (Intern) und Einträge ohne Typ (`['0']`, z.B. „Vermietung"). Gruppen später aufnehmen: `'10'` in `_GENIAL_TYPEN` ergänzen. Titel-Ausschluss ganzwortgenau (`intern`, `vermietung`, `geschlossen`) — „Internationales Sprachcafé“ darf **nicht** treffen (Regressionstest). Mehrtägige Termine je Tag, ganztägig. Ohne Venue → Ort „Recklinghausen“; „… im Genial“ ohne Adresse → Limperstraße 11 ergänzt. Keine Beschreibung in der AJAX-Antwort (nur Art + Notiz). Tests gegen gesicherte Antwort: `tests/test_genial_re.py`. `kategorie='Begegnung'` |
| `hole_demokratie_werkstadt()` | demokratie-werkstadt-re.de/termine/ | Prosa-Seite ohne JSON-LD/ICS: Monatsüberschrift („Oktober 2026“), darunter Blöcke, die mit dem Tag beginnen (`3. September 19:00-21:30 Uhr`, `1.10. Liederabend, …`, `11./25. Oktober, …`). Gelesen nur bis zur Überschrift „Rückblick“. Titel inline oder in der Folgezeile, Ort per Straßen-/Ortsmuster. Ohne Uhrzeit → „siehe Website“. „Regelmäßig“-Hinweise werden nicht ausgewertet. **Fragil.** `kategorie='Politik'`. Stoppwörter `offenes/offene/offener/treffen` in `app._STOPPWOERTER`, sonst verschluckt das Keyword-Dedup „Offenes Werkstadt-Treffen“ gegen „Offenes Begegnungs-Café“ |
| `hole_attac_re()` | attac-netzwerk.de/recklinghausen/termine | Blog-Freitext (TYPO3), Regex auf den Einladungssatz „am Montag, den 31. August 2026 um 19 Uhr in der …“. Unregelmäßig, 0 zukünftige Termine sind normal. `kategorie='Politik'` |

**Kinderschutzbund Recklinghausen** (`kinderschutzbund-recklinghausen.de/veranstaltungen/index.php`, Portuna-CMS): Terminliste am 07.10.2026 leer („Keine Veranstaltungen gefunden“), JSON-LD nur Breadcrumb. Kein Scraper ohne Beispieldaten; erneut prüfen, sobald Termine eingetragen sind. Die Demokratie-Treffs im Haus kommen über die Demokratie-Werkstadt.

**Jüdische Kultusgemeinde Kreis Recklinghausen** (`jg-recklinghausen.de/veranstaltungen/`): Kulturprogramm nur als Flyer-Bilder (JPG, WordPress/WPBakery), kein Text, daher kein Scraper. Termine werden einmal pro Jahr aus dem Flyer in `manuelle_termine.json` übernommen (Stand 07.10.2026: 25.10.2026 Tallana Gabriel/Boris Rosenthal; alle anderen Termine 2026 vergangen). Nächster Check: neuer Jahresflyer.

**Bürgerfunk Recklinghausen** (`cityredio.jimdofree.com`) wurde geprüft — reine Kontakt-/Über-uns-Seite ohne Terminliste oder Kalenderstruktur, daher kein Scraper. Sollte sich das ändern, ist die Seite erneut zu prüfen.

**Vereinsverzeichnis der Stadt Recklinghausen** ([Link](https://www.recklinghausen.de/inhalte/startseite/Leben_Wohnen/Vereine_und_Veranstaltungen/_vereinsverzeichnis.asp?db=17&form=list&fieldStadt=Recklinghausen&orderby=fieldName)) ist kein Terminkalender, sondern ein reines Vereinsregister ohne Datumsfelder — daher kein Scraper, sondern nur als Recherchequelle für Vereins-/Kontaktdaten dokumentiert (Hinweis von Ralf, Stand 08/2026).

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
6. Badge-CSS-Klasse `.badge-neuequelle` mit Farbgradient in `generiere_html()` ergänzen — Konvention: `linear-gradient(135deg, #HELL 0%, #DUNKEL 100%)`, zweite Farbe ca. 10 Einheiten dunkler; alle 24 vorhandenen Farben sind in der Funktion dokumentiert, keine Doppelung wählen
7. Badge-Zuordnung in `badge_classes`-Dict in `generiere_html()` eintragen
8. Footer-Link in der modulweiten Konstante `FOOTER_QUELLEN` (`app.py`, Liste von `(Anzeigename, URL)`-Tupeln) ergänzen — Reihenfolge egal, der Footer wird daraus alphabetisch (case-insensitiv) gerendert
9. Optional: Toggle-Button falls Quelle viele Termine liefert — `toggleXyz()`-Funktion + `xyzAusgeblendet`-Variable + `xyzMatch`-Check in `filterTermine()` (Muster: siehe VHS/Kino-Toggle)
10. Quellentabelle in dieser CLAUDE.md aktualisieren
11. Bei externen APIs (wie Apify): Apify-Abschnitt in dieser CLAUDE.md ergänzen

**`hebbert/`** — Maskottchen-Bilder für den Seitenheader. Aktiv: `1984-01-verkleinert.jpg` (links), `1985-04-verkleinert.jpg` (rechts) und `hebbert-winkend.png` (Spotlight-Karte; Original-Cartoon aus der Einladung „50 Jahre Holzwurm", Seite 2). Originals liegen als Fallback daneben, nicht mehr referenziert.

**`favicon.ico` / `favicon-96x96-1.webp`** — Beide Formate nötig: `.ico` als Browser-Fallback (wird automatisch als `/favicon.ico` abgerufen), `.webp` für moderne Browser. Beide sind im HTML-`<head>` eingebunden, `.ico` zuerst.
