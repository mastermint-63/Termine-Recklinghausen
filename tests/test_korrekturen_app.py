"""Tests für Korrekturen und Absagen im Generator (app.py)."""
import json
import re
from datetime import date, datetime

import app
import hw_import as hw
from scraper import Termin

TAG = datetime(2026, 10, 23)


def _t(name, quelle, uhrzeit="10:00 Uhr", **kw):
    return Termin(name=name, datum=TAG.replace(hour=10), uhrzeit=uhrzeit, ort=kw.pop("ort", "Altstadtschmiede"),
                  link=kw.pop("link", ""), quelle=quelle, **kw)


def _k(**kw):
    k = {"datum": "2026-10-23", "name": "Offene Schmiede", "name_norm": "offene schmiede",
         "quelle": "altstadtschmiede", "aenderung": {}, "absage": False, "hw_mail": "kalender:x",
         "freigegeben": True, "angelegt": "2026-10-11"}
    k.update(kw)
    return k


def test_korrektur_greift_vor_dublettenpruefung():
    """Aggregator-Dublette wird mitkorrigiert, danach bleibt ein Termin mit der neuen Uhrzeit."""
    termine = [_t("Offene Schmiede", "altstadtschmiede"), _t("Offene Schmiede", "stadt-re"),
               _t("Lesung Müller", "nlgr", "19:00 Uhr")]
    verwaist = app.wende_korrekturen_an(termine, [_k(aenderung={"uhrzeit": "14:00"})], 2026, 10)
    assert verwaist == []
    ergebnis = app.entferne_duplikate(termine)
    schmiede = [t for t in ergebnis if "Schmiede" in t.name]
    assert len(schmiede) == 1 and schmiede[0].uhrzeit == "14:00 Uhr" and schmiede[0].datum.hour == 14
    assert [t for t in ergebnis if t.name == "Lesung Müller"][0].uhrzeit == "19:00 Uhr"


def test_korrektur_ort():
    termine = [_t("Offene Schmiede", "altstadtschmiede")]
    app.wende_korrekturen_an(termine, [_k(aenderung={"ort": "Rathaus, Rathausplatz 3"})], 2026, 10)
    assert termine[0].ort == "Rathaus, Rathausplatz 3"


def test_absage_setzt_flag():
    termine = [_t("Offene Schmiede", "altstadtschmiede")]
    app.wende_korrekturen_an(termine, [_k(absage=True)], 2026, 10)
    assert termine[0].abgesagt is True


def test_nicht_freigegebene_und_datumsaenderung_greifen_nicht():
    termine = [_t("Offene Schmiede", "altstadtschmiede")]
    app.wende_korrekturen_an(termine, [_k(freigegeben=False, absage=True),
                                       _k(aenderung={"datum": "2026-10-30"})], 2026, 10)
    assert termine[0].abgesagt is False and termine[0].datum.day == 23


def test_korrektur_anderer_tag_greift_nicht():
    termine = [_t("Offene Schmiede", "altstadtschmiede")]
    app.wende_korrekturen_an(termine, [_k(datum="2026-10-24", absage=True)], 2026, 10)
    assert termine[0].abgesagt is False


def test_verwaiste_korrektur_wird_geloggt(capsys):
    termine = [_t("Lesung Müller", "nlgr")]
    verwaist = app.wende_korrekturen_an(termine, [_k(absage=True), _k(datum="2026-11-05", absage=True)], 2026, 10)
    assert [k["datum"] for k in verwaist] == ["2026-10-23"]  # November gehört nicht zu diesem Lauf
    assert "nicht angewendet" in capsys.readouterr().out


def test_absage_ueberlebt_dublettenpruefung():
    """Gewinnt der nicht abgesagte Doppelgänger, übernimmt er die Absage."""
    termine = [_t("Offene Schmiede", "manuell", abgesagt=True, link=""),
               _t("Offene Schmiede", "altstadtschmiede", link="https://x.example/s", beschreibung="lang")]
    ergebnis = app.entferne_duplikate(termine)
    assert len(ergebnis) == 1 and ergebnis[0].abgesagt is True


def _html(termine):
    return app.generiere_html(termine, 2026, 10, [(2026, 10)], "termine_re_2026_10.html")


def test_absage_wird_sichtbar_markiert():
    s = _html([_t("Offene Schmiede", "altstadtschmiede", abgesagt=True), _t("Lesung Müller", "nlgr")])
    assert '<div class="termin" data-quelle="altstadtschmiede" data-abgesagt="1">' in s
    assert '<div class="termin" data-quelle="nlgr">' in s
    block = s.split('data-quelle="altstadtschmiede" data-abgesagt="1">')[1].split('<div class="termin"')[0]
    assert '<span class="badge badge-abgesagt">Abgesagt</span>' in block


def test_jsonld_ohne_abgesagte_termine():
    s = _html([_t("Offene Schmiede", "altstadtschmiede", abgesagt=True), _t("Lesung Müller", "nlgr")])
    ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', s, re.S).group(1))
    namen = [e["name"] for e in ld["mainEntity"]["itemListElement"]]
    assert namen == ["Lesung Müller"]


def test_monatsseite_mit_absage_bleibt_fuer_import_lesbar(tmp_path, monkeypatch):
    """hw_import liest die generierte Seite (Dubletten, Zielsuche): auch abgesagte Termine."""
    (tmp_path / "termine_re_2026_10.html").write_text(
        _html([_t("Offene Schmiede", "altstadtschmiede", abgesagt=True), _t("Lesung Müller", "nlgr")]),
        encoding="utf-8")
    monkeypatch.setattr(hw, "HIER", tmp_path)
    hw._lese_monatsseite.cache_clear()
    try:
        termine = hw.lade_bestehende(date(2026, 10, 23))
    finally:
        hw._lese_monatsseite.cache_clear()
    assert sorted(t.name for t in termine) == ["Lesung Müller", "Offene Schmiede"]
    assert {t.quelle for t in termine} == {"altstadtschmiede", "nlgr"}


def test_korrektur_trifft_keinen_kurzen_fremden_titel():
    """Teilstring nur ab einer Mindestlänge: 'Party' ist nicht 'Halloween-Party im Moondock'."""
    termine = [_t("Halloween-Party im Moondock", "moondock"), _t("Party", "facebook")]
    app.wende_korrekturen_an(termine, [_k(name_norm="halloween party im moondock", absage=True)], 2026, 10)
    assert [t.abgesagt for t in termine] == [True, False]


def test_korrektur_trifft_aggregator_mit_praefix():
    termine = [_t("Offene Schmiede", "altstadtschmiede"), _t("Altstadtschmiede: Offene Schmiede", "stadt-re")]
    app.wende_korrekturen_an(termine, [_k(absage=True)], 2026, 10)
    assert [t.abgesagt for t in termine] == [True, True]


def test_korrektur_link():
    termine = [_t("Offene Schmiede", "altstadtschmiede", link="https://alt.example/x")]
    app.wende_korrekturen_an(termine, [_k(aenderung={"link": "https://neu.example/termine/"})], 2026, 10)
    assert termine[0].link == "https://neu.example/termine/"


def test_korrektur_link_unsicher_wird_ignoriert():
    termine = [_t("Offene Schmiede", "altstadtschmiede", link="https://alt.example/x")]
    app.wende_korrekturen_an(termine, [_k(aenderung={"link": 'https://x.example/"onmouseover=1'})], 2026, 10)
    assert termine[0].link == "https://alt.example/x"
