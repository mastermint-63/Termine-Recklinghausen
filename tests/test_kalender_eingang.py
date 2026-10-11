"""Tests für den Kalender-Eingang (IMAP): MIME-Zerlegung, Vertrauensstufen, Massenmails.

Ohne Netz und ohne echte Adressen: alle Mails sind künstlich, Domains aus .example/.test.
"""
import io
from email.message import EmailMessage

import hw_import as hw
import kalender_eingang as ke

REDAKTION = {"ralf@redaktion.example", "fs@mailer.example"}

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 25_000
PDF = b"%PDF-1.4\n" + b"0" * 500


def _docx_bytes(text: str) -> bytes:
    from docx import Document
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _mail(von="Ralf <ralf@redaktion.example>", auth=None, extra_header=(), betreff="Termin"):
    m = EmailMessage()
    # iCloud setzt seine Header oberhalb der Absender-Header
    for k, v in auth or []:
        m[k] = v
    m["From"] = von
    m["To"] = "sammeladresse@empfang.example"
    m["Subject"] = betreff
    m["Date"] = "Sun, 11 Oct 2026 10:40:00 +0200"
    m["Message-ID"] = "<abc123@mailer.example>"
    for k, v in extra_header:
        m[k] = v
    m.set_content("Am Freitag, 23.10.2026 um 19:00 Uhr Lesung im Altstadtcafé, Recklinghausen.")
    m.add_alternative("<p>Am Freitag, 23.10.2026 um <b>19:00 Uhr</b> Lesung</p>", subtype="html")
    return m


def _auth_pass(domain="redaktion.example"):
    return [
        ("Authentication-Results", "bimi.icloud.com; bimi=none"),
        ("Authentication-Results", f"dmarc.icloud.com; dmarc=pass header.from={domain}"),
        ("Authentication-Results", f"dkim-verifier.icloud.com; dkim=pass header.d={domain} header.i=@{domain}"),
        ("Authentication-Results", f"spf.icloud.com; spf=pass smtp.mailfrom=x@{domain}"),
    ]


# --------------------------------------------------------------------------- MIME-Zerlegung

def test_mime_teile_haben_dieselbe_struktur_wie_em_client():
    m = _mail()
    m.add_attachment(JPEG, maintype="image", subtype="jpeg", filename="plakat.jpg")
    m.add_attachment(PDF, maintype="application", subtype="pdf", filename="flyer.pdf")
    m.add_attachment(_docx_bytes("Konzert am Samstag, 24.10.2026"), maintype="application",
                     subtype="vnd.openxmlformats-officedocument.wordprocessingml.document", filename="pm.docx")
    teile = ke.mime_teile(m)
    text, bilder, pdfs = hw.werte_teile_aus(teile)
    assert "Lesung im Altstadtcafé" in text
    assert "[Angehängtes Word-Dokument]" in text and "24.10.2026" in text
    assert bilder == [("image/jpeg", JPEG)]
    assert pdfs == [PDF]
    # gleiche Auswertung wie der eM-Client-Weg (contentType, partBody)
    em_teile = [("text/plain; charset=utf-8", "Am Freitag, 23.10.2026 um 19:00 Uhr Lesung im Altstadtcafé, "
                 "Recklinghausen.\n"), ("image/jpeg", JPEG), ("application/pdf", PDF)]
    em_text, em_bilder, em_pdfs = hw.werte_teile_aus(em_teile)
    assert em_text.strip() == text.split("\n\n[Angehängtes")[0].strip()
    assert (em_bilder, em_pdfs) == (bilder, pdfs)


def test_nur_html_mail_liefert_text():
    m = EmailMessage()
    m["From"] = "a@b.example"
    m.set_content("<p>Vortrag am <b>Montag, 26.10.2026</b> um 18 Uhr in der Stadtbibliothek</p>", subtype="html")
    text, _, _ = hw.werte_teile_aus(ke.mime_teile(m))
    assert "Vortrag am Montag, 26.10.2026" in text and "<b>" not in text


def test_kleine_bilder_werden_ignoriert():
    m = _mail()
    m.add_attachment(b"\xff\xd8\xff\xe0" + b"\x00" * 100, maintype="image", subtype="jpeg", filename="logo.jpg")
    _, bilder, _ = hw.werte_teile_aus(ke.mime_teile(m))
    assert bilder == []


def test_baue_mail_setzt_schluessel_und_felder():
    m = _mail(auth=_auth_pass())
    mail = ke.baue_mail(m, uid=7, redaktion=REDAKTION)
    assert mail.schluessel == "kalender:abc123@mailer.example"
    assert mail.konto == "kalender" and mail.betreff == "Termin"
    assert "ralf@redaktion.example" in mail.absender
    assert mail.datum.year == 2026 and mail.datum.month == 10
    assert mail.vertrauen == "vertraut"


# --------------------------------------------------------------------------- Vertrauensstufen

def test_redaktion_mit_dkim_pass_ist_vertraut():
    assert ke.vertrauensstufe(_mail(auth=_auth_pass()), REDAKTION)[0] == "vertraut"


def test_redaktion_mit_nur_dmarc_pass_ist_vertraut():
    auth = [("Authentication-Results", "dmarc.icloud.com; dmarc=pass header.from=redaktion.example"),
            ("Authentication-Results", "dkim-verifier.icloud.com; dkim=none"),
            ("Authentication-Results", "spf.icloud.com; spf=pass smtp.mailfrom=x@redaktion.example")]
    assert ke.vertrauensstufe(_mail(auth=auth), REDAKTION)[0] == "vertraut"


def test_redaktion_mit_dkim_fail_ist_nicht_authentifiziert():
    auth = [("Authentication-Results", "dmarc.icloud.com; dmarc=fail header.from=redaktion.example"),
            ("Authentication-Results", "dkim-verifier.icloud.com; dkim=fail header.d=redaktion.example"),
            ("Authentication-Results", "spf.icloud.com; spf=fail")]
    stufe, grund = ke.vertrauensstufe(_mail(auth=auth), REDAKTION)
    assert stufe == "redaktion_unauth" and "nicht authentifiziert" in grund


def test_redaktion_ohne_dkim_ist_nicht_authentifiziert():
    auth = [("Authentication-Results", "dmarc.icloud.com; dmarc=none header.from=redaktion.example"),
            ("Authentication-Results", "dkim-verifier.icloud.com; dkim=none"),
            ("Authentication-Results", "spf.icloud.com; spf=none")]
    assert ke.vertrauensstufe(_mail(auth=auth), REDAKTION)[0] == "redaktion_unauth"


def test_ohne_icloud_header_nicht_authentifiziert():
    assert ke.vertrauensstufe(_mail(), REDAKTION)[0] == "redaktion_unauth"


def test_gefaelschter_from_mit_fremder_dkim_domain():
    """Angreifer signiert korrekt für seine eigene Domain, setzt aber eine Redaktionsadresse in From."""
    auth = [("Authentication-Results", "dmarc.icloud.com; dmarc=fail header.from=redaktion.example"),
            ("Authentication-Results", "dkim-verifier.icloud.com; dkim=pass header.d=angreifer.test"),
            ("Authentication-Results", "spf.icloud.com; spf=pass smtp.mailfrom=x@angreifer.test")]
    assert ke.vertrauensstufe(_mail(auth=auth), REDAKTION)[0] == "redaktion_unauth"


def test_eingeschmuggelter_auth_header_unterhalb_von_icloud_zaehlt_nicht():
    """Ein gefälschter 'dkim=pass'-Header aus der Mail selbst steht unter iClouds echtem Block."""
    auth = [("Authentication-Results", "dmarc.icloud.com; dmarc=none header.from=redaktion.example"),
            ("Authentication-Results", "spf.icloud.com; spf=none"),
            # ab hier Header des Absenders
            ("Authentication-Results", "dkim-verifier.icloud.com; dkim=pass header.d=redaktion.example"),
            ("Authentication-Results", "dmarc.icloud.com; dmarc=pass header.from=redaktion.example")]
    assert ke.vertrauensstufe(_mail(auth=auth), REDAKTION)[0] == "redaktion_unauth"


def test_fremder_auth_server_zaehlt_nicht():
    auth = [("Authentication-Results", "mx.angreifer.test; dkim=pass header.d=redaktion.example; "
                                       "dmarc=pass header.from=redaktion.example"),
            ("Authentication-Results", "spf.icloud.com; spf=none")]
    assert ke.vertrauensstufe(_mail(auth=auth), REDAKTION)[0] == "redaktion_unauth"


def test_unbekannter_absender():
    m = _mail(von="Fremd <wer@anders.example>", auth=_auth_pass("anders.example"))
    assert ke.vertrauensstufe(m, REDAKTION)[0] == "unbekannt"


def test_absender_vergleich_ignoriert_gross_klein():
    m = _mail(von="Ralf <Ralf@Redaktion.Example>", auth=_auth_pass())
    assert ke.vertrauensstufe(m, REDAKTION)[0] == "vertraut"


def test_mehrere_from_adressen_sind_unbekannt():
    m = _mail(von="ralf@redaktion.example, wer@anders.example", auth=_auth_pass())
    assert ke.vertrauensstufe(m, REDAKTION)[0] == "unbekannt"


def test_dkim_der_elterndomain_reicht_nicht_fuer_fremde_subdomain():
    """header.d=example deckt nicht redaktion.example ab (andere Domain)."""
    auth = [("Authentication-Results", "dkim-verifier.icloud.com; dkim=pass header.d=example"),
            ("Authentication-Results", "spf.icloud.com; spf=none")]
    assert ke.vertrauensstufe(_mail(auth=auth), REDAKTION)[0] == "redaktion_unauth"


def test_redaktionsliste_aus_env_text():
    assert ke.lese_redaktion(" A@x.example, b@y.example ,,") == {"a@x.example", "b@y.example"}
    assert ke.lese_redaktion("") == set()


# --------------------------------------------------------------------------- Massenmails

def test_massenmail_wird_erkannt():
    assert ke.ist_massenmail(_mail(extra_header=[("List-Unsubscribe", "<https://x.example/u>")]))
    assert ke.ist_massenmail(_mail(extra_header=[("List-Id", "<news.x.example>")]))
    assert not ke.ist_massenmail(_mail())


def test_ohne_icloud_spf_zeile_wird_nichts_gewertet():
    """Ohne iClouds SPF-Zeile ist die Blockgrenze unklar: dann zählt kein Prüfergebnis."""
    auth = [("Authentication-Results", "dkim-verifier.icloud.com; dkim=pass header.d=redaktion.example"),
            ("Authentication-Results", "dmarc.icloud.com; dmarc=pass header.from=redaktion.example")]
    assert ke.vertrauensstufe(_mail(auth=auth), REDAKTION)[0] == "redaktion_unauth"


def test_dkim_mit_laengenbegrenzung_ist_nicht_vertraut():
    """l=-Tag: Signatur deckt nur den Anfang des Texts ab, angehängter Text wäre ungeprüft."""
    auth = _auth_pass() + [("DKIM-Signature", "v=1; a=rsa-sha256; d=redaktion.example; s=s1; l=120; h=from:to; "
                                              "bh=abc; b=def")]
    stufe, grund = ke.vertrauensstufe(_mail(auth=auth), REDAKTION)
    assert stufe == "redaktion_unauth" and "Teil" in grund


def test_dkim_fuer_anderes_postfach_derselben_domain_ist_nicht_vertraut():
    """header.i nennt ein anderes Postfach (z.B. fremdes GMX-Konto mit gefälschtem From)."""
    auth = [("Authentication-Results", "dmarc.icloud.com; dmarc=pass header.from=redaktion.example"),
            ("Authentication-Results", "dkim-verifier.icloud.com; dkim=pass header.d=redaktion.example "
                                       "header.i=fremd@redaktion.example header.b=xyz"),
            ("Authentication-Results", "spf.icloud.com; spf=pass smtp.mailfrom=fremd@redaktion.example")]
    assert ke.vertrauensstufe(_mail(auth=auth), REDAKTION)[0] == "redaktion_unauth"


def test_dkim_mit_passendem_postfach_ist_vertraut():
    auth = [("Authentication-Results", "dkim-verifier.icloud.com; dkim=pass header.d=redaktion.example "
                                       "header.i=ralf@redaktion.example header.b=xyz"),
            ("Authentication-Results", "spf.icloud.com; spf=pass")]
    assert ke.vertrauensstufe(_mail(auth=auth), REDAKTION)[0] == "vertraut"


# --------------------------------------------------------------------------- HEIC (iPhone-Fotos)

def _heic_bytes(tmp_path) -> bytes:
    """Echtes HEIC per sips aus einem gerenderten Bild (macOS)."""
    import shutil
    import subprocess

    import fitz
    import pytest
    if not shutil.which("sips"):
        pytest.skip("sips nicht vorhanden")
    doc = fitz.open()
    seite = doc.new_page(width=1200, height=1600)
    seite.insert_text((100, 200), "Konzert am Samstag, 24.10.2026, 20 Uhr", fontsize=40)
    png = tmp_path / "plakat.png"
    seite.get_pixmap(dpi=150).save(png)
    heic = tmp_path / "plakat.heic"
    r = subprocess.run(["sips", "-s", "format", "heic", str(png), "--out", str(heic)], capture_output=True)
    if r.returncode != 0 or not heic.exists():
        pytest.skip("sips kann kein HEIC schreiben")
    return heic.read_bytes()


def test_heic_wird_erkannt():
    assert hw._bildtyp(b"\x00\x00\x00\x18ftypheic" + b"\x00" * 20) == "image/heic"
    assert hw._bildtyp(b"\x00\x00\x00\x18ftypmif1" + b"\x00" * 20) == "image/heic"


def test_heic_anhang_wird_als_jpeg_mitgegeben(tmp_path):
    heic = _heic_bytes(tmp_path)
    m = _mail()
    m.add_attachment(heic, maintype="image", subtype="heic", filename="IMG_0001.HEIC")
    _, bilder, _ = hw.werte_teile_aus(ke.mime_teile(m))
    assert len(bilder) == 1 and bilder[0][0] == "image/jpeg" and bilder[0][1][:3] == b"\xff\xd8\xff"


def test_heic_als_octet_stream_wird_erkannt(tmp_path):
    heic = _heic_bytes(tmp_path)
    m = _mail()
    m.add_attachment(heic, maintype="application", subtype="octet-stream", filename="IMG_0001.HEIC")
    _, bilder, _ = hw.werte_teile_aus(ke.mime_teile(m))
    assert len(bilder) == 1 and bilder[0][0] == "image/jpeg"
