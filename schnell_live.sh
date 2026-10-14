#!/bin/bash
# schnell_live.sh: eine kleine Änderung (Absage, Handeintrag, Korrektur) in etwa einer Minute live bringen.
#
#   ./schnell_live.sh            deploy termine-re (mit Tests), dann in prod update.sh --nur-bauen
#   ./schnell_live.sh --dry-run  nur deploy --dry-run, nichts bauen, nichts pushen
#
# Voraussetzungen: dev steht auf main, die Änderung ist committet und gepusht (prüft deploy).
# In prod muss termine_stand.json existieren (schreibt der nächtliche Lauf um 06:30).
# Kein Abruf der Quellen, kein Signal-Bericht, keine Rückmelde-Mails.
set -u

KI="${KI_ROOT:-$HOME/ki}"
PROD="$KI/prod/termine/re"
LOG="$HOME/Library/Logs/ki/termine/schnell_live.log"
mkdir -p "$(dirname "$LOG")"

case "${1:-}" in
    "") TROCKEN=false ;;
    --dry-run) TROCKEN=true ;;
    *) echo "Unbekannte Option: $1 (erlaubt: --dry-run)"; exit 2 ;;
esac

{
    echo "===== $(date '+%Y-%m-%d %H:%M:%S') schnell_live ${1:-} ====="
    if [ "$TROCKEN" = true ]; then
        "$KI/infra/bin/deploy" termine-re --dry-run
        rc=$?
    else
        "$KI/infra/bin/deploy" termine-re
        rc=$?
        if [ "$rc" -ne 0 ]; then
            echo "FEHLER: deploy Exit $rc, kein Bau"
        else
            cd "$PROD" || exit 1
            ENV_DATEI="$KI/prod/termine/secrets/termine-re.env"
            # shellcheck source=/dev/null
            [ -r "$ENV_DATEI" ] && { set -a; . "$ENV_DATEI"; set +a; }
            export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
            PYTHON="$PROD/.venv/bin/python" /bin/bash update.sh --nur-bauen
            rc=$?
        fi
    fi
    echo "===== Ende schnell_live rc=$rc ====="
    exit "$rc"
} 2>&1 | tee -a "$LOG"
exit "${PIPESTATUS[0]}"
