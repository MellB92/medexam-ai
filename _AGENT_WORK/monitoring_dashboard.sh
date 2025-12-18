#!/bin/bash
BASE_DIR="/Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617/_AGENT_WORK"
echo "🤖 AGENT MONITORING DASHBOARD"
echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
while IFS=: read -r agent_name work_dir; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Agent: $agent_name ($work_dir)"
    if [ -f "$BASE_DIR/$work_dir/progress.log" ]; then
        echo "Recent:"
        tail -2 "$BASE_DIR/$work_dir/progress.log"
    fi
    echo ""
done < ACTIVE_AGENTS.txt
