# Quellen-Tier-Bonus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aggregator-Quellen (Stadt RE, Vesterleben, Der Recklinghäuser) bekommen einen Score-Malus von −10, sodass spezifische Veranstalter (NLGR u.a.) im Dedup-Vergleich immer gewinnen.

**Architecture:** Neue modulweite Konstante `_QUELLEN_TIER` in `app.py`; `_termin_score()` liest daraus und subtrahiert 10 bei Tier-2-Quellen. Kein weiterer Code wird geändert.

**Tech Stack:** Python 3.14, pytest (neu eingeführt für dieses Projekt)

**Spec:** `docs/superpowers/specs/2026-03-21-quellen-tier-dedup-design.md`

---

## Betroffene Dateien

| Datei | Aktion |
|-------|--------|
| `Recklinghausen/app.py` | Modify: `_QUELLEN_TIER`-Konstante ergänzen (~Zeile 110), `_termin_score()` anpassen (~Zeile 204) |
| `Recklinghausen/tests/test_dedup.py` | Create: Tests für `_termin_score()` und `entferne_duplikate()` |

---

### Task 1: Test-Datei anlegen und Tier-Score-Tests schreiben

**Files:**
- Create: `Recklinghausen/tests/__init__.py`
- Create: `Recklinghausen/tests/test_dedup.py`

- [ ] **Step 1: Tests-Verzeichnis und `__init__.py` anlegen**

```bash
cd /Volumes/ki/claude/termine/Recklinghausen
mkdir -p tests
touch tests/__init__.py
```

- [ ] **Step 2: Failing Tests schreiben**

Datei `tests/test_dedup.py`:

```python
"""Tests für Dedup-Logik in app.py."""
import sys
import os
from datetime import datetime

# app.py liegt im Parent-Verzeichnis
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper import Termin
from app import _termin_score, entferne_duplikate


def _termin(name, quelle, link='', uhrzeit='', beschreibung='', ort=''):
    return Termin(
        name=name,
        datum=datetime(2026, 3, 15),
        uhrzeit=uhrzeit,
        ort=ort,
        link=link,
        beschreibung=beschreibung,
        quelle=quelle,
        kategorie='',
    )


# --- _termin_score ---

def test_veranstalter_score_kein_malus():
    """Ein Veranstalter (z.B. nlgr) bekommt keinen Malus."""
    t = _termin('Konzert', 'nlgr', link='https://nlgr.de', uhrzeit='20:00 Uhr')
    assert _termin_score(t) == 4  # link(2) + uhrzeit(2)


def test_aggregator_bekommt_malus():
    """Stadt RE bekommt −10 Malus."""
    t = _termin('Konzert', 'stadt-re',
                link='https://re.de', uhrzeit='20:00 Uhr',
                beschreibung='Toll', ort='Stadtbibliothek')
    # Basis: 6, nach Malus: -4
    assert _termin_score(t) == -4


def test_vesterleben_bekommt_malus():
    """Vesterleben bekommt −10 Malus."""
    t = _termin('Event', 'vesterleben', link='https://vest.de')
    assert _termin_score(t) == -8  # link(2) - 10


def test_recklinghaeuser_bekommt_malus():
    """Der Recklinghäuser bekommt −10 Malus."""
    t = _termin('Event', 'recklinghaeuser', link='https://re.de')
    assert _termin_score(t) == -8  # link(2) - 10


def test_veranstalter_schlaegt_aggregator_immer():
    """Veranstalter ohne ein einziges Feld (Score 0) schlägt Aggregator mit allem (Score -4)."""
    veranstalter = _termin('Konzert', 'nlgr')  # Score: 0
    aggregator = _termin('Konzert', 'stadt-re',
                         link='https://re.de', uhrzeit='20:00',
                         beschreibung='Text', ort='Ort')  # Score: -4
    assert _termin_score(veranstalter) > _termin_score(aggregator)


# --- entferne_duplikate ---

def test_veranstalter_gewinnt_gegen_aggregator():
    """NLGR-Eintrag bleibt, Stadt-RE-Eintrag wird entfernt."""
    nlgr = _termin('Jahreskonzert NLGR', 'nlgr',
                   link='https://nlgr.de/konzert', uhrzeit='19:30 Uhr')
    stadt_re = _termin('Jahreskonzert NLGR', 'stadt-re',
                       link='https://re.de/x', uhrzeit='19:30 Uhr',
                       beschreibung='Tolle Veranstaltung', ort='Stadtbibliothek')

    ergebnis = entferne_duplikate([nlgr, stadt_re])

    assert len(ergebnis) == 1
    assert ergebnis[0].quelle == 'nlgr'


def test_aggregator_felder_werden_aufgefuellt():
    """NLGR gewinnt, bekommt aber Beschreibung + Ort aus Stadt RE."""
    nlgr = _termin('Jahreskonzert NLGR', 'nlgr',
                   link='https://nlgr.de/konzert', uhrzeit='19:30 Uhr')
    stadt_re = _termin('Jahreskonzert NLGR', 'stadt-re',
                       link='https://re.de/x', uhrzeit='19:30 Uhr',
                       beschreibung='Tolle Veranstaltung', ort='Stadtbibliothek')

    ergebnis = entferne_duplikate([nlgr, stadt_re])

    assert ergebnis[0].beschreibung == 'Tolle Veranstaltung'
    assert ergebnis[0].ort == 'Stadtbibliothek'
    # Link bleibt der NLGR-Link, nicht Stadt-RE-Link
    assert ergebnis[0].link == 'https://nlgr.de/konzert'


def test_zwei_aggregatoren_einer_bleibt():
    """Wenn Stadt RE und Vesterleben das gleiche Event listen, bleibt nur einer."""
    stadt_re = _termin('Stadtfest', 'stadt-re',
                       link='https://re.de', uhrzeit='12:00 Uhr',
                       beschreibung='Großes Fest', ort='Marktplatz')
    vesterleben = _termin('Stadtfest', 'vesterleben',
                          link='https://vest.de')

    ergebnis = entferne_duplikate([stadt_re, vesterleben])

    assert len(ergebnis) == 1
    assert ergebnis[0].quelle == 'stadt-re'  # höherer Basis-Score (−4 vs −8)
```

- [ ] **Step 3: Tests ausführen (müssen fehlschlagen)**

```bash
cd /Volumes/ki/claude/termine/Recklinghausen
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest tests/test_dedup.py -v
```

Erwartetes Ergebnis: Tests `test_aggregator_bekommt_malus`, `test_vesterleben_bekommt_malus` usw. schlagen fehl, weil der Malus noch nicht implementiert ist.

---

### Task 2: `_QUELLEN_TIER`-Konstante und Malus implementieren

**Files:**
- Modify: `Recklinghausen/app.py` (~Zeile 110 und ~Zeile 204)

- [ ] **Step 1: Konstante nach `_normalisiere()` einfügen (~Zeile 110)**

Nach dem Block `def _normalisiere(...)` (endet ca. Zeile 109) folgende Konstante einfügen:

```python
# Tier 2 = Aggregatoren (listen auch fremde Events auf → Malus im Score)
# Tier 1 = Veranstalter (Default; listen nur eigene Events)
_QUELLEN_TIER: dict[str, int] = {
    'stadt-re': 2,
    'vesterleben': 2,
    'recklinghaeuser': 2,
    # 'regioactive': 2,  # blockiert seit 2026-03; bei Reaktivierung aktivieren
}
```

- [ ] **Step 2: `_termin_score()` um Malus erweitern (~Zeile 204)**

Die bestehende Funktion `_termin_score()` am Ende vor `return score` ergänzen:

```python
def _termin_score(t: Termin) -> int:
    """Bewertet die Informationsqualität eines Termins (höher = besser).
    Aggregator-Quellen (Tier 2) erhalten −10 Malus, damit spezifische
    Veranstalter im Dedup-Vergleich immer gewinnen.
    """
    score = 0
    if t.link:
        score += 2
    if t.uhrzeit and t.uhrzeit not in ('ganztägig', 'siehe Website'):
        score += 2
    if t.beschreibung:
        score += 1
    if t.ort:
        score += 1
    if _QUELLEN_TIER.get(t.quelle, 1) == 2:
        score -= 10  # Aggregator-Malus: Veranstalter gewinnen immer
    return score
```

- [ ] **Step 3: Tests ausführen (müssen alle grün sein)**

```bash
cd /Volumes/ki/claude/termine/Recklinghausen
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pytest tests/test_dedup.py -v
```

Erwartetes Ergebnis: Alle 8 Tests PASS.

- [ ] **Step 4: Commit**

```bash
cd /Volumes/ki/claude/termine/Recklinghausen
git add app.py tests/
git commit -m "feat: Aggregator-Quellen bekommen −10 Score-Malus in Dedup

Stadt RE, Vesterleben und Der Recklinghäuser sind Aggregatoren –
sie listen auch Events anderer Veranstalter auf. Mit dem Malus
gewinnen spezifische Veranstalter (NLGR u.a.) immer den
Dedup-Vergleich, auch wenn der Aggregator mehr Felder gefüllt hat.

Fixes: NLGR-Events wurden durch Stadt-RE-Einträge verdrängt."
```

---

### Task 3: Manuelle Verifikation

- [ ] **Step 1: App für aktuellen Monat ausführen**

```bash
cd /Volumes/ki/claude/termine/Recklinghausen
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 app.py --no-browser
```

Auf Ausgabe achten: `[Fuzzy-Dedup]` und `[Keyword-Dedup]` Zeilen zeigen, welche Duplikate erkannt wurden. NLGR-Events dürfen jetzt nicht mehr von Stadt RE verdrängt werden.

- [ ] **Step 2: HTML im Browser prüfen**

```bash
open termine_re_2026_03.html
```

Im Quellen-Dropdown "NLGR" auswählen und prüfen, ob NLGR-Events jetzt sichtbar sind und die richtige Quelle tragen.
