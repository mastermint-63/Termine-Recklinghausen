"""Herkunft bei Redaktionsterminen ohne Link (Wunsch FS, 24.10.2026): Statt eines Links steht da, woher der Termin
stammt (Pressemitteilung, Zeitungsbericht, Plakat oder Hinweis der Redaktion)."""
from datetime import date, datetime

import app
import hw_import as hw
from scraper import Termin

TAG = datetime(2026, 10, 24, 17, 30)


def _html(**kw):
    t = Termin(**{"name": "Grillstand der Tafel", "datum": TAG, "uhrzeit": "17:30 Uhr", "ort": "Gymnasialkirche",
                  "link": "", "quelle": "manuell", **kw})
    return app.generiere_html([t], 2026, 10, [(2026, 10)], "termine_re_2026_10.html")


def test_zeitung_ohne_link():
    assert "Quelle: Zeitungsbericht, kein Link zum Veranstalter" in _html(herkunft="zeitung")


def test_pressemitteilungen():
    assert "Quelle: Pressemitteilung der Stadt Recklinghausen" in _html(herkunft="pressemitteilung_stadt")
    assert "Quelle: Pressemitteilung des Kreises Recklinghausen" in _html(herkunft="pressemitteilung_kreis")


def test_ohne_herkunft_oder_unbekannt_hinweis_der_redaktion():
    assert "Quelle: Hinweis der Redaktion, kein Link zum Veranstalter" in _html()
    assert "Quelle: Hinweis der Redaktion" in _html(herkunft="<script>")
    assert "<script>" not in _html(herkunft="<script>").split("<body", 1)[1].split("<script", 1)[0]


def test_mit_link_kein_hinweis():
    assert "termin-herkunft\"" not in _html(herkunft="zeitung", link="https://example.org/grill")


def test_scraper_termin_ohne_link_kein_hinweis():
    assert "termin-herkunft\"" not in _html(quelle="frauenforum")


def test_herkunft_nicht_im_stand():
    t = Termin(name="X", datum=TAG, uhrzeit="", ort="", link="", quelle="manuell", herkunft="zeitung")
    assert "herkunft" not in app._termin_zu_dict(t)


# --------------------------------------------------------------------------- Import

def _mail(absender="E <e@x.example>", konto="kalender", presse=False):
    m = hw.Mail(konto=konto, id=1, message_id="m1@x", datum=datetime(2026, 10, 23, 14, 15), betreff="Kalender",
                absender=absender, text="Samstag, 31.10.2026 Grillstand", vertrauen="vertraut")
    m.presse_auto = presse
    return m


def _herkunft(mail, **kw):
    t = {"name": "Grillstand", "datum": "2026-10-31", "uhrzeit": "17:30", "ort": "Gymnasialkirche", "eindeutig": True,
         "in_recklinghausen": True, "beleg": "BILD", "kategorie": "Fest", **kw}
    status, _, e = hw.bewerte_termin(t, mail, date(2026, 10, 24), lambda e, m: False, lambda e: None, lambda e: None)
    assert e, status  # Presse-Mails landen hier ohne Anhang auf der Prüfliste, das Feld zählt
    return e["herkunft"]


def test_import_herkunft_aus_modell():
    assert _herkunft(_mail(), herkunft="zeitung") == "zeitung"
    assert _herkunft(_mail(), herkunft="plakat") == "plakat"
    assert _herkunft(_mail(), herkunft="sonst") == "redaktion"
    assert _herkunft(_mail(), herkunft="erfunden") == "redaktion"
    assert _herkunft(_mail()) == "redaktion"


def test_import_herkunft_presse_aus_absender_nicht_aus_modell():
    stadt = _mail("Pressestelle <PressestelleRecklinghausen@recklinghausen.de>", konto="gmx", presse=True)
    kreis = _mail("Kreis Recklinghausen <info@presse.example>", konto="gmx", presse=True)
    assert _herkunft(stadt, herkunft="zeitung") == "pressemitteilung_stadt"
    assert _herkunft(kreis) == "pressemitteilung_kreis"


def test_schema_kennt_herkunft():
    felder = hw.TOOL["input_schema"]["properties"]["termine"]["items"]["properties"]
    assert felder["herkunft"]["enum"] == ["zeitung", "plakat", "sonst"]
