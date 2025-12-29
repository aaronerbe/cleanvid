#!/bin/bash
# Reset all failed videos so they can be retried in the next scheduled batch job

echo "=========================================="
echo "CLEANVID - RESET FAILED VIDEOS"
echo "=========================================="
echo ""

echo "Resetting all failed videos..."
docker exec cleanvid2 cleanvid reset --filter failed

if [ $? -eq 0 ]; then
    echo "✓ Failed videos reset successfully"
    echo "✓ These videos will be retried in the next scheduled batch job"
else
    echo "✗ Failed to reset videos"
    exit 1
fi
