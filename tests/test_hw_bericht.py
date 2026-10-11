"""Tests für den Signal-Bericht nach dem Push (hw_bericht.py). Kein Versand."""
import json

import hw_bericht as hb


def _bericht(**kw):
    b = {"erstellt": "2026-10-12T00:30:05", "mails": 2, "eingetragen": [], "geaendert": [], "abgesagt": [],
         "pruefen": [], "neue_seiten": [], "quellfehler": [], "verwaist": [], "ohne_ergebnis": [], "fehler": []}
    b.update(kw)
    return b


def test_kein_text_wenn_nichts_passiert_ist():
    assert hb.baue_nachricht(_bericht(), "live") is None


def test_text_mit_allen_teilen():
    text = hb.baue_nachricht(_bericht(
        eingetragen=[{"datum": "2026-10-23", "name": "Lesung Müller"}],
        geaendert=[{"datum": "2026-10-24", "name": "Offene Schmiede", "was": "uhrzeit 14:00"}],
        abgesagt=[{"datum": "2026-10-25", "name": "Konzert"}],
        pruefen=[{"datum": "2026-10-26", "name": "Vortrag", "grund": "Beleg-Zitat nicht im Mailtext gefunden"}],
        neue_seiten=["verein.example (JSON-LD mit 3 Event(s))"],
        quellfehler=["Quelle nlgr liefert vermutlich falsche Daten (Konzert, 2026-10-25), Scraper prüfen."],
        verwaist=[{"datum": "2026-10-27", "name": "Weg"}],
        fehler=["Kalender-Eingang: IMAP-Login abgelehnt"]), "live")
    assert text.startswith("Holzwurm-Import 12.10.")
    assert "Ist live." in text
    assert "Eingetragen (1):\n- 23.10. Lesung Müller" in text
    assert "- 24.10. Offene Schmiede: uhrzeit 14:00" in text
    assert "Abgesagt (1):\n- 25.10. Konzert" in text
    assert "Zur Prüfung (1), hw_pruefliste.md:" in text
    assert "Scraper prüfen" in text and "verein.example" in text and "IMAP-Login abgelehnt" in text
    assert "Korrektur greift nicht mehr" in text


def test_hinweis_wenn_push_fehlgeschlagen():
    text = hb.baue_nachricht(_bericht(eingetragen=[{"datum": "2026-10-23", "name": "Lesung"}]),
                             "fehler", "Push fehlgeschlagen!")
    assert "NICHT live" in text and "Push fehlgeschlagen" in text


def test_unveraendert_ohne_live_zeile():
    text = hb.baue_nachricht(_bericht(pruefen=[{"datum": "2026-10-26", "name": "Vortrag", "grund": "x"}]),
                             "unveraendert")
    assert "Ist live." not in text and "NICHT live" not in text


def test_titel_werden_bereinigt_und_gekuerzt():
    name = "Lesung‮\x07 – mit sehr langem Titel " + "x" * 200
    text = hb.baue_nachricht(_bericht(eingetragen=[{"datum": "2026-10-23", "name": name}]), "live")
    zeile = [z for z in text.splitlines() if z.startswith("- 23.10.")][0]
    assert "‮" not in zeile and "\x07" not in zeile and "–" not in zeile
    assert len(zeile) <= 90


def test_lange_listen_werden_gekappt():
    viele = [{"datum": "2026-10-23", "name": f"Termin {i}"} for i in range(30)]
    text = hb.baue_nachricht(_bericht(eingetragen=viele), "live")
    assert "... und 20 weitere" in text


def test_main_sendet_einmal_und_markiert(tmp_path, monkeypatch):
    pfad = tmp_path / "hw_bericht.json"
    pfad.write_text(json.dumps(_bericht(eingetragen=[{"datum": "2026-10-23", "name": "Lesung"}])), encoding="utf-8")
    gesendet = []
    monkeypatch.setattr(hb, "sende_signal", lambda text: gesendet.append(text) or True)
    assert hb.main(["--status", "live", "--pfad", str(pfad)]) == 0
    assert hb.main(["--status", "live", "--pfad", str(pfad)]) == 0
    assert len(gesendet) == 1
    assert "gesendet" in json.loads(pfad.read_text(encoding="utf-8"))


def test_main_ohne_bericht_ist_kein_fehler(tmp_path):
    assert hb.main(["--status", "live", "--pfad", str(tmp_path / "fehlt.json")]) == 0


def test_main_versandfehler_markiert_nicht(tmp_path, monkeypatch):
    pfad = tmp_path / "hw_bericht.json"
    pfad.write_text(json.dumps(_bericht(eingetragen=[{"datum": "2026-10-23", "name": "Lesung"}])), encoding="utf-8")
    monkeypatch.setattr(hb, "sende_signal", lambda text: False)
    assert hb.main(["--status", "live", "--pfad", str(pfad)]) == 1
    assert "gesendet" not in json.loads(pfad.read_text(encoding="utf-8"))


def test_mail_ohne_ergebnis_wird_gemeldet():
    text = hb.baue_nachricht(_bericht(ohne_ergebnis=["Stammtisch fällt aus"]), "unveraendert")
    assert "Ohne Ergebnis, Mail von Hand ansehen (1):\n- Stammtisch fällt aus" in text


def test_nicht_uebernommene_werden_gemeldet():
    text = hb.baue_nachricht(_bericht(verworfen=[{"datum": "2026-10-10", "name": "SkF-Infostand",
                                                  "grund": "Termin liegt in der Vergangenheit"}]), "unveraendert")
    assert "Nicht übernommen (1):\n- 10.10. SkF-Infostand (Termin liegt in der Vergangenheit)" in text
