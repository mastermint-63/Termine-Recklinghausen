"""Redaktion direkt (Entscheidung FS, 13.10.2026): Mails vertrauter Redaktionsmitglieder an den Kalender-Eingang
werden ohne Prüfliste umgesetzt. Verworfen wird nur, was vergangen ist, schon im Kalender steht oder ausgeschlossen
ist. Anzeichen für einen Modellfehler (Beleg, Wochentag) werden eingetragen, aber im Bericht markiert."""
from datetime import date, datetime

import hw_bericht
import hw_import as hw
from scraper import Termin

HEUTE = date(2026, 10, 11)
TAG = date(2026, 10, 23)  # Freitag


def _mail(text="Am Freitag, 23.10.2026 um 19:00 Uhr Lesung im Altstadtcafé", vertrauen="vertraut", konto="kalender"):
    return hw.Mail(konto=konto, id=1, message_id="m1@x", datum=datetime(2026, 10, 11, 10, 0), betreff="Termin",
                   absender="R <r@x.example>", text=text, vertrauen=vertrauen,
                   vertrauen_grund="" if vertrauen == "vertraut" else "Absender nicht authentifiziert")


def _termin(**kw):
    t = {"name": "Lesung", "datum": "2026-10-23", "uhrzeit": "19:00", "ort": "Altstadtcafé", "eindeutig": True,
         "in_recklinghausen": True, "beleg": "Freitag, 23.10.2026 um 19:00 Uhr", "kategorie": "Lesung"}
    t.update(kw)
    return t


def _bewerte(t, mail=None, dublette=False, ausgeschlossen=False, konflikt=None):
    return hw.bewerte_termin(t, mail or _mail(), HEUTE, lambda e, m: ausgeschlossen, lambda e: dublette,
                             lambda e: konflikt)


# --------------------------------------------------------------------------- neue Termine

def test_redaktion_direkt_nur_kalender_und_vertraut():
    assert hw.ist_redaktion_direkt(_mail())
    assert not hw.ist_redaktion_direkt(_mail(vertrauen="redaktion_unauth"))
    assert not hw.ist_redaktion_direkt(_mail(vertrauen="unbekannt"))
    assert not hw.ist_redaktion_direkt(_mail(konto="gmx"))
    presse = _mail()
    presse.presse_auto = True
    assert not hw.ist_redaktion_direkt(presse)


def test_weiche_zweifel_werden_uebergangen():
    for t, konflikt in [(_termin(eindeutig=False, unklar_grund="Jahr fehlt"), None),
                        (_termin(in_recklinghausen=False), None),
                        (_termin(ort="", uhrzeit=""), None),
                        (_termin(datum="2027-12-03", beleg="3.12.2027"), None),
                        (_termin(), "ähnlicher Termin am 2026-10-30 (nlgr): Lesung - Datum abweichend?")]:
        mail = _mail(t["beleg"])
        status, _, e = _bewerte(t, mail=mail, konflikt=konflikt)
        assert status == "auto" and e["freigegeben"] is True and "hw_warnung" not in e, t


def test_beleg_fehlt_wird_eingetragen_und_markiert():
    status, _, e = _bewerte(_termin(beleg="Samstag, 24.10.2026"))
    assert status == "auto" and e["freigegeben"] is True and "Beleg" in e["hw_warnung"]


def test_wochentag_falsch_wird_eingetragen_und_markiert():
    mail = _mail("Am Samstag, 23.10.2026 um 19:00 Uhr Lesung")
    status, _, e = _bewerte(_termin(beleg="Samstag, 23.10.2026"), mail=mail)
    assert status == "auto" and "Wochentag" in e["hw_warnung"]


def test_harte_gruende_verwerfen_weiter():
    assert _bewerte(_termin(datum="2026-10-01"))[0] == "verwerfen"
    assert _bewerte(_termin(), dublette=True)[0] == "verwerfen"
    assert _bewerte(_termin(), ausgeschlossen=True)[0] == "verwerfen"


def test_nicht_authentifizierte_redaktion_bleibt_pruefung():
    status, _, e = _bewerte(_termin(eindeutig=False), mail=_mail(vertrauen="redaktion_unauth"))
    assert status == "pruefen" and e["freigegeben"] is False


def test_andere_konten_bleiben_wie_bisher():
    status, _, _ = _bewerte(_termin(eindeutig=False), mail=_mail(konto="gmx"))
    assert status == "pruefen"


# --------------------------------------------------------------------------- Korrekturen, Absagen, Verschiebungen

def _seite(*termine):
    def bestehende(d):
        return [Termin(name=n, datum=datetime.combine(d, datetime.min.time()), uhrzeit=u, ort=o, link="",
                       quelle=q) for (n, q, u, o) in termine] if d == TAG else []
    return bestehende


SCHMIEDE = ("Offene Schmiede", "altstadtschmiede", "10:00 Uhr", "Altstadtschmiede, Kirchplatz 1")


def _aend(**kw):
    a = {"art": "absage", "bezug_name": "Offene Schmiede", "bezug_datum": "2026-10-23", "neu_datum": "",
         "neu_uhrzeit": "", "neu_ort": "", "beleg": "Offene Schmiede am Freitag, 23.10.2026 fällt aus",
         "eindeutig": True, "unklar_grund": "", "quellfehler": False}
    a.update(kw)
    return a


def _bewerte_a(a, mail=None, eintraege=None, seite=None):
    return hw.bewerte_aenderung(a, mail or _mail("Die Offene Schmiede am Freitag, 23.10.2026 fällt aus."), HEUTE,
                                eintraege if eintraege is not None else [], seite or _seite(SCHMIEDE))


def test_absage_unklar_wird_trotzdem_ausgefuehrt():
    status, _, aktion = _bewerte_a(_aend(eindeutig=False, unklar_grund="Jahr?"))
    assert status == "auto" and aktion["absage"] is True and not aktion.get("warnung")


def test_absage_ohne_beleg_wird_ausgefuehrt_und_markiert():
    status, _, aktion = _bewerte_a(_aend(beleg="fällt am Samstag aus"))
    assert status == "auto" and "Beleg" in aktion["warnung"]


def test_kein_ziel_wird_verworfen_statt_pruefliste():
    status, grund, aktion = _bewerte_a(_aend(), seite=_seite(("Lesung Müller", "nlgr", "19:00 Uhr", "")))
    assert status == "verwerfen" and "kein passender Termin" in grund and aktion is None
    assert "genauer" in hw.kurzgrund(grund)


def test_mehrere_ziele_werden_verworfen_statt_pruefliste():
    status, grund, aktion = _bewerte_a(_aend(bezug_name="Schmiede"),
                                       seite=_seite(SCHMIEDE, ("Schmiede-Konzert", "facebook", "20:00 Uhr", "")))
    assert status == "verwerfen" and "mehrere" in grund and aktion is None
    assert "genauer" in hw.kurzgrund(grund)


def test_ungueltiger_link_wird_verworfen():
    a = _aend(art="korrektur", neu_link="javascript:alert(1)", beleg="Offene Schmiede am Freitag, 23.10.2026")
    status, grund, aktion = _bewerte_a(a)
    assert status == "verwerfen" and "Link ungültig" in grund and aktion is None


def test_unauth_absage_bleibt_pruefung():
    status, _, _ = _bewerte_a(_aend(), mail=_mail("Die Offene Schmiede am Freitag, 23.10.2026 fällt aus.",
                                                  vertrauen="redaktion_unauth"))
    assert status == "pruefen"


def _verschiebung():
    mail = _mail("Die Offene Schmiede wird vom 23.10.2026 auf den 30.10.2026 verschoben, Beginn 14 Uhr.")
    a = _aend(art="korrektur", neu_datum="2026-10-30", neu_uhrzeit="14:00",
              beleg="auf den 30.10.2026 verschoben, Beginn 14 Uhr")
    return mail, a


def test_verschiebung_scraper_termin_wird_ausgefuehrt():
    mail, a = _verschiebung()
    status, _, aktion = _bewerte_a(a, mail=mail)
    assert status == "auto" and aktion["ziel"]["typ"] == "scraper"

    eintraege, korrekturen = [], []
    was = hw.wende_aenderung_an(aktion, eintraege, korrekturen, mail, HEUTE, freigegeben=True)
    assert "datum" in was
    assert korrekturen == [{"datum": "2026-10-23", "name": "Offene Schmiede", "name_norm": "offene schmiede",
                            "quelle": "altstadtschmiede", "aenderung": {}, "absage": False,
                            "verschoben_auf": "2026-10-30", "hw_mail": "kalender:m1@x", "freigegeben": True,
                            "angelegt": "2026-10-11"}]
    assert len(eintraege) == 1
    neu = eintraege[0]
    assert (neu["name"], neu["datum"], neu["uhrzeit"], neu["ort"]) == \
        ("Offene Schmiede", "2026-10-30", "14:00", "Altstadtschmiede, Kirchplatz 1")
    assert neu["freigegeben"] is True and neu["hw_mail"] == "kalender:m1@x"


def test_verschiebung_ist_idempotent():
    mail, a = _verschiebung()
    eintraege, korrekturen = [], []
    for _ in range(2):
        _, _, aktion = _bewerte_a(a, mail=mail)
        hw.wende_aenderung_an(aktion, eintraege, korrekturen, mail, HEUTE, freigegeben=True)
    assert len(eintraege) == 1 and len(korrekturen) == 1


def test_verschobene_korrektur_gilt_nicht_als_verwaist():
    """Zieht die Quelle nach, verschwindet der alte Termin. Das ist erwartet und keine Meldung wert."""
    k = {"datum": "2026-10-23", "name_norm": "offene schmiede", "freigegeben": True, "angelegt": "2026-10-01",
         "verschoben_auf": "2026-10-30", "absage": False, "aenderung": {}}
    assert hw.finde_verwaiste_korrekturen([k], HEUTE, _seite()) == []


# --------------------------------------------------------------------------- Bericht

def test_bericht_markiert_warnungen():
    bericht = {"erstellt": "2026-10-12T00:30:00",
               "eingetragen": [{"datum": "2026-10-23", "name": "Lesung", "warnung": "Beleg-Zitat nicht im Mailtext gefunden"},
                               {"datum": "2026-10-24", "name": "Konzert"}],
               "abgesagt": [{"datum": "2026-10-23", "name": "Offene Schmiede", "warnung": "Wochentag im Beleg passt nicht"}]}
    text = hw_bericht.baue_nachricht(bericht, "live")
    assert "Lesung - bitte ansehen: Beleg-Zitat" in text
    assert "Offene Schmiede - bitte ansehen: Wochentag" in text
    assert "Konzert\n" in text + "\n" and "Konzert - bitte" not in text
