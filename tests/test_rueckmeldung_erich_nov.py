"""Befunde aus Erichs Mails vom 03./04.11.2026 ("Er versteht mich nicht"):

1. Rückmeldung: Ohne Leerzeile zieht sein Mailprogramm "Nicht übernommen:" an die Zeile davor, 007 las sich wie abgelehnt.
2. Mail ohne Termin (Frage, nur ein Link) blieb ohne jede Antwort.
3. "Afrika & Europa - ... ihre Musik" wurde als Dublette von "The Glams, Live-Musik ..." verworfen, nur wegen "Musik".
4. Weihnachtscircus: Uhrzeit und Zeitraum aus der Mail gingen als "steht schon im Kalender" verloren.
5. PDF nur aus einem Bild: Beide Modelle wollten einen Befehl ausführen, agy verweigerte, Ergebnis leere Antwort.
"""
import json
from datetime import date, datetime

import fitz
import pytest

import app
import hw_bericht as hb
import hw_import as hw
import rueckmeldung as rm
from scraper import Termin

HEUTE = date(2026, 11, 5)
TAG = datetime(2026, 11, 8)
AFRIKA = "Afrika & Europa – zwei Kontinente und ihre Musik"
GLAMS = "„The Glams“, Live-Musik mit Verena und Meike"
CIRCUS = "1. Recklinghäuser Weihnachtscircus"


def _mail(text="Der Circus läuft täglich", **kw):
    return hw.Mail(konto="kalender", id=1, message_id="m1@x", datum=datetime(2026, 11, 4, 8, 17), betreff="Kalender",
                   absender="E <e@x.example>", text=text, vertrauen="vertraut", **kw)


def _termin(**kw):
    t = {"name": CIRCUS, "datum": "2026-12-17", "bis": "2027-01-03", "uhrzeit": "15:30", "ort": "Rathausplatz",
         "eindeutig": True, "in_recklinghausen": True, "beleg": "täglich", "kategorie": "Familie",
         "beschreibung": "Täglich 15:30 und 19:30 Uhr, am 24.12. nur 15:30 Uhr, bis zum 03.01. Karten online."}
    t.update(kw)
    return t


def _termin_obj(name, uhrzeit, quelle):
    return Termin(name=name, datum=TAG, uhrzeit=uhrzeit, ort="", link="", quelle=quelle)


def _alt(**kw):
    e = {"name": CIRCUS, "datum": "2026-12-17", "uhrzeit": "", "ort": "Rathausplatz Recklinghausen", "link": "",
         "beschreibung": "Weihnachtscircus auf dem Rathausplatz.", "kategorie": "Familie", "freigegeben": True}
    e.update(kw)
    return e


# --------------------------------------------------------------------------- 1. Leerzeilen

def test_abschnitte_haben_leerzeile_davor():
    text = rm.baue_text([{"eingetragen": [{"datum": "2026-11-07", "name": "007-Melodien"}],
                          "verworfen": [{"datum": "2026-12-17", "name": "Circus", "grund": "steht schon im Kalender"}]}])
    assert "- Sa 07.11. 007-Melodien\n\nNicht übernommen:\n" in text
    assert "\n\n\n" not in text


# --------------------------------------------------------------------------- 2. Mail ohne Termin

def test_frage_ohne_termin_bekommt_antwort(monkeypatch):
    monkeypatch.setattr(hw, "analysiere", lambda c, m, h: {"termine": [], "aenderungen": [], "terminseiten": []})
    mail = _mail("Hast Du was gegen den Weihnachtsmarkt in Recklinghausen?")
    res = hw.verarbeite_mail(None, mail, HEUTE, True, [], [], hw.neuer_bericht())
    inhalt = hw.rueckmeldung_inhalt(res["bericht"])
    assert inhalt["nichts_erkannt"] == [{"auszug": "Hast Du was gegen den Weihnachtsmarkt in Recklinghausen?"}]
    text = rm.baue_text([inhalt])
    assert "Kein Termin erkannt:\n- Hast Du was gegen den Weihnachtsmarkt" in text
    assert "Fragen" in text and "Datum" in text


def test_nur_ein_link_nennt_die_seite(monkeypatch):
    url = "https://ratskeller-recklinghausen.ticket.io/"
    monkeypatch.setattr(hw, "analysiere", lambda c, m, h: {"termine": [], "aenderungen": [],
                                                           "terminseiten": [{"url": url}]})
    monkeypatch.setattr(hw, "melde_neue_seiten", lambda s, m, d: [])
    res = hw.verarbeite_mail(None, _mail(url), HEUTE, True, [], [], hw.neuer_bericht())
    inhalt = hw.rueckmeldung_inhalt(res["bericht"])
    assert inhalt["seiten"] == [{"host": "ratskeller-recklinghausen.ticket.io"}]
    assert "- ratskeller-recklinghausen.ticket.io" in rm.baue_text([inhalt])


def test_erfundene_seite_steht_nicht_in_der_antwort(monkeypatch):
    monkeypatch.setattr(hw, "analysiere", lambda c, m, h: {"termine": [], "aenderungen": [],
                                                           "terminseiten": [{"url": "https://boese.example/"}]})
    monkeypatch.setattr(hw, "melde_neue_seiten", lambda s, m, d: [])
    res = hw.verarbeite_mail(None, _mail("kein Link hier"), HEUTE, True, [], [], hw.neuer_bericht())
    assert not res["bericht"]["seiten"]


def test_presse_mail_ohne_termin_bleibt_ohne_antwort(monkeypatch):
    monkeypatch.setattr(hw, "analysiere", lambda c, m, h: {"termine": [], "aenderungen": [], "terminseiten": []})
    mail = hw.Mail(konto="gmx", id=1, message_id="m@x", datum=datetime(2026, 11, 4), betreff="PM", absender="a@b.example",
                   text="Pressemitteilung", vertrauen="vertraut")
    res = hw.verarbeite_mail(None, mail, HEUTE, True, [], [], hw.neuer_bericht())
    assert hw.rueckmeldung_inhalt(res["bericht"]) is None


# --------------------------------------------------------------------------- 3. falsche Dubletten

def _dedup(*termine):
    return [t.name for t in app.entferne_duplikate(list(termine))]


def test_musik_allein_ist_keine_dublette():
    assert len(_dedup(_termin_obj(AFRIKA, "16:00 Uhr", "manuell"), _termin_obj(GLAMS, "15:00 Uhr", "stadt-re"))) == 2


def test_manuell_nur_schluesselwort_andere_uhrzeit_bleibt_getrennt():
    t = _dedup(_termin_obj("Abendmusik Trompetenklang", "19:00 Uhr", "manuell"),
               _termin_obj("Trompetenklang im Advent", "18:00 Uhr", "stadt-re"))
    assert len(t) == 2


def test_manuell_nur_schluesselwort_gleiche_uhrzeit_bleibt_dublette():
    t = _dedup(_termin_obj("Abendmusik Trompetenklang", "19.00 Uhr", "manuell"),
               _termin_obj("Trompetenklang im Advent", "19:00 Uhr", "stadt-re"))
    assert len(t) == 1


def test_manuell_ohne_uhrzeit_bleibt_dublette():
    t = _dedup(_termin_obj("Abendmusik Trompetenklang", "siehe Website", "manuell"),
               _termin_obj("Trompetenklang im Advent", "19:00 Uhr", "stadt-re"))
    assert len(t) == 1


def test_scraper_untereinander_unveraendert():
    t = _dedup(_termin_obj("Abendmusik Trompetenklang", "19:00 Uhr", "nlgr"),
               _termin_obj("Trompetenklang im Advent", "18:00 Uhr", "stadt-re"))
    assert len(t) == 1


def test_gleicher_titel_andere_uhrzeit_bleibt_dublette():
    assert len(_dedup(_termin_obj("Drohnenshow am Rathaus", "20:00 Uhr", "manuell"),
                      _termin_obj("Drohnenshow am Rathaus", "21:00 Uhr", "stadt-re"))) == 1


def _eintrag(name, uhrzeit):
    return {"name": name, "datum": "2026-11-08", "uhrzeit": uhrzeit, "ort": "", "link": "", "beschreibung": "",
            "kategorie": "Konzert"}


def test_import_traegt_aehnlichen_termin_mit_warnung_ein(monkeypatch):
    monkeypatch.setattr(hw, "lade_bestehende", lambda d: [_termin_obj("Trompetenklang im Advent", "18:00 Uhr", "stadt-re")])
    monkeypatch.setattr(hw, "lade_json", lambda: [])
    e = _eintrag("Abendmusik Trompetenklang", "19:00")
    assert hw.ist_dublette_im_kalender(e) is None
    assert e["_aehnlich"] == "Trompetenklang im Advent, 18:00 Uhr"


def test_warnung_landet_am_eintrag_nicht_als_feld():
    def dublette(e):
        e["_aehnlich"] = "Trompetenklang im Advent, 18:00 Uhr"
        return None

    t = _termin(name="Abendmusik Trompetenklang", datum="2026-11-08", bis="", beleg="täglich")
    status, _grund, e = hw.bewerte_termin(t, _mail(), HEUTE, lambda e, m: False, dublette, lambda e: None)
    assert status == "auto" and "_aehnlich" not in e
    assert "ähnlicher Termin im Kalender: Trompetenklang im Advent, 18:00 Uhr" in e["hw_warnung"]


# --------------------------------------------------------------------------- 4. Ergänzen statt verwerfen

def _verarbeite(monkeypatch, eintraege, mail=None, **kw):
    monkeypatch.setattr(hw, "ist_dublette_im_kalender", lambda e: _termin_obj(CIRCUS, "siehe Website", "manuell"))
    monkeypatch.setattr(hw, "finde_konflikt", lambda e: None)
    monkeypatch.setattr(hw, "analysiere", lambda c, m, h: {"termine": [_termin(**kw)]})
    bericht = hw.neuer_bericht()
    return hw.verarbeite_mail(None, mail or _mail(), HEUTE, True, eintraege, [], bericht), bericht


def test_dublette_mit_neuer_uhrzeit_ergaenzt_den_eintrag(monkeypatch):
    eintraege = [_alt()]
    res, gesamt = _verarbeite(monkeypatch, eintraege)
    e = eintraege[0]
    assert len(eintraege) == 1 and e["uhrzeit"] == "15:30" and "19:30" in e["beschreibung"]
    assert e["ort"] == "Rathausplatz Recklinghausen"  # vorhandener Ort bleibt
    assert {x["feld"] for x in e["hw_aenderungen"]} == {"uhrzeit", "beschreibung"}
    assert not res["bericht"]["verworfen"]
    assert res["bericht"]["ergaenzt"] == [{"datum": "2026-12-17", "name": CIRCUS, "was": "uhrzeit, beschreibung"}]
    assert gesamt["ergaenzt"] == res["bericht"]["ergaenzt"]
    text = rm.baue_text([hw.rueckmeldung_inhalt(res["bericht"])])
    assert "Ergänzt:\n- Do 17.12. 1. Recklinghäuser Weihnachtscircus: Uhrzeit, Beschreibung" in text


def test_wiederholung_ergaenzt_nichts_mehr(monkeypatch):
    eintraege = [_alt()]
    _verarbeite(monkeypatch, eintraege)
    res, _ = _verarbeite(monkeypatch, eintraege)
    assert not res["bericht"]["ergaenzt"]
    assert res["bericht"]["verworfen"][0]["grund"] == "steht schon im Kalender"


def test_vorhandene_uhrzeit_wird_nicht_ueberschrieben(monkeypatch):
    eintraege = [_alt(uhrzeit="11:00")]
    _verarbeite(monkeypatch, eintraege)
    assert eintraege[0]["uhrzeit"] == "11:00"


def test_link_nur_wenn_er_in_der_mail_steht(monkeypatch):
    eintraege = [_alt()]
    _verarbeite(monkeypatch, eintraege, link="https://erfunden.example/")
    assert eintraege[0]["link"] == ""
    eintraege = [_alt()]
    _verarbeite(monkeypatch, eintraege, mail=_mail("Karten: https://circus.example/"), link="https://circus.example/")
    assert eintraege[0]["link"] == "https://circus.example/"


def test_nicht_vertrauter_absender_ergaenzt_nicht(monkeypatch):
    eintraege = [_alt()]
    mail = _mail()
    mail.vertrauen = "unbekannt"
    res, _ = _verarbeite(monkeypatch, eintraege, mail=mail)
    assert eintraege[0]["uhrzeit"] == "" and not res["bericht"]["ergaenzt"]


def test_mehrere_passende_eintraege_ergaenzen_nicht(monkeypatch):
    eintraege = [_alt(), _alt(name=CIRCUS + " Nachmittag")]
    res, _ = _verarbeite(monkeypatch, eintraege)
    assert eintraege[0]["uhrzeit"] == "" and not res["bericht"]["ergaenzt"]


def test_signal_bericht_nennt_ergaenzung():
    bericht = hw.neuer_bericht()
    bericht["ergaenzt"] = [{"datum": "2026-12-17", "name": CIRCUS, "was": "uhrzeit"}]
    text = hb.baue_nachricht(bericht, "live")
    assert "Ergänzt" in text and "Weihnachtscircus" in text


# --------------------------------------------------------------------------- 5. PDFs und leere agy-Antworten

def _pdf(text=""):
    doc = fitz.open()
    seite = doc.new_page()
    if text:
        seite.insert_text((72, 72), text)
    else:
        seite.draw_rect(fitz.Rect(50, 50, 200, 200), fill=(0.8, 0.2, 0.2))
    return doc.tobytes()


def _analysiere(pdfs, bilder=()):
    gesehen = {}

    def runner(prompt, schema, modell, b, p):
        gesehen.update(prompt=prompt, bilder=b, pdfs=p)
        return {"termine": [], "aenderungen": [], "terminseiten": []}

    hw.analysiere(runner, _mail(pdfs=pdfs, bilder=list(bilder)), HEUTE)
    return gesehen


def test_bild_pdf_geht_als_bild_ans_modell():
    g = _analysiere([_pdf()])
    assert g["pdfs"] == [] and len(g["bilder"]) == 1
    assert g["bilder"][0][0] == "image/jpeg" and g["bilder"][0][1][:2] == b"\xff\xd8"


def test_text_pdf_geht_als_text_ans_modell():
    g = _analysiere([_pdf("Konzert am 8. November")])
    assert g["pdfs"] == [] and g["bilder"] == [] and "Konzert am 8. November" in g["prompt"]


def test_bild_pdf_haelt_die_bildgrenze_ein():
    vorhanden = [("image/jpeg", b"x")] * hw.MAX_BILDER
    assert len(_analysiere([_pdf()], vorhanden)["bilder"]) == hw.MAX_BILDER


def test_kaputtes_pdf_bricht_nicht_ab():
    assert _analysiere([b"kein pdf"])["bilder"] == []


class _Proc:
    returncode = 0
    stderr = ""

    def __init__(self, payload):
        self.stdout = json.dumps(payload)


def _agy(monkeypatch, payload):
    aufrufe = []

    def run(cmd, **kw):
        aufrufe.append(cmd)
        return _Proc(payload)

    monkeypatch.setattr(hw.subprocess, "run", run)
    monkeypatch.setattr(hw, "_agy_home", lambda: "/tmp")
    return aufrufe


def test_verweigerter_befehl_steht_in_der_fehlermeldung(monkeypatch):
    _agy(monkeypatch, {"status": "SUCCESS", "response": "",
                       "denied_actions": [{"action": "command", "display_name": "RunCommand"}]})
    with pytest.raises(RuntimeError, match="RunCommand"):
        hw._run_agy_hw("p", {}, "m", [], [])


def test_leere_antwort_ohne_verweigerung_hat_klare_meldung(monkeypatch):
    _agy(monkeypatch, {"status": "SUCCESS", "response": ""})
    with pytest.raises(RuntimeError, match="keine Antwort"):
        hw._run_agy_hw("p", {}, "m", [], [])


def test_prompt_verbietet_befehle_auch_ohne_anhang(monkeypatch):
    aufrufe = _agy(monkeypatch, {"status": "SUCCESS", "response": "{}"})
    hw._run_agy_hw("p", {}, "m", [], [])
    prompt = next(a for a in aufrufe[0] if a.startswith("--print="))
    assert "keine Befehle" in prompt and "keine Links" in prompt
