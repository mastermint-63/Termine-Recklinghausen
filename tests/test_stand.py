"""Tests für die Trennung von Abruf und Bau (termine_stand.json, app.py --nur-bauen)."""
import json
import os
import re
from datetime import datetime, timedelta

import pytest

import app
from scraper import Termin


def _termine_quelle_a(jahr, monat):
    if (jahr, monat) != (2026, 10):
        return []
    return [
        Termin(name="Offene Schmiede", datum=datetime(2026, 10, 23, 19), uhrzeit="19:00 Uhr",
               ort="Altstadtschmiede", link="https://altstadtschmiede.example/x", quelle="altstadtschmiede",
               beschreibung="Offener Abend"),
        Termin(name="Lesung Müller", datum=datetime(2026, 10, 24, 20), uhrzeit="20:00 Uhr",
               ort="Stadtbibliothek", link="", quelle="stadtbibliothek"),
    ]


def _termine_quelle_b(jahr, monat):
    if (jahr, monat) == (2026, 11):
        return [Termin(name="Jazz im November", datum=datetime(2026, 11, 5, 20), uhrzeit="20:00 Uhr",
                       ort="Kunsthalle", link="", quelle="kunsthalle")]
    if (jahr, monat) == (2026, 10):
        # Aggregator-Dublette, wird beim Bauen zusammengeführt
        return [Termin(name="Offene Schmiede", datum=datetime(2026, 10, 23, 19), uhrzeit="19:00 Uhr",
                       ort="Altstadtschmiede", link="", quelle="stadt-re")]
    return []


def _manuell(jahr, monat):
    if (jahr, monat) != (2026, 10):
        return []
    return [Termin(name="Hebbert-Fest", datum=datetime(2026, 10, 25, 15), uhrzeit="15:00 Uhr",
                   ort="Holzwurm", link="", quelle="manuell")]


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "ABRUF_SCRAPER", [(_termine_quelle_a, "Quelle A"), (_termine_quelle_b, "Quelle B")])
    monkeypatch.setattr(app, "hole_manuelle_termine", _manuell)
    korrekturen = tmp_path / "korrekturen.json"
    korrekturen.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(app, "KORREKTUREN_PFAD", str(korrekturen))
    return tmp_path


def _lauf(monkeypatch, *argv):
    monkeypatch.setattr("sys.argv", ["app.py", "2026", "10", "2", "--no-browser", *argv])
    app.main()


def _seiten(ordner):
    """Alle erzeugten Dateien, ohne die Zeitangabe „Generiert am …“."""
    ergebnis = {}
    for name in sorted(os.listdir(ordner)):
        text = (ordner / name).read_text(encoding="utf-8")
        ergebnis[name] = re.sub(r"Generiert am [^<]*", "", text)
    return ergebnis


def _verbiete_abruf(monkeypatch):
    def kein_abruf(jahr, monat):
        raise AssertionError("nur bauen darf keine Quelle abrufen")
    monkeypatch.setattr(app, "ABRUF_SCRAPER", [(kein_abruf, "verboten")])


def test_abruf_ohne_manuelle_termine():
    """Der Stand enthält nur Scraper-Ergebnisse, manuelle Termine kommen erst beim Bauen dazu."""
    assert all(fn is not app.hole_manuelle_termine for fn, _ in app.ABRUF_SCRAPER)
    assert len(app.ABRUF_SCRAPER) == len(app.SCRAPER) - 1


def test_normaler_lauf_schreibt_stand(umgebung, monkeypatch):
    stand_pfad = umgebung / "stand.json"
    _lauf(monkeypatch, "--ausgabe", str(umgebung / "site"), "--stand", str(stand_pfad))
    stand = json.loads(stand_pfad.read_text(encoding="utf-8"))
    assert set(stand["monate"]) == {"2026-10", "2026-11"}
    assert datetime.fromisoformat(stand["abgerufen"]) <= datetime.now()
    assert set(stand["quellen"]) == {"Quelle A", "Quelle B"}
    assert stand["quellen"]["Quelle A"]["anzahl"] == 2
    quellen = {t["quelle"] for termine in stand["monate"].values() for t in termine}
    assert "manuell" not in quellen
    # Rohdaten vor Dublettenprüfung: beide „Offene Schmiede“ stehen im Stand
    assert sum(t["name"] == "Offene Schmiede" for t in stand["monate"]["2026-10"]) == 2


def test_stand_roundtrip_ohne_erneute_bereinigung(capsys):
    t = Termin(name="Konzert", datum=datetime(2026, 10, 23, 19, 30), uhrzeit="19:30 Uhr", ort="Ort",
               link="", quelle="x", beschreibung="Der Termin entfällt.")
    assert t.abgesagt
    capsys.readouterr()
    zurueck = app._termin_aus_dict(app._termin_zu_dict(t))
    assert zurueck == t
    assert capsys.readouterr().out == ""  # keine zweite Meldung „[Absage erkannt]“


def test_nur_bauen_liefert_dieselben_seiten(umgebung, monkeypatch):
    stand_pfad = umgebung / "stand.json"
    _lauf(monkeypatch, "--ausgabe", str(umgebung / "kombiniert"), "--stand", str(stand_pfad))
    stand_vorher = stand_pfad.read_text(encoding="utf-8")
    _verbiete_abruf(monkeypatch)
    _lauf(monkeypatch, "--nur-bauen", "--ausgabe", str(umgebung / "gebaut"), "--stand", str(stand_pfad))
    kombiniert = _seiten(umgebung / "kombiniert")
    assert set(kombiniert) == {"termine_re_2026_10.html", "termine_re_2026_11.html", "index.html", "sitemap.xml"}
    assert _seiten(umgebung / "gebaut") == kombiniert
    assert "Hebbert-Fest" in kombiniert["termine_re_2026_10.html"]
    assert stand_pfad.read_text(encoding="utf-8") == stand_vorher  # nur bauen ändert den Stand nicht


def test_neue_absage_wirkt_beim_nur_bauen(umgebung, monkeypatch):
    stand_pfad = umgebung / "stand.json"
    _lauf(monkeypatch, "--ausgabe", str(umgebung / "site"), "--stand", str(stand_pfad))
    seite = (umgebung / "site" / "termine_re_2026_10.html").read_text(encoding="utf-8")
    assert 'data-abgesagt="1"' not in seite

    (umgebung / "korrekturen.json").write_text(json.dumps([{
        "datum": "2026-10-24", "name": "Lesung Müller", "name_norm": "lesung müller",
        "quelle": "stadtbibliothek", "aenderung": {}, "absage": True, "hw_mail": "kalender:x",
        "freigegeben": True, "angelegt": "2026-10-14"}]), encoding="utf-8")
    _verbiete_abruf(monkeypatch)
    _lauf(monkeypatch, "--nur-bauen", "--ausgabe", str(umgebung / "site"), "--stand", str(stand_pfad))
    seite = (umgebung / "site" / "termine_re_2026_10.html").read_text(encoding="utf-8")
    assert seite.count('data-abgesagt="1"') == 1
    assert "Abgesagt" in seite


def test_neuer_handeintrag_wirkt_beim_nur_bauen(umgebung, monkeypatch):
    stand_pfad = umgebung / "stand.json"
    _lauf(monkeypatch, "--ausgabe", str(umgebung / "site"), "--stand", str(stand_pfad))

    def mit_neuem_eintrag(jahr, monat):
        neu = [Termin(name="Neuer Handeintrag", datum=datetime(2026, 10, 26, 18), uhrzeit="18:00 Uhr",
                      ort="Holzwurm", link="", quelle="manuell")] if (jahr, monat) == (2026, 10) else []
        return _manuell(jahr, monat) + neu
    monkeypatch.setattr(app, "hole_manuelle_termine", mit_neuem_eintrag)
    _verbiete_abruf(monkeypatch)
    _lauf(monkeypatch, "--nur-bauen", "--ausgabe", str(umgebung / "site"), "--stand", str(stand_pfad))
    assert "Neuer Handeintrag" in (umgebung / "site" / "termine_re_2026_10.html").read_text(encoding="utf-8")


def _schreibe_stand(pfad, abgerufen, monate=("2026-10", "2026-11")):
    pfad.write_text(json.dumps({"format": 1, "abgerufen": abgerufen.isoformat(timespec="seconds"),
                                "quellen": {}, "monate": {m: [] for m in monate}}), encoding="utf-8")


def test_nur_bauen_ohne_stand_bricht_ab(umgebung, monkeypatch, capsys):
    _verbiete_abruf(monkeypatch)
    with pytest.raises(SystemExit) as e:
        _lauf(monkeypatch, "--nur-bauen", "--ausgabe", str(umgebung / "site"), "--stand", str(umgebung / "fehlt.json"))
    assert e.value.code not in (0, None)
    assert "fehlt" in capsys.readouterr().err
    assert not (umgebung / "site").exists()


def test_nur_bauen_mit_kaputtem_stand_bricht_ab(umgebung, monkeypatch, capsys):
    stand_pfad = umgebung / "stand.json"
    stand_pfad.write_text("{kaputt", encoding="utf-8")
    _verbiete_abruf(monkeypatch)
    with pytest.raises(SystemExit) as e:
        _lauf(monkeypatch, "--nur-bauen", "--ausgabe", str(umgebung / "site"), "--stand", str(stand_pfad))
    assert e.value.code not in (0, None)
    assert "nicht lesbar" in capsys.readouterr().err


def test_nur_bauen_mit_altem_stand_bricht_ab(umgebung, monkeypatch, capsys):
    stand_pfad = umgebung / "stand.json"
    _schreibe_stand(stand_pfad, datetime.now() - timedelta(hours=37))
    _verbiete_abruf(monkeypatch)
    with pytest.raises(SystemExit) as e:
        _lauf(monkeypatch, "--nur-bauen", "--ausgabe", str(umgebung / "site"), "--stand", str(stand_pfad))
    assert e.value.code not in (0, None)
    assert "älter als 36 Stunden" in capsys.readouterr().err
    assert not (umgebung / "site").exists()


def test_nur_bauen_mit_stand_knapp_unter_grenze(umgebung, monkeypatch):
    stand_pfad = umgebung / "stand.json"
    _schreibe_stand(stand_pfad, datetime.now() - timedelta(hours=35))
    _verbiete_abruf(monkeypatch)
    _lauf(monkeypatch, "--nur-bauen", "--ausgabe", str(umgebung / "site"), "--stand", str(stand_pfad))
    assert (umgebung / "site" / "termine_re_2026_11.html").exists()


def test_nur_bauen_mit_fehlendem_monat_bricht_ab(umgebung, monkeypatch, capsys):
    """Monatswechsel: Der Stand von gestern deckt den neuen letzten Monat nicht ab."""
    stand_pfad = umgebung / "stand.json"
    _schreibe_stand(stand_pfad, datetime.now() - timedelta(hours=1), monate=("2026-10",))
    _verbiete_abruf(monkeypatch)
    with pytest.raises(SystemExit) as e:
        _lauf(monkeypatch, "--nur-bauen", "--ausgabe", str(umgebung / "site"), "--stand", str(stand_pfad))
    assert e.value.code not in (0, None)
    assert "2026-11" in capsys.readouterr().err
