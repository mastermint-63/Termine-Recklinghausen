#!/bin/bash
# Termine Recklinghausen - Automatische Aktualisierung mit GitHub Push

cd "$(dirname "$0")"
LOGFILE="$(pwd)/launchd.log"
DATUM=$(date +%Y-%m-%d)

echo "=========================================="
echo "Aktualisierung gestartet: $(date)"
echo "=========================================="

# Alte Event-Anzahl aus bestehenden HTML-Dateien auslesen
ALTE_ANZAHL=0
for html in termine_re_*.html; do
    if [ -f "$html" ]; then
        ANZAHL=$(grep -o '<span id="termine-count">[0-9]*</span>' "$html" | grep -o '[0-9]*' | head -1)
        ALTE_ANZAHL=$((ALTE_ANZAHL + ANZAHL))
    fi
done

# Termine abrufen
OUTPUT=$(/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 app.py --no-browser 2>&1)
echo "$OUTPUT"

# Prüfe auf Fehler (Timeouts, Connection-Errors)
FEHLER_COUNT=$(echo "$OUTPUT" | grep -c "Fehler beim Abrufen")

# Neue Event-Anzahl aus Output extrahieren
NEUE_ANZAHL=0
while IFS= read -r line; do
    ANZAHL=$(echo "$line" | grep -o 'Gesamt: [0-9]* Termine' | grep -o '[0-9]*' | head -1)
    if [ -n "$ANZAHL" ]; then
        NEUE_ANZAHL=$((NEUE_ANZAHL + ANZAHL))
    fi
done <<< "$OUTPUT"

# Differenz berechnen
DIFF=$((NEUE_ANZAHL - ALTE_ANZAHL))

# Zu GitHub pushen (nur wenn Änderungen vorhanden)
PUSH_STATUS=""
if git diff --quiet termine_re_*.html 2>/dev/null && [ -z "$(git ls-files -o --exclude-standard termine_re_*.html 2>/dev/null)" ]; then
    echo "Keine Änderungen - kein Push nötig"
    PUSH_STATUS="Keine Änderungen"
else
    echo "Änderungen gefunden - pushe zu GitHub..."
    git add termine_re_*.html index.html 2>/dev/null
    git commit -m "Termine RE aktualisiert $DATUM" 2>&1

    if git push 2>&1; then
        echo "Push erfolgreich!"
        PUSH_STATUS="GitHub aktualisiert"
    else
        echo "Push fehlgeschlagen!"
        PUSH_STATUS="Push fehlgeschlagen!"
    fi
fi

# Benachrichtigungs-Text
if [ $FEHLER_COUNT -gt 0 ]; then
    TITEL="⚠️ Update mit Fehlern"
    TEXT="$NEUE_ANZAHL Termine (${FEHLER_COUNT}× Fehler)"
    SOUND="Basso"
elif [ $DIFF -gt 0 ]; then
    TITEL="✅ Termine RE aktualisiert"
    TEXT="$NEUE_ANZAHL Termine (+${DIFF} neu)"
    SOUND="Glass"
elif [ $DIFF -lt 0 ]; then
    TITEL="✅ Termine RE aktualisiert"
    TEXT="$NEUE_ANZAHL Termine (${DIFF} weniger)"
    SOUND="Glass"
else
    TITEL="✅ Termine RE aktualisiert"
    TEXT="$NEUE_ANZAHL Termine (unverändert)"
    SOUND="Glass"
fi

# Push-Status anhängen
if [ -n "$PUSH_STATUS" ]; then
    TEXT="$TEXT | $PUSH_STATUS"
fi

# Klickbare macOS Benachrichtigung
/opt/homebrew/bin/terminal-notifier \
    -title "$TITEL" \
    -subtitle "Termine Recklinghausen" \
    -message "$TEXT - Klicke zum Log" \
    -sound "$SOUND" \
    -execute "osascript -e 'tell application \"Terminal\" to do script \"tail -30 \\\"$LOGFILE\\\"\"'"

echo ""
echo "Fertig: $(date)"
