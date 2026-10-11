#!/bin/bash
# HW-Import: Kalender-Eingang (IMAP), "HW"-markierte Mails und Presse-PMs in den Kalender übernehmen.
# Läuft nachts (00:30) per launchd, VOR dem Kalender-Lauf (06:30, update.sh), der veröffentlicht.
cd "$(dirname "$0")" || exit 1
echo "=========================================="
echo "HW-Import gestartet: $(date)"
"${PYTHON:-python3}" hw_import.py
RC=$?
echo "HW-Import beendet: $(date), Exit-Code $RC"
exit $RC
