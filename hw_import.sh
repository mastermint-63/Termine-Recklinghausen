#!/bin/bash
# HW-Import: mit "HW" markierte Mails aus eM Client in den Kalender übernehmen.
# Läuft nachts (05:30) per launchd, VOR dem Kalender-Lauf (06:30, update.sh), der veröffentlicht.
cd "$(dirname "$0")" || exit 1
echo "=========================================="
echo "HW-Import gestartet: $(date)"
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 hw_import.py
RC=$?
echo "HW-Import beendet: $(date), Exit-Code $RC"
exit $RC
