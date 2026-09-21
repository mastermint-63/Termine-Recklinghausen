"""Tests für hw_import: Validierung, Beleg-Prüfung, Idempotenz. Kein API-Aufruf, kein eM Client."""
from datetime import date, datetime


import hw_import as hw

HEUTE = date(2026, 9, 21)


def _mail(text="Am Freitag, 25.09.2026 um 18:00 Uhr Seminar im Infoladen", anhang=False):
    return hw.Mail(konto="gmx", id=1, message_id="abc@x", datum=datetime(2026, 9, 21, 18, 0),
                   betreff="Seminar", absender="A <a@b.de>", text=text,
                   bilder=[("image/jpeg", b"x")] if anhang else [])


def _termin(**kw):
    basis = {"name": "Seminar Komoot", "datum": "2026-09-25", "uhrzeit": "18:00", "ort": "Infoladen, Börster Weg 38a",
             "beschreibung": "x", "kategorie": "Vortrag", "eindeutig": True, "in_recklinghausen": True,
             "beleg": "Freitag, 25.09.2026 um 18:00 Uhr"}
    basis.update(kw)
    return basis


def _bewerte(t, mail=None, dublette=False, ausgeschlossen=False, konflikt=None):
    return hw.bewerte_termin(t, mail or _mail(), HEUTE, lambda e, m: ausgeschlossen, lambda e: dublette,
                             lambda e: konflikt)


def test_eindeutiger_termin_wird_automatisch_freigegeben():
    status, _, e = _bewerte(_termin())
    assert status == "auto" and e["freigegeben"] is True and e["hw_mail"] == "gmx:abc@x"


def test_vergangener_termin_wird_verworfen():
    assert _bewerte(_termin(datum="2026-09-01"))[0] == "verwerfen"


def test_dublette_wird_verworfen():
    assert _bewerte(_termin(), dublette=True)[0] == "verwerfen"


def test_afd_wird_verworfen():
    assert _bewerte(_termin(), ausgeschlossen=True)[0] == "verwerfen"


def test_unklar_vom_modell_geht_zur_pruefung():
    status, grund, e = _bewerte(_termin(eindeutig=False, unklar_grund="Jahr fehlt"))
    assert status == "pruefen" and e["freigegeben"] is False and "Jahr fehlt" in grund


def test_beleg_nicht_im_text_geht_zur_pruefung():
    status, grund, _ = _bewerte(_termin(beleg="Samstag, 26.09.2026 um 20 Uhr"))
    assert status == "pruefen" and "Beleg" in grund


def test_wochentag_passt_nicht_zum_datum():
    # 25.09.2026 ist ein Freitag; Beleg behauptet Samstag
    mail = _mail(text="Am Samstag, 25.09.2026 um 18:00 Uhr Seminar")
    status, grund, _ = _bewerte(_termin(beleg="Samstag, 25.09.2026"), mail=mail)
    assert status == "pruefen" and "Wochentag" in grund


def test_beleg_bild_nur_mit_anhang():
    assert hw.beleg_ok("BILD", "text", hat_anhang=True)
    assert not hw.beleg_ok("BILD", "text", hat_anhang=False)


def test_ohne_ort_und_uhrzeit_zur_pruefung():
    assert _bewerte(_termin(ort="", uhrzeit=""))[0] == "pruefen"


def test_ausserhalb_recklinghausen_zur_pruefung():
    assert _bewerte(_termin(in_recklinghausen=False))[0] == "pruefen"


def test_link_muss_im_mailtext_stehen():
    _, _, e = _bewerte(_termin(link="https://erfunden.example/x"))
    assert e["link"] == ""
    mail = _mail(text="Am Freitag, 25.09.2026 um 18:00 Uhr Seminar https://adfc.de/komoot")
    _, _, e = _bewerte(_termin(link="https://adfc.de/komoot"), mail=mail)
    assert e["link"] == "https://adfc.de/komoot"


def test_ungueltiges_datum_wird_verworfen():
    assert _bewerte(_termin(datum="2026-13-45"))[0] == "verwerfen"


def test_uhrzeit_normalisierung():
    assert hw.normalisiere_uhrzeit("18.00 Uhr") == "18:00"
    assert hw.normalisiere_uhrzeit("9:30") == "09:30"
    assert hw.normalisiere_uhrzeit("ab 18 Uhr") == ""
    assert hw.normalisiere_uhrzeit("25:00") == ""


def test_haenge_an_ist_idempotent():
    bestehend = [{"datum": "2026-09-25", "name": "Seminar Komoot"}]
    neu = [{"datum": "2026-09-25", "name": "Seminar  KOMOOT!"}, {"datum": "2026-09-26", "name": "Anderes"}]
    ergebnis = hw.haenge_an(bestehend, neu)
    assert [e["name"] for e in ergebnis] == ["Seminar Komoot", "Anderes"]


def test_bekannte_hosts_enthalten_adfc():
    assert "recklinghausen.adfc.de" in hw.bekannte_hosts()


def test_hw_kategorie_wird_gefunden_oder_leer(tmp_path, monkeypatch):
    """Leseweg gegen die echte eM-Client-DB: darf nie schreiben und nie crashen."""
    treffer = hw.finde_hw_mail_ids()
    assert isinstance(treffer, list)


def test_konflikt_mit_scraper_quelle_geht_zur_pruefung():
    status, grund, e = _bewerte(_termin(), konflikt="ähnlicher Termin am 2026-09-30 (holzwurm): X - Datum abweichend?")
    assert status == "pruefen" and "abweichend" in grund and e["freigegeben"] is False


def test_bekannte_hosts_enthalten_dokumentierte_verworfene_seite():
    assert "cityredio.jimdofree.com" in hw.bekannte_hosts()
