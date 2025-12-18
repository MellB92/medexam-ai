#!/bin/bash
# Composer2 Monitoring Script
set -euo pipefail

BASE_DIR="/Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617"
SIGNAL_FILE="$BASE_DIR/_OUTPUT/.ready_for_documentation_update"
CHECK_INTERVAL=30

echo "=== Composer2 Signal Monitor ==="
echo "Signal: .ready_for_documentation_update"
echo "Check Interval: ${CHECK_INTERVAL} Sekunden"
echo "Start: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

check_count=0
while [ ! -f "$SIGNAL_FILE" ]; do
  check_count=$((check_count + 1))
  timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  echo "[$timestamp] Check #$check_count - Waiting..."
  sleep $CHECK_INTERVAL
done

timestamp=$(date '+%Y-%m-%d %H:%M:%S')
echo ""
echo "✅✅✅ SIGNAL ERHALTEN! ✅✅✅"
echo "Signal gefunden um: $timestamp"
echo "Starte Dokumentationsaktualisierung..."
