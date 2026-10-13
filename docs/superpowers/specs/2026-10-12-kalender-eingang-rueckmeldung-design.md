# Spec: Kalender-Eingang, Ablage und Rückmeldung an die Redaktion

Stand: 12.10.2026 · Status: live seit 13.10.2026 (v2, Zweitmeinung eingearbeitet) · Ergänzt `2026-10-10-kalender-eingang-design.md` und hebt dort in Abschnitt 4 „Strikt lesend … kein Verschieben“ auf.

> **Öffentliches Repo:** keine Mailadressen in Spec, Code, Tests, Fixtures. Alias und Redaktion stehen nur in `prod/termine/secrets/termine-hw.env`.

## 1. Ziel

1. Ausgewertete Mails im iCloud-Ordner `Kalender-Eingang` wandern in den Unterordner `Kalender-Eingang/bearbeitet`. Im Eingang bleibt nur, was noch nicht ausgewertet ist.
2. Absender aus der Redaktion bekommen nach der Veröffentlichung **eine Sammelantwort pro Adresse und Tag**: eingetragen, geändert, abgesagt, steht schon im Kalender, wird von Hand geprüft, nicht übernommen.

Entscheidungen FS (12.10.2026): beides umsetzen; Antwort **nur an vertraute Absender** (`vertraut`); Prüffälle wandern ebenfalls nach `bearbeitet`.

**Bewusste Ausnahme** von der globalen Regel „E-Mails niemals selbst senden“: Ein Job verschickt Bestätigungen nach festem Text an die verifizierte Redaktion. Gründe stammen aus einer festen Liste, nur Termintitel aus der Auswertung (bereinigt). Wird in der Projekt-`CLAUDE.md` festgehalten.

## 2. Geprüft am 12.10.2026

- IMAP iCloud: `UIDPLUS` vorhanden, `MOVE` **nicht**. Hierarchie-Trenner `/`. Unterordner `bearbeitet` existiert noch nicht. `conn.uid("EXPUNGE", …)` funktioniert mit `imaplib`.
- SMTP `smtp.mail.me.com:587`, STARTTLS, Login mit dem App-Passwort des Jobs klappt.
- `infra`: Ein Job darf `env` und `env_files` gleichzeitig haben (`run-job` exportiert erst `env`, dann `env_files`).
- 13.10.2026: iCloud nimmt den Alias als `From` an (Testmail an die Apple-ID, Posteingang, nicht Junk). Einzeltest Verschieben: eine Mail nach `bearbeitet`, Flags unverändert, keine Löschmarken übrig.

## 3. Vorab-Fix: erst speichern, dann als verarbeitet markieren

Heute markiert `main()` jede Mail sofort in `hw_state.db`, gespeichert wird erst am Ende. Stürzt der Lauf dazwischen ab, sind die Einträge verloren, die Mail gilt aber als erledigt. Mit dem Verschieben würde das unsichtbar.

Neu: Markierungen (und Rückmeldungen) je Mail sammeln. Erst nach `speichere_json`/`speichere_korrekturen`/`schreibe_pruefliste` in **einer** SQLite-Transaktion schreiben. Danach `raeume_eingang()`. Stürzt der Lauf vorher ab, wird im nächsten Lauf neu ausgewertet (Kosten, kein Verlust; Dublettenprüfung greift).

`sqlite3.connect(…, timeout=30)`, weil beide Jobs dieselbe DB nutzen.

## 4. Verschieben: `kalender_eingang.raeume_eingang()`

Eigener, idempotenter Schritt am Ende jedes Laufs (nicht bei `--dry-run`/`--mail`), zusätzlich aufrufbar als `hw_import.py --nur-verschieben [--dry-run]`.

- Eigene Verbindung, `SELECT '"Kalender-Eingang"'` schreibend. **Keine UIDs von außen**: Die Funktion ermittelt die Mails in ihrer Sitzung selbst: `UID SEARCH UNDELETED SINCE <heute−30>`, dann `UID FETCH … BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)]`, Schlüssel bilden, gegen den State prüfen (Callback `ist_erledigt(schluessel) -> bool`).
- Verschoben wird jede Mail, deren Schlüssel im State steht (jedes Ergebnis, auch `massenmail` und `automatisch`). **Mails ohne Message-ID werden nie verschoben** (Schlüssel hinge an der UID).
- Zielordner `Kalender-Eingang/bearbeitet` anlegen, wenn `LIST` ihn nicht kennt (`CREATE`, `SUBSCRIBE`). Ordnernamen selbst in Anführungszeichen.
- Je UID: `UID COPY` → nur bei `OK`: `UID STORE +FLAGS.SILENT (\Deleted)` → nur bei `OK`: `UID EXPUNGE <uid>`. `COPYUID` ins Log.
- **Nie** `close()`, nie nacktes `expunge()`: Beides entfernt alle `\Deleted`-Mails im Ordner, auch fremde. Nur `logout()`.
- Teilfehler (COPY ok, STORE/EXPUNGE nicht) erzeugen beim nächsten Lauf eine zweite Kopie in `bearbeitet`. Hingenommen, steht im Log.
- Mails älter als 30 Tage im Eingang: Anzahl ins Log und in den Bericht (`UID SEARCH UNDELETED BEFORE …`).
- Fehler brechen den Lauf nicht ab, landen in `bericht["fehler"]`.
- `hole_mails()` sucht künftig ebenfalls mit `UNDELETED`.

Für Nachtests: `--mail kalender:<UID>` und `--force` bekommen `--ordner bearbeitet` (Parameter `ordner` in `hole_mails()` gibt es schon).

## 5. Vorfilter vor der Auswertung (nur Kalender-Eingang)

Ohne Modellaufruf als `automatisch` in den State (und damit verschoben), nie beantwortet:
- `Content-Type: multipart/report`, Absender `MAILER-DAEMON@…`/`postmaster@…` (Unzustellbar-Meldungen)
- `Auto-Submitted` vorhanden und nicht `no`, `X-Autoreply`/`X-Autorespond`, `Precedence: auto_reply|bulk|junk|list`
- Kopfzeile `X-Holzwurm-Rueckmeldung` (unsere eigene Mail)
- `From` ist der Alias selbst oder `ICLOUD_USER`

Zitate: Der Rückmeldungstext beginnt mit einer festen Markerzeile (`MARKER = "Automatische Rückmeldung des Holzwurm-Kalenders"`). Vor der Auswertung wird bei Kalender-Mails der Text ab der ersten Zeile mit dem Marker abgeschnitten. So landen weder unsere Zeilen noch das darunter zitierte Original erneut beim Modell. Antworten auf eine Rückmeldung werden normal ausgewertet und beantwortet.

## 6. Vertrauen schärfen

`vertraut` verlangt zusätzlich, dass `KALENDER_ALIAS` in `To` oder `Cc` steht (Schutz gegen DKIM-Replay: eine alte signierte Mail eines Redaktionsmitglieds, an den Alias weitergeschickt). Fehlt der Alias in der Env, gibt es kein `vertraut` (Grund „KALENDER_ALIAS fehlt“). Mails per Bcc gehen damit zur Prüfung, nicht verloren.

## 7. Rückmeldung

### 7.1 Vormerken (00:30, `hw_import.py`)

Nur `mail.konto == "kalender"` und Stufe `vertraut`, nur ohne `--dry-run`, `--mail`, `--force`. Nicht bei `ohne_ergebnis` (das ist der Fall, den Abwesenheitsnotizen erzeugen; FS sieht ihn im Signal-Bericht).

`verarbeite_mail()` bekommt einen eigenen Bericht pro Mail, der danach in den Gesamtbericht übernommen wird. Neu darin: `bekannt` (Termin von `haenge_an()` als Wiederholung übersprungen). Ist der Inhalt leer, wird nichts vorgemerkt.

```
rueckmeldungen(schluessel text primary key, adresse text, message_id text, betreff text,
               inhalt text, angelegt text, gesendet text, eigene_id text, versuche int default 0)
```

`INSERT … ON CONFLICT DO NOTHING`. `adresse` = die eine From-Adresse, nie `Reply-To`. `hw_state.db` ist git-ignoriert.

`inhalt` (JSON): `eingetragen [{datum,name}]`, `geaendert [{datum,name,was}]`, `abgesagt`, `bekannt`, `pruefen [{datum,name}]`, `verworfen [{datum,name,grund}]`. `grund` ist bereits ein Kurzgrund aus fester Liste:

| Rohgrund | Kurzgrund |
|---|---|
| liegt in der Vergangenheit | „liegt in der Vergangenheit“ |
| steht schon im Kalender / Angaben stehen bereits so / bereits als abgesagt | „steht schon so im Kalender“ |
| ausgeschlossene Gruppierung | „wird nach den Regeln des Kalenders nicht aufgenommen“ |
| alles andere | „Angaben reichen nicht aus“ |

`was` bei Änderungen nur aus Feldname (Uhrzeit, Ort, Link) plus normalisiertem Wert.

### 7.2 Senden (06:30, `rueckmeldung.py`)

`update.sh` merkt sich vor `app.py` die Startzeit und ruft nach dem Push **vor** `hw_bericht.py`:
`rueckmeldung.py --status live|unveraendert|fehler --bis <start-iso> [--dry-run]`

- Gesendet wird nur bei `live`/`unveraendert` und nur für Einträge mit `angelegt < --bis` (sonst bestätigt die Mail Termine, die `app.py` noch nicht kannte, z.B. wenn beide Jobs nach dem Aufwachen gleichzeitig nachlaufen).
- **Eine Mail pro Adresse**: alle offenen Einträge der Adresse zusammengeführt. `In-Reply-To`/`References` = Message-ID der jüngsten Mail; Betreff: bei einer Mail „Re: “ + Originalbetreff ohne vorhandene `Re:/AW:/WG:/Fwd:`, max. 120 Zeichen; bei mehreren „Holzwurm-Kalender: Rückmeldung zu deinen Mails“.
- Höchstens 10 Mails pro Lauf. Einträge älter als 7 Tage werden ohne Versand geschlossen (`verfallen`).
- Vor dem Senden: `adresse` erneut gegen `HW_REDAKTION` prüfen, sonst schließen (`nicht mehr in der Redaktionsliste`).
- Doppelversand vermeiden: vor `send_message` `gesendet='laeuft'` committen, danach Zeitstempel. Ein `laeuft` aus einem abgebrochenen Lauf gilt als gesendet (lieber einmal zu wenig).
- Fehler: Verbindungs- oder Loginfehler → Lauf abbrechen, `versuche` **nicht** erhöhen. Ablehnung des Empfängers (`SMTPRecipientsRefused`, 5xx) → `versuche += 1`, ab 3 geschlossen.
- `EmailMessage(policy=email.policy.SMTP)` (lehnt CR/LF in Kopfzeilen ab), `From` per `formataddr(("Holzwurm-Kalender", alias))`, `Message-ID` per `make_msgid(domain=<Domain des Alias>)`, gespeichert in `eigene_id`. `In-Reply-To` nur, wenn die Original-ID `^[\x21-\x3b\x3d\x3f-\x7e]{1,250}$` erfüllt. Zusätzlich `Auto-Submitted: auto-replied`, `X-Auto-Response-Suppress: All`, `X-Holzwurm-Rueckmeldung: 1`. Versand `send_message(msg, from_addr=alias, to_addrs=[adresse])`.
- Env: `ICLOUD_USER`, `ICLOUD_APP_PASSWORD`, `KALENDER_ALIAS`, `HW_REDAKTION` aus `HW_ENV_FILE`. Im Manifest bekommt der Job `termine-re` `env = { HW_ENV_FILE = … }`, **nicht** `env_files` (sonst hätten `app.py` und alle Scraper API-Key und App-Passwort in der Umgebung).
- Ergebnis: `"rueckmeldungen": {"gesendet": n, "fehler": m}` in `hw_bericht.json`, `hw_bericht.py` zeigt eine Zeile und wertet `fehler > 0` als meldenswert. Ist der Bericht schon gesendet, schickt `rueckmeldung.py` Fehler selbst per Signal (`hw_bericht.sende_signal`).

### 7.3 Text (fest, du-Form)

```
Automatische Rückmeldung des Holzwurm-Kalenders

Hallo,

danke für deine Mail an den Holzwurm-Kalender. Sie ist bearbeitet:

Eingetragen:
- Sa 24.10. Titel
Geändert:
- Fr 23.10. Titel: Uhrzeit 19:30
Abgesagt:
- ...
Stand schon im Kalender:
- ...
Wird noch von Hand geprüft:
- ...
Nicht übernommen:
- Fr 23.10. Titel (liegt in der Vergangenheit)

Zum Kalender: https://termine.holzwurm-recklinghausen.de/termine_re_2026_10.html

Bitte nicht direkt auf diese Mail antworten, außer du hast einen neuen Hinweis.
```

(Bei mehreren Mails: „danke für deine Mails …“.) Nur Abschnitte mit Inhalt, je max. 10 Zeilen. Titel über `hw_bericht.bereinige()`. Link: Monatsseite des ersten eingetragenen Termins, wenn die Datei im Repo existiert, sonst `index.html`-URL.

## 8. Proof of Concept vor dem Scharfschalten

1. Alias aus dem `To`-Header einer Mail im Eingang lesen, als `KALENDER_ALIAS` in `termine-hw.env` eintragen (nicht im Chat ausgeben).
2. `hw_import.py --nur-verschieben --dry-run` gegen den echten Eingang: Liste prüfen.
3. **Eine** Testmail an FS (nach Freigabe): Alias als Absender akzeptiert? Erscheint als Antwort?
4. `--nur-verschieben` scharf, danach beide Ordner per `SELECT readonly` zählen.
5. Manifest (`jobs gen` ansehen, dann `install`), Deploy `--dry-run`, dann scharf.

## 9. Tests (ohne Netz, nur `.example`-Adressen)

- `raeume_eingang()` mit Fake-IMAP: COPY → STORE → UID EXPUNGE; kein `CLOSE`, kein `EXPUNGE` ohne UID; bei COPY-Fehler kein STORE; Ordner wird angelegt; ohne Message-ID nicht verschoben; nicht im State bleibt.
- Speicherreihenfolge: Absturz vor dem Speichern lässt State leer.
- Vorfilter (Report, Auto-Submitted, eigene Kopfzeile, eigener Absender) und Marker-Schnitt.
- Vertrauen: ohne Alias in To/Cc kein `vertraut`; ohne Env-Alias kein `vertraut`.
- Vormerken: nur Kalender + vertraut; nicht bei ohne_ergebnis, force, dry-run; `bekannt` erfasst; Kurzgründe.
- Senden mit Fake-SMTP: Sammelmail je Adresse, Kopfzeilen, Betreff ohne `AW:`, `--bis`, Status `fehler`, Limit, Verfall, Loginfehler erhöht `versuche` nicht, Empfängerablehnung schon, Adresse nicht mehr in Liste, `laeuft`.
- Text: Abschnitte, Bereinigung, Link-Rückfall.

## 10. Nicht Teil dieser Spec

- Kopie im Ordner „Gesendet“ (Nachweis über `hw_state.db` und Log).
- Antwort an unbekannte oder nicht authentifizierte Absender.
- Sperre gegen gleichzeitigen Lauf beider Jobs (betrifft auch `hw_bericht` schon heute; `--bis` deckt die Rückmeldung ab).
