#!/bin/bash
# Process Video - Easy wrapper for cleanvid
# Usage: ./process_video.sh "movie name"
# Example: ./process_video.sh "Hostiles"

# Check if search term provided
if [ -z "$1" ]; then
    echo "Usage: ./process_video.sh \"movie name\""
    echo "Example: ./process_video.sh \"Hostiles\""
    exit 1
fi

SEARCH="$1"

echo "Searching for: $SEARCH"
echo ""

# Find the video (case insensitive)
VIDEO=$(find /volume1/Videos -iname "*$SEARCH*" -type f \( -name "*.mp4" -o -name "*.mkv" -o -name "*.avi" -o -name "*.m4v" \) 2>/dev/null | head -1)

if [ -z "$VIDEO" ]; then
    echo "❌ Video not found: $SEARCH"
    echo ""
    echo "Tip: Try a shorter search term"
    echo "Example: Instead of 'Hostiles 2017', try just 'Hostiles'"
    exit 1
fi

echo "✓ Found: $VIDEO"
echo ""

# Convert path from /volume1/Videos to /input
DOCKER_PATH=$(echo "$VIDEO" | sed 's|/volume1/Videos|/input|')

echo "Processing: $(basename "$VIDEO")"
echo "------------------------------------------------------------"
echo ""

# Reset if already processed (ignore errors if not processed)
docker exec cleanvid cleanvid reset "$DOCKER_PATH" 2>/dev/null

# Process the video
docker exec cleanvid cleanvid process "$DOCKER_PATH"

exit $?
