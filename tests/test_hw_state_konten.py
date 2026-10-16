"""Verarbeitet-Status über eM-Client-Konten hinweg (Befund 15.10.2026).

Der Mail-Organizer und der Kehraus verschieben Mails zwischen Konten. Mit dem Schlüssel
konto:message_id galt eine verschobene Mail im neuen Konto als neu und wurde ein zweites
Mal ausgewertet (zwei Presse-Mails des Kreises: 09.10. vestreporter, 13.10. gmx).
"""
import hw_import as hw


def _markiere(con, schluessel):
    con.execute("insert into verarbeitet values (?,?,?,?)", (schluessel, "Betreff", "2026-10-09T00:30:00", "{}"))
    con.commit()


def test_mail_gilt_nach_kontowechsel_als_verarbeitet(tmp_path):
    con = hw.state_db(tmp_path / "s.db")
    _markiere(con, "vestreporter:abc@kreis.example")
    assert hw.ist_verarbeitet(con, "gmx:abc@kreis.example")
    assert hw.ist_verarbeitet(con, "vestreporter:abc@kreis.example")
    assert not hw.ist_verarbeitet(con, "gmx:andere@kreis.example")


def test_kalender_eingang_bleibt_getrennt(tmp_path):
    """Der Kalender-Eingang hat eigene Regeln (Rückmeldung, Vertrauensstufen) und bleibt außen vor."""
    con = hw.state_db(tmp_path / "s.db")
    _markiere(con, "kalender:abc@redaktion.example")
    assert not hw.ist_verarbeitet(con, "gmx:abc@redaktion.example")
    _markiere(con, "gmx:xyz@redaktion.example")
    assert not hw.ist_verarbeitet(con, "kalender:xyz@redaktion.example")


def test_mail_ohne_message_id_bleibt_je_konto(tmp_path):
    """Ohne Message-ID ist der Schlüssel die interne eM-ID, die je Konto etwas anderes bedeutet."""
    con = hw.state_db(tmp_path / "s.db")
    _markiere(con, "gmx:id-7")
    assert hw.ist_verarbeitet(con, "gmx:id-7")
    assert not hw.ist_verarbeitet(con, "vestreporter:id-7")


def test_kennung_fasst_konten_zusammen():
    """Innerhalb eines Laufs: dieselbe Mail in zwei Konten nur einmal auswerten."""
    assert hw.lauf_kennung("gmx:abc@x.example") == hw.lauf_kennung("vestreporter:abc@x.example")
    assert hw.lauf_kennung("kalender:abc@x.example") != hw.lauf_kennung("gmx:abc@x.example")
    assert hw.lauf_kennung("gmx:id-7") != hw.lauf_kennung("vestreporter:id-7")
