#!/bin/bash
# Remove all failed entries from processed_log.json
# This allows the next scheduled batch job to retry those videos

echo "=========================================="
echo "CLEANVID - RESET FAILED VIDEOS"
echo "=========================================="
echo ""

CONFIG_FILE="/config/processed_log.json"
BACKUP_FILE="/config/processed_log.json.backup.$(date +%Y%m%d_%H%M%S)"

echo "Creating backup..."
docker exec cleanvid2 cp "$CONFIG_FILE" "$BACKUP_FILE"

echo "Removing failed entries..."
docker exec cleanvid2 python3 -c "
import json
import sys

try:
    with open('$CONFIG_FILE', 'r') as f:
        data = json.load(f)
    
    failed_count = sum(1 for entry in data if not entry.get('success', True))
    successful = [entry for entry in data if entry.get('success', True)]
    
    with open('$CONFIG_FILE', 'w') as f:
        json.dump(successful, f, indent=2)
    
    print(f'✓ Removed {failed_count} failed entries')
    print(f'✓ Kept {len(successful)} successful entries')
    print(f'✓ Backup saved: $BACKUP_FILE')
    print(f'')
    print(f'These videos will be retried in the next scheduled batch job')
except Exception as e:
    print(f'✗ Error: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "SUCCESS"
    echo "=========================================="
else
    echo ""
    echo "=========================================="
    echo "FAILED - Check error message above"
    echo "=========================================="
    exit 1
fi
