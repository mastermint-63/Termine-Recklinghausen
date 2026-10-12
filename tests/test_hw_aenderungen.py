"""Tests für Korrekturen und Absagen im HW-Import: Zielsuche, Bewertung, Anwendung. Ohne API, ohne Mail."""
from datetime import date, datetime

import hw_import as hw
from scraper import Termin

HEUTE = date(2026, 10, 11)
TAG = date(2026, 10, 23)  # Freitag


def _mail(text="Die Offene Schmiede am Freitag, 23.10.2026 beginnt erst um 14 Uhr.", vertrauen="vertraut"):
    return hw.Mail(konto="kalender", id=1, message_id="m1@x", datum=datetime(2026, 10, 11, 10, 0),
                   betreff="Korrektur", absender="R <r@x.example>", text=text, vertrauen=vertrauen,
                   vertrauen_grund="" if vertrauen == "vertraut" else "Absender nicht authentifiziert")


def _seite(*termine):
    """Ersatz für lade_bestehende(): Termine der generierten Monatsseite am TAG."""
    def bestehende(d):
        return [Termin(name=n, datum=datetime.combine(d, datetime.min.time()), uhrzeit=u, ort="", link="",
                       quelle=q) for (n, q, u) in termine] if d == TAG else []
    return bestehende


def _aend(**kw):
    a = {"art": "korrektur", "bezug_name": "Offene Schmiede", "bezug_datum": "2026-10-23", "neu_datum": "",
         "neu_uhrzeit": "14:00", "neu_ort": "", "beleg": "beginnt erst um 14 Uhr", "eindeutig": True,
         "unklar_grund": "", "quellfehler": False}
    a.update(kw)
    return a


MANUELL = {"name": "Offene Schmiede", "datum": "2026-10-23", "uhrzeit": "10:00", "ort": "Altstadtschmiede",
           "freigegeben": True}


# --------------------------------------------------------------------------- Zielsuche

def test_ziel_kein_treffer():
    assert hw.finde_ziele("Offene Schmiede", TAG, [], _seite(("Lesung Müller", "nlgr", "19:00 Uhr"))) == []


def test_ziel_ein_scraper_treffer():
    ziele = hw.finde_ziele("Offene Schmiede", TAG, [], _seite(("Offene Schmiede", "altstadtschmiede", "10:00 Uhr"),
                                                            ("Lesung Müller", "nlgr", "19:00 Uhr")))
    assert len(ziele) == 1 and ziele[0]["typ"] == "scraper" and ziele[0]["quelle"] == "altstadtschmiede"


def test_ziel_manueller_eintrag_statt_seitenkopie():
    """Manuelle Termine stehen auch auf der Seite; gezählt wird nur der JSON-Eintrag."""
    ziele = hw.finde_ziele("Offene Schmiede", TAG, [dict(MANUELL)], _seite(("Offene Schmiede", "manuell", "10:00 Uhr")))
    assert len(ziele) == 1 and ziele[0]["typ"] == "manuell" and ziele[0]["index"] == 0


def test_ziel_zwei_treffer():
    ziele = hw.finde_ziele("Schmiede", TAG, [], _seite(("Offene Schmiede", "altstadtschmiede", "10:00 Uhr"),
                                                     ("Schmiede-Konzert", "facebook", "20:00 Uhr")))
    assert len(ziele) == 2


def test_ziel_genauer_treffer_schlaegt_schluesselwort():
    """Teilstring-Treffer haben Vorrang vor Treffern nur über ein markantes Schlüsselwort."""
    ziele = hw.finde_ziele("Offene Schmiede", TAG, [], _seite(("Offene Schmiede", "altstadtschmiede", "10:00 Uhr"),
                                                            ("Schmiede-Sommerfest", "facebook", "20:00 Uhr")))
    assert len(ziele) == 1 and ziele[0]["quelle"] == "altstadtschmiede"


def test_ziel_ignoriert_nicht_freigegebene_manuelle():
    e = dict(MANUELL, freigegeben=False)
    assert hw.finde_ziele("Offene Schmiede", TAG, [e], _seite()) == []


# --------------------------------------------------------------------------- Bewertung

def _bewerte(a, mail=None, eintraege=None, seite=None):
    return hw.bewerte_aenderung(a, mail or _mail(), HEUTE, eintraege or [],
                                seite or _seite(("Offene Schmiede", "altstadtschmiede", "10:00 Uhr")))


def test_korrektur_scraper_termin_automatisch():
    status, _, aktion = _bewerte(_aend())
    assert status == "auto" and aktion["ziel"]["typ"] == "scraper" and aktion["aenderung"] == {"uhrzeit": "14:00"}


def test_absage_scraper_termin_automatisch():
    status, _, aktion = _bewerte(_aend(art="absage", neu_uhrzeit="", beleg="Offene Schmiede am Freitag, 23.10.2026"))
    assert status == "auto" and aktion["absage"] is True


def test_verschiebung_scraper_termin_immer_pruefen():
    mail = _mail("Die Offene Schmiede wird vom 23.10.2026 auf den 30.10.2026 verschoben.")
    status, grund, _ = _bewerte(_aend(neu_datum="2026-10-30", neu_uhrzeit="", beleg="auf den 30.10.2026 verschoben"),
                                mail=mail)
    assert status == "pruefen" and "Verschiebung" in grund


def test_verschiebung_manueller_termin_automatisch():
    mail = _mail("Die Offene Schmiede wird vom 23.10.2026 auf den 30.10.2026 verschoben.")
    status, _, aktion = _bewerte(_aend(neu_datum="2026-10-30", neu_uhrzeit="", beleg="auf den 30.10.2026 verschoben"),
                                 mail=mail, eintraege=[dict(MANUELL)], seite=_seite())
    assert status == "auto" and aktion["aenderung"] == {"datum": "2026-10-30"}


def test_kein_ziel_geht_zur_pruefung():
    status, grund, aktion = _bewerte(_aend(), seite=_seite(("Lesung Müller", "nlgr", "19:00 Uhr")))
    assert status == "pruefen" and "kein passender Termin" in grund and aktion is not None


def test_mehrere_ziele_gehen_zur_pruefung():
    status, grund, _ = _bewerte(_aend(bezug_name="Schmiede"),
                                seite=_seite(("Offene Schmiede", "altstadtschmiede", "10:00 Uhr"),
                                             ("Schmiede-Konzert", "facebook", "20:00 Uhr")))
    assert status == "pruefen" and "mehrere" in grund


def test_beleg_nicht_im_text_geht_zur_pruefung():
    status, grund, _ = _bewerte(_aend(beleg="beginnt um 15 Uhr"))
    assert status == "pruefen" and "Beleg" in grund


def test_nicht_authentifiziert_geht_zur_pruefung():
    status, grund, _ = _bewerte(_aend(), mail=_mail(vertrauen="redaktion_unauth"))
    assert status == "pruefen" and "nicht authentifiziert" in grund


def test_unklar_geht_zur_pruefung():
    status, grund, _ = _bewerte(_aend(eindeutig=False, unklar_grund="welcher Termin?"))
    assert status == "pruefen" and "welcher Termin?" in grund


def test_vergangener_bezug_wird_verworfen():
    assert _bewerte(_aend(bezug_datum="2026-10-01"))[0] == "verwerfen"


def test_korrektur_ohne_neue_angabe_wird_verworfen():
    assert _bewerte(_aend(neu_uhrzeit=""))[0] == "verwerfen"


def test_korrektur_ohne_wirkung_wird_verworfen():
    """Die Seite zeigt schon 14:00 Uhr: nichts zu tun."""
    status, grund, _ = _bewerte(_aend(), seite=_seite(("Offene Schmiede", "altstadtschmiede", "14:00 Uhr")))
    assert status == "verwerfen" and "bereits" in grund


def test_wochentag_im_beleg_muss_passen():
    mail = _mail("Die Offene Schmiede am Samstag, 23.10.2026 beginnt erst um 14 Uhr.")
    status, grund, _ = _bewerte(_aend(beleg="Samstag, 23.10.2026 beginnt erst um 14 Uhr"), mail=mail)
    assert status == "pruefen" and "Wochentag" in grund


# --------------------------------------------------------------------------- Anwendung

def test_anwenden_auf_manuellen_eintrag_mit_spur():
    eintraege, korrekturen = [dict(MANUELL)], []
    _, _, aktion = _bewerte(_aend(), eintraege=eintraege, seite=_seite())
    hw.wende_aenderung_an(aktion, eintraege, korrekturen, _mail(), HEUTE, freigegeben=True)
    assert eintraege[0]["uhrzeit"] == "14:00" and korrekturen == []
    assert eintraege[0]["hw_aenderungen"] == [{"mail": "kalender:m1@x", "feld": "uhrzeit", "alt": "10:00", "neu": "14:00"}]


def test_absage_manueller_eintrag():
    eintraege, korrekturen = [dict(MANUELL)], []
    _, _, aktion = _bewerte(_aend(art="absage", neu_uhrzeit="", beleg="Offene Schmiede am Freitag, 23.10.2026"),
                            eintraege=eintraege, seite=_seite())
    hw.wende_aenderung_an(aktion, eintraege, korrekturen, _mail(), HEUTE, freigegeben=True)
    assert eintraege[0]["abgesagt"] is True and eintraege[0]["hw_aenderungen"][0]["feld"] == "abgesagt"


def test_anwenden_auf_scraper_termin_schreibt_korrektur():
    eintraege, korrekturen = [], []
    _, _, aktion = _bewerte(_aend())
    hw.wende_aenderung_an(aktion, eintraege, korrekturen, _mail(), HEUTE, freigegeben=True)
    assert korrekturen == [{"datum": "2026-10-23", "name": "Offene Schmiede", "name_norm": "offene schmiede",
                            "quelle": "altstadtschmiede", "aenderung": {"uhrzeit": "14:00"}, "absage": False,
                            "hw_mail": "kalender:m1@x", "freigegeben": True, "angelegt": "2026-10-11"}]


def test_pruefen_schreibt_nicht_freigegebene_korrektur_mit_hinweis():
    eintraege, korrekturen = [], []
    _, grund, aktion = _bewerte(_aend(), seite=_seite(("Lesung Müller", "nlgr", "19:00 Uhr")))
    hw.wende_aenderung_an(aktion, eintraege, korrekturen, _mail(), HEUTE, freigegeben=False, hinweis=grund)
    k = korrekturen[0]
    assert k["freigegeben"] is False and k["name_norm"] == "" and k["bezug_name"] == "Offene Schmiede"
    assert "kein passender Termin" in k["hinweis"]


def test_pruefen_bei_manuellem_ziel_aendert_json_nicht():
    eintraege, korrekturen = [dict(MANUELL)], []
    _, grund, aktion = _bewerte(_aend(), mail=_mail(vertrauen="unbekannt"), eintraege=eintraege, seite=_seite())
    hw.wende_aenderung_an(aktion, eintraege, korrekturen, _mail(), HEUTE, freigegeben=False, hinweis=grund)
    assert eintraege[0]["uhrzeit"] == "10:00" and korrekturen[0]["quelle"] == "manuell"


def test_korrektur_wird_nicht_doppelt_angelegt():
    eintraege, korrekturen = [], []
    for _ in range(2):
        _, _, aktion = _bewerte(_aend())
        hw.wende_aenderung_an(aktion, eintraege, korrekturen, _mail(), HEUTE, freigegeben=True)
    assert len(korrekturen) == 1


def test_alte_korrekturen_werden_nach_14_tagen_abgeraeumt():
    ks = [{"datum": "2026-09-20"}, {"datum": "2026-09-30"}, {"datum": "2026-10-23"}]
    assert [k["datum"] for k in hw.raeume_korrekturen(ks, HEUTE)] == ["2026-09-30", "2026-10-23"]


# --------------------------------------------------------------------------- Termine von nicht vertrauten Absendern

def test_neuer_termin_von_unbekanntem_absender_geht_zur_pruefung():
    mail = _mail("Am Freitag, 23.10.2026 um 19:00 Uhr Lesung im Altstadtcafé", vertrauen="unbekannt")
    mail.vertrauen_grund = "Absender nicht in der Redaktionsliste"
    t = {"name": "Lesung", "datum": "2026-10-23", "uhrzeit": "19:00", "ort": "Altstadtcafé", "eindeutig": True,
         "in_recklinghausen": True, "beleg": "Freitag, 23.10.2026 um 19:00 Uhr", "kategorie": "Lesung"}
    status, grund, e = hw.bewerte_termin(t, mail, HEUTE, lambda e, m: False, lambda e: False, lambda e: None)
    assert status == "pruefen" and "Redaktionsliste" in grund and e["freigegeben"] is False


# --------------------------------------------------------------------------- Verwaiste Korrekturen

def test_verwaiste_korrektur_wird_erkannt():
    ks = [{"datum": "2026-10-23", "name": "Offene Schmiede", "name_norm": "offene schmiede", "freigegeben": True,
           "angelegt": "2026-10-10"},
          {"datum": "2026-10-23", "name": "Weg", "name_norm": "verschwundener termin", "freigegeben": True,
           "angelegt": "2026-10-10"},
          {"datum": "2026-10-23", "name": "Neu", "name_norm": "noch nicht generiert", "freigegeben": True,
           "angelegt": "2026-10-11"}]
    verwaist = hw.finde_verwaiste_korrekturen(ks, HEUTE, _seite(("Offene Schmiede", "altstadtschmiede", "14:00 Uhr")))
    assert [k["name"] for k in verwaist] == ["Weg"]


def test_aenderung_aus_presse_automatik_geht_zur_pruefung():
    """Presse-Mails werden nur an Absender/Anzeigename erkannt (fälschbar): Änderungen nie automatisch."""
    mail = _mail()
    mail.presse_auto = True
    status, grund, _ = _bewerte(_aend(), mail=mail)
    assert status == "pruefen" and "Presse" in grund


# --------------------------------------------------------------------------- SSRF-Schutz Terminseiten

def test_interne_adressen_werden_nicht_abgerufen():
    for url in ["http://127.0.0.1:8100/", "http://localhost/x", "http://192.168.1.10/", "http://10.0.0.1/",
                "http://[::1]/", "http://169.254.169.254/latest", "ftp://example.org/", "http://0.0.0.0/"]:
        assert not hw._url_erlaubt(url), url


def test_oeffentliche_adresse_ist_erlaubt(monkeypatch):
    monkeypatch.setattr(hw.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.215.14", 0))])
    assert hw._url_erlaubt("https://verein.example/termine")


def test_hostname_der_intern_aufloest_ist_gesperrt(monkeypatch):
    monkeypatch.setattr(hw.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("192.168.1.5", 0))])
    assert not hw._url_erlaubt("https://intern.example/")


def test_terminseite_von_nicht_vertrautem_absender_wird_nicht_abgerufen(monkeypatch):
    aufrufe = []
    monkeypatch.setattr(hw, "pruefe_terminseite", lambda url: aufrufe.append(url) or "x")
    monkeypatch.setattr(hw, "bekannte_hosts", lambda: set())
    mail = _mail("Neue Terminseite: https://verein.example/termine", vertrauen="unbekannt")
    gemeldet = hw.melde_neue_seiten([{"url": "https://verein.example/termine", "beschreibung": "Verein"}], mail, True)
    assert aufrufe == [] and gemeldet and "nicht abgerufen" in gemeldet[0]


def test_terminseite_aus_presse_automatik_wird_nicht_abgerufen(monkeypatch):
    aufrufe = []
    monkeypatch.setattr(hw, "pruefe_terminseite", lambda url: aufrufe.append(url) or "x")
    monkeypatch.setattr(hw, "bekannte_hosts", lambda: set())
    mail = _mail("Neue Terminseite: https://verein.example/termine")
    mail.presse_auto = True
    hw.melde_neue_seiten([{"url": "https://verein.example/termine", "beschreibung": "Verein"}], mail, True)
    assert aufrufe == []


# --------------------------------------------------------------------------- Bericht: nicht übernommen

class _Client:
    """Ersatz für den API-Client: liefert eine feste Tool-Antwort."""
    def __init__(self, antwort):
        self.antwort = antwort
        self.messages = self

    def create(self, **kw):
        from types import SimpleNamespace
        return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=self.antwort)])


def test_verworfene_aus_kalender_eingang_stehen_im_bericht():
    antwort = {"termine": [{"name": "SkF-Infostand", "datum": "2026-10-10", "eindeutig": True,
                            "in_recklinghausen": True, "beleg": "PDF"}],
               "aenderungen": [_aend(bezug_datum="2026-10-01")], "terminseiten": []}
    bericht = hw.neuer_bericht()
    hw.verarbeite_mail(_Client(antwort), _mail(), HEUTE, True, [], [], bericht)
    assert [(v["datum"], v["name"]) for v in bericht["verworfen"]] == [("2026-10-10", "SkF-Infostand"),
                                                                      ("2026-10-01", "Offene Schmiede")]
    assert all("Vergangenheit" in v["grund"] for v in bericht["verworfen"])


def test_verworfene_aus_presse_mails_stehen_nicht_im_bericht():
    antwort = {"termine": [{"name": "Alt", "datum": "2026-10-10", "eindeutig": True, "in_recklinghausen": True,
                            "beleg": "x"}], "aenderungen": [], "terminseiten": []}
    mail = _mail()
    mail.konto = "gmx"
    bericht = hw.neuer_bericht()
    hw.verarbeite_mail(_Client(antwort), mail, HEUTE, True, [], [], bericht)
    assert bericht["verworfen"] == []


# --------------------------------------------------------------------------- Grenzen im Hauptablauf

def _lauf(monkeypatch, tmp_path, absender, auth, analysiere, anzahl=30):
    from email.message import EmailMessage
    import sys
    mails = []
    for i in range(anzahl):
        m = EmailMessage()
        for k, v in auth:
            m[k] = v
        m["From"] = absender
        m["Subject"] = f"Mail {i}"
        m["Message-ID"] = f"<m{i}@x.example>"
        m.set_content("Am Freitag, 23.10.2026 um 19 Uhr Lesung.")
        mails.append((i, m, False))
    aufrufe = []
    monkeypatch.setattr(hw, "STATE_PFAD", tmp_path / "state.db")
    monkeypatch.setattr(hw, "_env", lambda n: "r@x.example" if n == "HW_REDAKTION" else "test")
    monkeypatch.setattr(hw, "hole_kalender_mails", lambda heute, bericht, uid=None: mails)
    monkeypatch.setattr(hw, "analysiere", lambda c, m, h: aufrufe.append(m.betreff) or analysiere())
    monkeypatch.setattr(sys, "argv", ["hw_import.py", "--dry-run", "--nur-kalender"])
    hw.main()
    return aufrufe


def test_gefaelschter_redaktionsabsender_faellt_unter_das_limit(monkeypatch, tmp_path):
    aufrufe = _lauf(monkeypatch, tmp_path, "R <r@x.example>", [], lambda: {"termine": [], "aenderungen": [],
                                                                         "terminseiten": []})
    assert len(aufrufe) == hw.MAX_UNBEKANNTE_PRO_LAUF


def test_fehlgeschlagene_auswertungen_zaehlen_zum_limit(monkeypatch, tmp_path):
    auth = [("Authentication-Results", "dkim-verifier.icloud.com; dkim=pass header.d=x.example"),
            ("Authentication-Results", "spf.icloud.com; spf=pass")]

    def kaputt():
        raise RuntimeError("API-Fehler")
    aufrufe = _lauf(monkeypatch, tmp_path, "R <r@x.example>", auth, kaputt)
    assert len(aufrufe) == hw.MAX_MAILS_PRO_LAUF


# --------------------------------------------------------------------------- Link-Korrektur

def _link_mail():
    return _mail("Offene Schmiede am Freitag, 23.10.2026. Richtige Quelle ist aber: https://www.demokratie-werkstadt-re.de/termine/")


def test_link_korrektur_wird_uebernommen():
    a = _aend(neu_uhrzeit="", neu_link="https://www.demokratie-werkstadt-re.de/termine/",
              beleg="Richtige Quelle ist aber: https://www.demokratie-werkstadt-re.de/termine/")
    status, grund, aktion = hw.bewerte_aenderung(a, _link_mail(), HEUTE, [],
                                                _seite(("Offene Schmiede", "altstadtschmiede", "10:00 Uhr")))
    assert status == "auto", grund
    assert aktion["aenderung"] == {"link": "https://www.demokratie-werkstadt-re.de/termine/"}


def test_link_korrektur_ungueltiger_link_zur_pruefung():
    a = _aend(neu_uhrzeit="", neu_link="javascript:alert(1)", beleg="Richtige Quelle ist aber")
    status, grund, _ = hw.bewerte_aenderung(a, _link_mail(), HEUTE, [],
                                           _seite(("Offene Schmiede", "altstadtschmiede", "10:00 Uhr")))
    assert status == "pruefen" and "Link ungültig" in grund


def test_link_korrektur_gleicher_link_manuell_wird_verworfen():
    e = dict(MANUELL, link="https://www.demokratie-werkstadt-re.de/termine/")
    a = _aend(neu_uhrzeit="", neu_link="https://www.demokratie-werkstadt-re.de/termine/",
              beleg="Richtige Quelle ist aber: https://www.demokratie-werkstadt-re.de/termine/")
    status, grund, _ = hw.bewerte_aenderung(a, _link_mail(), HEUTE, [e], _seite())
    assert status == "verwerfen" and "bereits" in grund
