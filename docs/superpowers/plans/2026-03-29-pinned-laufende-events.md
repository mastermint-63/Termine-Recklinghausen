# Pinned-Bereich: Laufende Veranstaltungen

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ausstellungen, Festivals und andere mehrtägige Veranstaltungen in einem Pinned-Bereich oberhalb der Tagesliste anzeigen, damit Nutzer laufende Events sofort sehen.

**Architecture:** Das `Termin`-Dataclass bekommt ein optionales `datum_ende`-Feld. Scraper, die Laufzeiten kennen (Atelierhaus, Stadtlabor, Kunsthalle, Ikonen-Museum), füllen dieses Feld. In `generiere_html()` werden Termine mit `datum_ende` in einen eigenen Pinned-Bereich gerendert (kompakte Karten mit Laufzeit-Anzeige), statt in der normalen Tagesliste. Die Deduplizierung und JS-Filter berücksichtigen beide Bereiche.

**Tech Stack:** Python 3.14, BeautifulSoup, HTML/CSS/JS (inline, standalone)

---

## Dateistruktur

| Datei | Änderung | Verantwortung |
|-------|----------|---------------|
| `scraper.py` | Modify | `Termin`-Dataclass erweitern + betroffene Scraper anpassen |
| `app.py` | Modify | Pinned-Bereich in HTML-Generierung, CSS, JS-Filter |
| `tests/test_dedup.py` | Modify | Tests für Termine mit `datum_ende` |

---

### Task 1: Termin-Dataclass um `datum_ende` erweitern

**Files:**
- Modify: `scraper.py:59-77` (Termin dataclass)
- Test: `tests/test_dedup.py`

- [ ] **Step 1: Schreibe einen Test für das neue Feld**

In `tests/test_dedup.py` am Ende hinzufügen:

```python
def test_termin_datum_ende_optional():
    """datum_ende ist optional und defaults to None."""
    t = Termin(
        name='Ausstellung X',
        datum=datetime(2026, 3, 1),
        uhrzeit='siehe Website',
        ort='Galerie',
        link='https://example.com',
        quelle='test',
    )
    assert t.datum_ende is None

    t2 = Termin(
        name='Ausstellung Y',
        datum=datetime(2026, 3, 1),
        uhrzeit='siehe Website',
        ort='Galerie',
        link='https://example.com',
        quelle='test',
        datum_ende=datetime(2026, 4, 15),
    )
    assert t2.datum_ende == datetime(2026, 4, 15)
```

- [ ] **Step 2: Test ausführen, Fehlschlag bestätigen**

Run: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest tests/test_dedup.py::test_termin_datum_ende_optional -v`
Expected: FAIL — `TypeError: Termin.__init__() got an unexpected keyword argument 'datum_ende'`

- [ ] **Step 3: `datum_ende`-Feld zum Dataclass hinzufügen**

In `scraper.py`, nach `kategorie: str = ''` (Zeile 68) einfügen:

```python
    datum_ende: datetime | None = None
```

Die `__lt__`-Methode (Sortierung) bleibt unverändert — mehrtägige Termine werden nach ihrem Startdatum sortiert.

- [ ] **Step 4: Test ausführen, Erfolg bestätigen**

Run: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest tests/test_dedup.py -v`
Expected: PASS (alle 12 Tests, inkl. neuer)

- [ ] **Step 5: Commit**

```bash
git add scraper.py tests/test_dedup.py
git commit -m "feat: add optional datum_ende field to Termin dataclass"
```

---

### Task 2: hole_atelierhaus() — datum_ende setzen

**Files:**
- Modify: `scraper.py` (hole_atelierhaus, ca. Zeile 1975–2038)

Der Atelierhaus-Scraper hat bereits `datum_start` und `datum_end` lokal berechnet, gibt sie aber nicht im Termin-Objekt weiter.

- [ ] **Step 1: Lokalen Code der Funktion lesen**

Lies `hole_atelierhaus()` komplett (ca. Zeilen 1975–2038). Die Funktion parst ICS-Daten mit `DTSTART`/`DTEND` und hat bereits eine Variable `datum_end` (das tatsächliche Ende der Ausstellung). Bei mehrtägigen Events wird `datum` auf `max(datum_start, erster_des_monats)` gesetzt.

- [ ] **Step 2: `datum_ende` im Termin-Objekt setzen**

Im Termin-Objekt für mehrtägige Events (der Zweig `if mehrtaegig:`, ca. Zeile 2015) das Feld ergänzen:

```python
datum_ende=datum_end,
```

Das `datum_end` ist bereits als lokale Variable vorhanden. Nur die Übergabe an den Termin-Konstruktor fehlt.

Für Eintages-Events (Zeile 2024ff) ist kein `datum_ende` nötig — der Default `None` greift.

- [ ] **Step 3: Manueller Funktionstest**

```bash
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -c "
from scraper import hole_atelierhaus
for m in range(1, 13):
    termine = hole_atelierhaus(2026, m)
    for t in termine:
        if t.datum_ende:
            print(f'{m:02d}/2026: {t.name[:50]} | bis {t.datum_ende.strftime(\"%d.%m.%Y\")}')
"
```

Expected: Mehrtägige Ausstellungen zeigen `datum_ende`, Einzelevents nicht.

- [ ] **Step 4: Alle Tests ausführen**

Run: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest tests/ -v`
Expected: PASS (alle Tests)

- [ ] **Step 5: Commit**

```bash
git add scraper.py
git commit -m "feat: atelierhaus scraper populates datum_ende for exhibitions"
```

---

### Task 3: hole_stadtlabor() — Ausstellungs-Laufzeit parsen

**Files:**
- Modify: `scraper.py` (hole_stadtlabor, ca. Zeile 2578–2745)

Die Stadtlabor-Seite zeigt Laufzeiten im Titel: "Vernissage 21. Februar 2026 bis 29. März 2026" oder "ab 10.01.2026 bis 14.02.2026".

- [ ] **Step 1: Laufzeit-Regex für den Titel entwickeln und testen**

```bash
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -c "
import re

titles = [
    '\"Federleicht\" - Kunst Vernissage 21. Februar 2026 bis 29. März 2026',
    'MUMPITZ ab 10.01.2026 bis 14.02.2026',
    'Zwischen Haut und Seele Vernissage 23.11.2025 Ausstellung bis zum 3.01.2026',
    'Gemeinschaftsausstellung HORIZONTE 11.10.2025 Vernissage 17 Uhr',
    'Vernissage und Ausstellung - Runenraunen und Steinwelten',
]

de_monate = {
    'januar': 1, 'februar': 2, 'märz': 3, 'april': 4, 'mai': 5,
    'juni': 6, 'juli': 7, 'august': 8, 'september': 9, 'oktober': 10,
    'november': 11, 'dezember': 12,
}
en_monate = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5,
    'june': 6, 'july': 7, 'august': 8, 'september': 9, 'october': 10,
    'november': 11, 'december': 12,
}

for t in titles:
    # Pattern: 'bis (zum)? DD. Monat YYYY' or 'bis DD.MM.YYYY'
    m1 = re.search(r'bis\s+(?:zum\s+)?(\d{1,2})\.?\s+(\w+)\.?\s+(\d{4})', t)
    m2 = re.search(r'bis\s+(?:zum\s+)?(\d{1,2})\.(\d{1,2})\.(\d{4})', t)
    if m1:
        monat_str = m1.group(2).lower()
        monat_nr = de_monate.get(monat_str) or en_monate.get(monat_str)
        print(f'  Ende (Monat): {m1.group(1)}.{monat_nr}.{m1.group(3)} | {t[:60]}')
    elif m2:
        print(f'  Ende (DD.MM): {m2.group(1)}.{m2.group(2)}.{m2.group(3)} | {t[:60]}')
    else:
        print(f'  Kein Ende | {t[:60]}')
"
```

Expected: "Federleicht" → 29.3.2026, "MUMPITZ" → 14.02.2026, "Zwischen Haut" → 3.01.2026, "HORIZONTE" → kein Ende, "Runenraunen" → kein Ende.

- [ ] **Step 2: Enddatum-Parsing in hole_stadtlabor() einbauen**

Direkt nach dem bestehenden Vernissage-Parsing-Block (vor dem `continue`), das Enddatum aus dem kombinierten Text parsen. Bei allen drei Code-Pfaden (Vernissage mit Datum+Uhrzeit, Vernissage nur mit Datum, Fallback Blog-Datum) das `datum_ende` setzen:

```python
        # Enddatum: "bis (zum)? DD. Monat YYYY" oder "bis DD.MM.YYYY"
        ende_datum = None
        m_ende1 = re.search(
            r'bis\s+(?:zum\s+)?(\d{1,2})\.?\s+(\w+)\.?\s+(\d{4})', combined,
        )
        m_ende2 = re.search(
            r'bis\s+(?:zum\s+)?(\d{1,2})\.(\d{1,2})\.(\d{4})', combined,
        )
        if m_ende1:
            e_monat_str = m_ende1.group(2).lower().rstrip('.')
            e_monat_num = de_monate.get(e_monat_str) or _MONATE_EN.get(e_monat_str)
            if e_monat_num:
                try:
                    ende_datum = datetime(int(m_ende1.group(3)), e_monat_num, int(m_ende1.group(1)))
                except ValueError:
                    pass
        elif m_ende2:
            try:
                e_j = int(m_ende2.group(3))
                if e_j < 100:
                    e_j += 2000
                ende_datum = datetime(e_j, int(m_ende2.group(2)), int(m_ende2.group(1)))
            except ValueError:
                pass
```

Dann bei jedem `Termin()`-Aufruf innerhalb der Funktion `datum_ende=ende_datum` hinzufügen.

- [ ] **Step 3: Monatsübergreifende Sichtbarkeit**

Aktuell zeigt der Scraper einen Termin nur im Monat des Startdatums. Mit `datum_ende` soll eine laufende Ausstellung auch in Folgemonaten erscheinen. Dazu die bestehende Monatsfilter-Logik anpassen:

Statt `if _im_monat(v_datum, jahr, monat)` prüfen wir:

```python
def _termin_in_monat(datum_start, datum_ende, jahr, monat):
    """Prüft ob ein Termin im Zielmonat sichtbar sein soll."""
    if _im_monat(datum_start, jahr, monat):
        return True
    if datum_ende:
        from calendar import monthrange
        erster = datetime(jahr, monat, 1)
        letzter = datetime(jahr, monat, monthrange(jahr, monat)[1])
        return datum_start <= letzter and datum_ende >= erster
    return False
```

Diese Hilfsfunktion als modulweite Funktion in `scraper.py` definieren (nach `_im_monat`). Dann in `hole_stadtlabor()` alle `_im_monat()`-Aufrufe durch `_termin_in_monat(v_datum, ende_datum, jahr, monat)` ersetzen.

**Wichtig:** Bei Terminen, die in einem Folgemonat erscheinen (Startdatum liegt vor dem Zielmonat), das `datum` auf den 1. des Monats setzen, damit sie oben in der Liste erscheinen — analog zum Atelierhaus-Pattern:

```python
if not _im_monat(v_datum, jahr, monat) and ende_datum:
    # Laufende Ausstellung: Datum auf Monatsanfang setzen
    v_datum = datetime(jahr, monat, 1)
```

- [ ] **Step 4: Manueller Funktionstest**

```bash
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -c "
from scraper import hole_stadtlabor
# Federleicht: Vernissage 21.02., Ausstellung bis 29.03.
for m in [2, 3]:
    termine = hole_stadtlabor(2026, m)
    for t in termine:
        ende = t.datum_ende.strftime('%d.%m.%Y') if t.datum_ende else 'kein Ende'
        print(f'{m:02d}/2026: {t.datum_formatiert()} | bis {ende} | {t.name[:50]}')
"
```

Expected: "Federleicht" erscheint sowohl im Februar (Vernissage) als auch im März (laufend), mit `datum_ende=29.03.2026`.

- [ ] **Step 5: Alle Tests ausführen**

Run: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest tests/ -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add scraper.py
git commit -m "feat: stadtlabor scraper parses exhibition end dates and shows in spanning months"
```

---

### Task 4: hole_atelierhaus() — monatsübergreifende Logik mit _termin_in_monat()

**Files:**
- Modify: `scraper.py` (hole_atelierhaus)

Der Atelierhaus-Scraper hat bereits mehrtägige Logik. Jetzt nutzt er `_termin_in_monat()` konsistent.

- [ ] **Step 1: _termin_in_monat() anwenden**

Prüfe, dass die bestehende Monatsüberlappungslogik im Atelierhaus-Scraper (`if not (datum_start <= letzte and datum_end >= erste): continue`) weiterhin korrekt funktioniert. Sie kann bleiben, da sie das gleiche leistet wie `_termin_in_monat()`. Keine Änderung nötig, sofern `datum_ende` bereits in Task 2 gesetzt wird.

- [ ] **Step 2: Funktionstest**

```bash
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -c "
from scraper import hole_atelierhaus
for m in range(1, 7):
    termine = hole_atelierhaus(2026, m)
    for t in termine:
        ende = t.datum_ende.strftime('%d.%m.%Y') if t.datum_ende else '-'
        print(f'{m:02d}/2026: {t.name[:50]} | Ende: {ende}')
"
```

- [ ] **Step 3: Commit (falls Änderungen nötig waren)**

```bash
git add scraper.py
git commit -m "refactor: atelierhaus uses consistent multi-day pattern"
```

---

### Task 5: Deduplizierung für Termine mit datum_ende anpassen

**Files:**
- Modify: `app.py` (entferne_duplikate, ca. Zeile 238–284)
- Modify: `tests/test_dedup.py`

Mehrtägige Termine (mit `datum_ende`) werden nach Startdatum gruppiert. Wenn eine Ausstellung von Aggregatoren (stadt-re, vesterleben) als Einzeltermin erkannt wird, soll sie trotzdem als Duplikat des mehrtägigen Termins gelten. Außerdem: `datum_ende` aus dem Duplikat übernehmen, falls beim Gewinner nicht vorhanden.

- [ ] **Step 1: Test für datum_ende-Übernahme bei Dedup schreiben**

```python
def test_datum_ende_wird_aus_duplikat_uebernommen():
    """Wenn der Gewinner kein datum_ende hat, wird es vom Duplikat übernommen."""
    from datetime import datetime
    from app import entferne_duplikate
    from scraper import Termin

    # Spezifischer Veranstalter ohne datum_ende
    t1 = Termin(
        name='Ausstellung Lichtblicke',
        datum=datetime(2026, 3, 1),
        uhrzeit='17:00 Uhr',
        ort='Galerie',
        link='https://galerie.de/lichtblicke',
        quelle='kunsthalle',
    )
    # Aggregator mit datum_ende
    t2 = Termin(
        name='Ausstellung Lichtblicke',
        datum=datetime(2026, 3, 1),
        uhrzeit='siehe Website',
        ort='Recklinghausen',
        link='https://stadt-re.de/event/123',
        quelle='stadt-re',
        datum_ende=datetime(2026, 4, 15),
    )

    ergebnis = entferne_duplikate([t1, t2])
    assert len(ergebnis) == 1
    assert ergebnis[0].quelle == 'kunsthalle'       # Veranstalter gewinnt
    assert ergebnis[0].datum_ende == datetime(2026, 4, 15)  # datum_ende übernommen
```

- [ ] **Step 2: Test ausführen, Fehlschlag bestätigen**

Run: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest tests/test_dedup.py::test_datum_ende_wird_aus_duplikat_uebernommen -v`
Expected: FAIL — `datum_ende` wird noch nicht übernommen.

- [ ] **Step 3: Feld-Übernahme in entferne_duplikate() ergänzen**

Im Dedup-Block (ca. Zeile 269–277), wo fehlende Felder ergänzt werden, nach der `ort`-Übernahme einfügen:

```python
if not vorhandener.datum_ende and kandidat.datum_ende:
    vorhandener.datum_ende = kandidat.datum_ende
```

- [ ] **Step 4: Test ausführen, Erfolg bestätigen**

Run: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest tests/test_dedup.py -v`
Expected: PASS (alle Tests)

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_dedup.py
git commit -m "feat: dedup merges datum_ende from duplicates"
```

---

### Task 6: Termine in laufende und tagesaktuelle aufteilen (app.py)

**Files:**
- Modify: `app.py` (generiere_html, ca. Zeile 318ff)

- [ ] **Step 1: Trennlogik in generiere_html() einbauen**

Am Anfang von `generiere_html()`, nach dem Empfang der Termine-Liste, die Termine in zwei Listen aufteilen:

```python
    from calendar import monthrange

    erster_tag = datetime(jahr, monat, 1)
    letzter_tag = datetime(jahr, monat, monthrange(jahr, monat)[1])

    laufende = []
    tagesaktuelle = []
    for t in termine:
        if t.datum_ende and t.datum_ende > t.datum:
            laufende.append(t)
        else:
            tagesaktuelle.append(t)
```

Die bestehende Gruppierung nach Datum (`nach_datum`) und Rendering verwendet ab jetzt `tagesaktuelle` statt `termine`.

- [ ] **Step 2: Vollständigen Lauf testen**

```bash
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 app.py 2026 3 1 --no-browser
```

Expected: Generierung funktioniert, laufende Termine werden (noch) nicht gerendert, aber die tagesaktuellen erscheinen wie gewohnt.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "refactor: split termine into laufende and tagesaktuelle in generiere_html"
```

---

### Task 7: Pinned-Bereich HTML und CSS

**Files:**
- Modify: `app.py` (generiere_html — HTML-Ausgabe und CSS)

- [ ] **Step 1: HTML für den Pinned-Bereich generieren**

Nach dem Kalender-Grid und vor der Filterleiste (ca. Zeile 1071–1073 im generierten HTML) den Pinned-Bereich einfügen. Der Bereich erscheint nur, wenn `laufende` nicht leer ist.

```python
    # Pinned-Bereich: Laufende Veranstaltungen
    pinned_html = ''
    if laufende:
        pinned_html += '<div class="laufende-events">\n'
        pinned_html += '<h2 class="laufende-titel">Laufende Veranstaltungen</h2>\n'
        pinned_html += '<div class="laufende-grid">\n'
        for t in sorted(laufende, key=lambda x: (x.datum_ende or x.datum, x.name)):
            name_escaped = _html.escape(t.name)
            ort_escaped = _html.escape(t.ort) if t.ort else ''
            link_safe = t.link if t.link and t.link.startswith(('http://', 'https://')) else ''
            quelle_label = QUELLEN.get(t.quelle, t.quelle)
            badge_class = badge_classes.get(t.quelle, 'badge-default')

            # Laufzeit formatieren
            start_str = t.datum.strftime('%d.%m.')
            ende_str = t.datum_ende.strftime('%d.%m.%Y') if t.datum_ende else ''
            laufzeit = f'{start_str} – {ende_str}' if ende_str else f'ab {start_str}'

            if link_safe:
                name_html = f'<a href="{link_safe}" target="_blank" rel="noopener noreferrer">{name_escaped}</a>'
            else:
                name_html = f'<span>{name_escaped}</span>'

            pinned_html += f'''<div class="laufend-karte" data-quelle="{t.quelle}">
    <div class="laufend-laufzeit">{laufzeit}</div>
    <div class="laufend-name">{name_html}</div>
    <div class="laufend-ort">{ort_escaped}</div>
    <div class="laufend-badges">
        <span class="badge {badge_class}">{quelle_label}</span>
    </div>
</div>\n'''
        pinned_html += '</div>\n</div>\n'
```

Diesen `pinned_html` vor der Filterleiste ins HTML einfügen.

- [ ] **Step 2: CSS für den Pinned-Bereich**

Im CSS-Block (innerhalb des `<style>`-Tags) hinzufügen:

```css
        .laufende-events {{
            margin: 0 0 20px 0;
            padding: 15px;
            background: var(--card-bg);
            border-radius: 12px;
            border: 1px solid var(--border-color);
        }}
        .laufende-titel {{
            font-size: 1em;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin: 0 0 12px 0;
        }}
        .laufende-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 10px;
        }}
        .laufend-karte {{
            padding: 10px 12px;
            background: var(--hover-color);
            border-radius: 8px;
            border-left: 3px solid var(--accent-color);
        }}
        .laufend-laufzeit {{
            font-size: 0.8em;
            color: var(--accent-color);
            font-weight: 600;
            margin-bottom: 4px;
        }}
        .laufend-name {{
            font-weight: 500;
            margin-bottom: 3px;
        }}
        .laufend-name a {{
            color: var(--text-color);
            text-decoration: none;
        }}
        .laufend-name a:hover {{
            color: var(--accent-color);
        }}
        .laufend-ort {{
            font-size: 0.85em;
            color: var(--text-secondary);
        }}
        .laufend-badges {{
            margin-top: 6px;
        }}
        @media (max-width: 600px) {{
            .laufende-grid {{
                grid-template-columns: 1fr;
            }}
        }}
```

- [ ] **Step 3: Vollständigen Lauf testen**

```bash
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 app.py 2026 2 2 --no-browser
```

Öffne `termine_re_2026_02.html` und `termine_re_2026_03.html` im Browser. Prüfe:
- Pinned-Bereich erscheint, wenn laufende Termine vorhanden
- Karten zeigen Laufzeit, Name, Ort, Badge
- Grid-Layout responsive (Desktop: mehrere Spalten, Mobil: eine Spalte)
- Dark Mode funktioniert

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add pinned section for ongoing events (exhibitions, festivals)"
```

---

### Task 8: JS-Filter für Pinned-Bereich erweitern

**Files:**
- Modify: `app.py` (JavaScript in generiere_html)

Die Quellen-Dropdown-Filterung und VHS/Kino-Toggle müssen auch die Pinned-Karten ein-/ausblenden.

- [ ] **Step 1: filterTermine() um Pinned-Karten erweitern**

In der `filterTermine()`-Funktion (ca. Zeile 1182) nach dem bestehenden `.termin`-Filter-Block den Pinned-Bereich ergänzen:

```javascript
        // Laufende Events filtern
        const laufende = document.querySelectorAll('.laufend-karte');
        laufende.forEach(k => {
            const quelleMatch = !quelleFilter || k.dataset.quelle === quelleFilter;
            const vhsMatch = !vhsAusgeblendet || k.dataset.quelle !== 'vhs';
            const kinoMatch = !kinoAusgeblendet || k.dataset.quelle !== 'cineworld';

            if (quelleMatch && vhsMatch && kinoMatch) {
                k.classList.remove('hidden');
            } else {
                k.classList.add('hidden');
            }
        });

        // Pinned-Container ausblenden wenn alle Karten hidden
        const pinned = document.querySelector('.laufende-events');
        if (pinned) {
            const sichtbareKarten = pinned.querySelectorAll('.laufend-karte:not(.hidden)');
            pinned.classList.toggle('hidden', sichtbareKarten.length === 0);
        }
```

- [ ] **Step 2: Testen**

```bash
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 app.py 2026 2 2 --no-browser
```

Im Browser testen:
- Quellen-Dropdown auf eine spezifische Quelle setzen → nur passende Karten im Pinned-Bereich
- VHS/Kino-Toggle → keine Auswirkung auf Pinned (da Ausstellungen, nicht VHS/Kino)
- Wenn alle laufenden gefiltert → ganzer Pinned-Container verschwindet

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: JS filter applies to pinned ongoing events section"
```

---

### Task 9: Terme-Count im Filter aktualisieren

**Files:**
- Modify: `app.py` (JavaScript)

Der Zähler "N Termine" in der Filterleiste soll auch laufende Events mitzählen.

- [ ] **Step 1: Zähler anpassen**

In `filterTermine()` den Zähler erweitern. Nach der laufende-Filterung:

```javascript
        // Laufende sichtbare mitzählen
        const sichtbareLaufende = document.querySelectorAll('.laufend-karte:not(.hidden)').length;
        document.getElementById('termine-count').textContent = sichtbar + sichtbareLaufende;
```

- [ ] **Step 2: Initiale Zahl beim Seitenaufruf korrigieren**

In `generiere_html()` die initiale `{count}`-Zahl (die im HTML steht) anpassen:

```python
count = len(tagesaktuelle) + len(laufende)
```

(statt nur `len(termine)`)

- [ ] **Step 3: Testen und Commit**

```bash
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 app.py 2026 2 2 --no-browser
git add app.py
git commit -m "fix: termine count includes ongoing events"
```

---

### Task 10: Quellen-Dropdown um laufende Events erweitern

**Files:**
- Modify: `app.py` (generiere_html, Dropdown-Generierung)

Das Quellen-Dropdown zeigt nur Quellen, die mindestens einen Termin im Monat haben. Es muss auch Quellen aus `laufende` berücksichtigen.

- [ ] **Step 1: Dropdown-Logik anpassen**

In `generiere_html()` wird das Dropdown basierend auf den vorhandenen Quellen gefüllt (ca. Zeile 1073ff). Sicherstellen, dass sowohl `tagesaktuelle` als auch `laufende` in die Quellen-Sammlung einfließen:

```python
    alle_quellen_im_monat = set()
    for t in tagesaktuelle + laufende:
        if t.quelle:
            alle_quellen_im_monat.add(t.quelle)
```

- [ ] **Step 2: Testen und Commit**

```bash
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 app.py 2026 3 1 --no-browser
git add app.py
git commit -m "fix: source dropdown includes sources from ongoing events"
```

---

### Task 11: Abschlusstest und Aufräumen

**Files:**
- Modify: `CLAUDE.md` (Quellentabelle, Architektur-Beschreibung)

- [ ] **Step 1: Vollständiger Testlauf über mehrere Monate**

```bash
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 app.py 2026 2 4 --no-browser
```

Prüfe in jedem generierten HTML:
- Pinned-Bereich zeigt nur laufende Ausstellungen
- Tagesansicht zeigt keine Termine, die im Pinned-Bereich sind (keine Dopplung)
- Filter funktioniert für beide Bereiche
- Zähler stimmt
- Dark Mode funktioniert
- Mobil-Layout (Browserfenster schmal ziehen)

- [ ] **Step 2: Alle Tests ausführen**

Run: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest tests/ -v`
Expected: PASS

- [ ] **Step 3: CLAUDE.md aktualisieren**

In der Architektur-Beschreibung den Pinned-Bereich erwähnen. In der Quellentabelle vermerken, welche Scraper `datum_ende` unterstützen (Atelierhaus, Stadtlabor).

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document pinned ongoing events feature and datum_ende support"
```
