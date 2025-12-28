#!/bin/bash
# Cleanvid Monitoring Dashboard
# Shows current status, activity, and recent logs

echo "========================================"
echo "CLEANVID MONITORING DASHBOARD"
echo "========================================"
echo ""

# Container Status
echo "📦 CONTAINER STATUS:"
echo "--------------------"
docker ps --filter "name=cleanvid" --format "table {{.Names}}\t{{.Status}}\t{{.Size}}" 2>/dev/null || echo "Container not running"
echo ""

# Current Processing
echo "⚙️  CURRENT ACTIVITY:"
echo "--------------------"
FFMPEG_RUNNING=$(docker exec cleanvid ps aux 2>/dev/null | grep ffmpeg | grep -v grep)
if [ -n "$FFMPEG_RUNNING" ]; then
    echo "✓ Processing video (FFmpeg running)"
    docker exec cleanvid ps aux | grep ffmpeg | grep -v grep | awk '{print "  PID: " $2 " | CPU: " $3"% | Mem: " $4"%"}'
else
    echo "○ Idle (no active processing)"
fi
echo ""

# Statistics
echo "📊 STATISTICS:"
echo "--------------------"
docker exec cleanvid cleanvid status 2>/dev/null | grep -A 20 "Videos:" | head -10
echo ""

# Recent Activity
echo "📋 RECENT ACTIVITY (Last 10):"
echo "--------------------"
docker exec cleanvid cleanvid history --limit 10 2>/dev/null | tail -20
echo ""

# Recent Logs
echo "📝 RECENT LOGS (Last 15 lines):"
echo "--------------------"
tail -15 /volume1/docker/cleanvid/logs/cleanvid.log 2>/dev/null || echo "No logs available"
echo ""

echo "========================================"
echo "Use 'cleanvid-logs' to follow live logs"
echo "Use 'pv \"movie\"' to process a video"
echo "========================================"
