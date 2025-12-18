#!/bin/bash
BASE_DIR="/Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617"
WORK_DIR="$BASE_DIR/_AGENT_WORK/Opus45_20251218_142539"
LOG_FILE="$WORK_DIR/progress.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Signal-Monitor gestartet" >> "$LOG_FILE"

while [ ! -f "$BASE_DIR/_OUTPUT/.ready_for_qa" ]; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Warte auf .ready_for_qa..." >> "$LOG_FILE"
  sleep 300  # Alle 5 Minuten loggen
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ SIGNAL ERHALTEN: .ready_for_qa!" >> "$LOG_FILE"
echo "🚀 QA kann starten!"
