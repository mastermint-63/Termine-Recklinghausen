# Design: Quellen-Tier-Bonus für Dedup

**Datum:** 2026-03-21
**Projekt:** Termine Recklinghausen (`Recklinghausen/app.py`)
**Anlass:** Ralf meldet, dass NLGR-Veranstaltungen durch "Stadt RE"-Einträge verdrängt werden, obwohl NLGR der eigentliche Veranstalter ist.

## Problem

`entferne_duplikate()` sortiert Duplikate nach *Infomenge* (Score: Link, Uhrzeit, Beschreibung, Ort). "Stadt RE" ruft für jeden Termin eine Detailseite ab und hat dadurch oft mehr Felder gefüllt — und gewinnt den Score-Vergleich gegen den eigentlichen Veranstalter. NLGR (und potentiell andere spezifische Veranstalter) verschwinden, obwohl sie die primäre Quelle sind.

**Ursache:** Der Score misst Infomenge, nicht Veranstalterzuständigkeit. Stadt RE ist ein Aggregator (listet alles auf, was an städtischen Orten stattfindet), NLGR ist der eigentliche Veranstalter.

## Lösung: Quellen-Tier-Bonus

### Neue Konstante `_QUELLEN_TIER`

```python
# Tier 2 = Aggregatoren (listen auch fremde Events auf)
# Tier 1 = Veranstalter (Default; listen nur eigene Events)
_QUELLEN_TIER: dict[str, int] = {
    'stadt-re': 2,
    'vesterleben': 2,
    'recklinghaeuser': 2,
}
```

Aggregatoren: **Stadt RE**, **Vesterleben**, **Der Recklinghäuser** — diese drei Quellen listen Veranstaltungen anderer Organisationen auf, weil sie an städtischen oder lokalen Orten stattfinden.

### Änderung in `_termin_score()`

```python
def _termin_score(t: Termin) -> int:
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
        score -= 10  # Aggregator-Malus
    return score
```

### Warum −10?

- Max-Score eines Veranstalters: 6 (Link + Uhrzeit + Beschreibung + Ort)
- Aggregator mit vollem Score: 6 − 10 = −4
- Veranstalter gewinnt immer, auch mit nur einem Feld (Score 2 > −4)

### Ergänzungs-Logik bleibt erhalten

Die bestehende Logik in `entferne_duplikate()` füllt fehlende Felder des Gewinners aus dem Verlierer auf (Beschreibung, Uhrzeit, Ort). Das bleibt unverändert: NLGR gewinnt als Quelle, bekommt aber trotzdem die Beschreibung aus dem Stadt-RE-Eintrag — das Beste aus beiden Welten.

## Betroffene Dateien

| Datei | Änderung |
|-------|----------|
| `Recklinghausen/app.py` | Neue Konstante `_QUELLEN_TIER` + Malus in `_termin_score()` |

## Nicht betroffen

- `scraper.py` — keine Änderung
- HTML-Ausgabe / CSS / JS — keine Änderung
- Dedup-Stufen (Exakt, Fuzzy, Keyword) — keine Änderung
- Ergänzungs-Logik (fehlende Felder auffüllen) — keine Änderung
