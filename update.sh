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
PYTHON_EXIT=$?
echo "$OUTPUT"

if [ $PYTHON_EXIT -ne 0 ]; then
    echo "FEHLER: app.py mit Exit-Code $PYTHON_EXIT abgebrochen – kein Push"
    /opt/homebrew/bin/terminal-notifier \
        -title "❌ Termine RE – Skriptfehler" \
        -subtitle "Termine Recklinghausen" \
        -message "app.py Exit-Code $PYTHON_EXIT – kein Push" \
        -sound "Basso"
    exit 1
fi

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

# Alte Monatsdateien aufräumen (Puffer: Vormonat bleibt, alles davor wird gelöscht)
CUTOFF_JAHR=$(date +%Y)
CUTOFF_MONAT=$(date +%-m)
if [ "$CUTOFF_MONAT" -eq 1 ]; then
    CUTOFF_JAHR=$((CUTOFF_JAHR - 1))
    CUTOFF_MONAT=12
else
    CUTOFF_MONAT=$((CUTOFF_MONAT - 1))
fi
CUTOFF=$(printf "%04d_%02d" "$CUTOFF_JAHR" "$CUTOFF_MONAT")
GELOESCHT=()
for html in termine_re_*.html; do
    [ -f "$html" ] || continue
    DATEI_KEY=$(echo "$html" | grep -o '[0-9]\{4\}_[0-9]\{2\}')
    if [[ "$DATEI_KEY" < "$CUTOFF" ]]; then
        echo "Lösche veraltete Datei: $html (älter als Vormonat)"
        git rm "$html" 2>/dev/null && GELOESCHT+=("$html")
    fi
done

# Zu GitHub pushen (nur wenn Änderungen vorhanden)
PUSH_STATUS=""
HAT_AENDERUNGEN=false
git diff --quiet termine_re_*.html 2>/dev/null || HAT_AENDERUNGEN=true
[ -n "$(git ls-files -o --exclude-standard termine_re_*.html 2>/dev/null)" ] && HAT_AENDERUNGEN=true
git diff --cached --quiet 2>/dev/null || HAT_AENDERUNGEN=true

if [ "$HAT_AENDERUNGEN" = false ]; then
    echo "Keine Änderungen - kein Push nötig"
    PUSH_STATUS="Keine Änderungen"
else
    echo "Änderungen gefunden - pushe zu GitHub..."
    git add termine_re_*.html index.html 2>/dev/null
    COMMIT_MSG="Termine RE aktualisiert $DATUM"
    [ ${#GELOESCHT[@]} -gt 0 ] && COMMIT_MSG="$COMMIT_MSG (${#GELOESCHT[@]} alte Datei(en) gelöscht)"
    git commit -m "$COMMIT_MSG" 2>&1

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

# Gelöschte Dateien anhängen
if [ ${#GELOESCHT[@]} -gt 0 ]; then
    TEXT="$TEXT | 🗑 ${#GELOESCHT[@]} alte Datei(en) gelöscht"
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
