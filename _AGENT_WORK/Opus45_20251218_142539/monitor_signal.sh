#!/bin/bash
BASE_DIR="/Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617"
LOG_FILE="$BASE_DIR/_AGENT_WORK/Opus45_20251218_142539/progress.log"
SIGNAL_FILE="$BASE_DIR/_OUTPUT/.ready_for_qa"

while true; do
  if [ -f "$SIGNAL_FILE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ SIGNAL ERHALTEN: .ready_for_qa existiert!" >> "$LOG_FILE"
    echo "SIGNAL_RECEIVED" > "$BASE_DIR/_AGENT_WORK/Opus45_20251218_142539/.signal_status"
    exit 0
  fi
  # Log alle 10 Minuten
  sleep 600
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Warte weiter auf .ready_for_qa..." >> "$LOG_FILE"
done
