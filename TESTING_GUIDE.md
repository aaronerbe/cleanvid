# Scene Editor - Testing & Verification Guide

## Step 1: Restart Docker
```bash
docker restart cleanvid2
```

## Step 2: Check scene_filters.json File

### Via Docker exec:
```bash
docker exec cleanvid2 cat /config/scene_filters.json
```

### Expected content:
```json
{
  "/volume1/video/jellyfin/Movies/YourMovie.mkv": {
    "video_path": "/volume1/video/jellyfin/Movies/YourMovie.mkv",
    "title": "",
    "skip_zones": [
      {
        "id": "some-uuid",
        "start_time": 123.5,
        "end_time": 145.0,
        "start_display": "02:03",
        "end_display": "02:25",
        "description": "Scene to blur",
        "mode": "blur",
        "mute": false
      }
    ],
    "last_modified": "2026-01-01T..."
  }
}
```

## Step 3: Process a Test Video

### From Scene Editor:
1. Select your test video
2. Click "Save & Process Now"

### Watch Docker Logs:
```bash
docker logs -f cleanvid2
```

## Step 4: Look for Debug Output

### Expected log output (with verbose debugging):

```
Processing: YourMovie.mkv
------------------------------------------------------------
  🔍 DEBUG: Checking for scene filters...
  🔍 DEBUG: config_dir = /config
  🔍 DEBUG: config_dir exists, attempting to load scene filters
  🔍 DEBUG: Looking for filters for video: /volume1/video/jellyfin/Movies/YourMovie.mkv
  🔍 DEBUG: video_filters = <VideoSceneFilters object>
  ✅ Found 2 scene skip zone(s)
  🔍 DEBUG: Skip zones: [{'desc': 'Scene 1', 'mode': 'skip', 'start': 60.0, 'end': 75.0}, ...]
  🔍 DEBUG: Blur zones: 1, Black zones: 0, Mute zones: 0
  ✅ Applying video filters: 1 blur, 0 black
  🔍 DEBUG: Generated filter: boxblur=20:20:enable='between(t,123.5,145.0)'
  Running FFmpeg with scene filters...
  🔍 DEBUG: Video filter with labels: [0:v]boxblur=20:20:enable='between(t,123.5,145.0)'[v]
  🔍 DEBUG: Full FFmpeg command:
  ffmpeg -i /volume1/video/jellyfin/Movies/YourMovie.mkv -threads 2 -filter_complex [0:v]boxblur=20:20:enable='between(t,123.5,145.0)'[v] -map [v] -map 0:a -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 192k -y /volume1/video/jellyfin-clean/Movies/YourMovie.mkv
```

## Step 5: Diagnostic Scenarios

### Scenario A: config_dir is None
```
  ℹ️  config_dir is None, skipping scene filter loading
```
**Problem:** Processor not passing config_dir to VideoProcessor
**Fix:** Already applied in processor.py line 56

### Scenario B: No scene filters found
```
  🔍 DEBUG: video_filters = None
  ℹ️  No scene filters found for this video
```
**Problem:** Video path mismatch or scene_filters.json doesn't exist
**Check:** Verify exact video path in JSON matches processing path

### Scenario C: Scene filters loaded but no blur/black zones
```
  ✅ Found 2 scene skip zone(s)
  🔍 DEBUG: Blur zones: 0, Black zones: 0, Mute zones: 2
```
**Expected:** Only mode="skip" zones, profanity muting will still work

### Scenario D: FFmpeg error
```
  FFmpeg error: [last 500 chars of stderr]
```
**Check:** FFmpeg filter syntax, video codec compatibility

## Step 6: Verify Output

### Check processing result in dashboard:
- Recent Activity should show scene_zones_processed count
- Purple text showing "Scene zones: X"

### Play the output video:
- Navigate to timestamp where blur/black should occur
- Verify visual effect is applied
- Check profanity muting still works

## Step 7: Manual FFmpeg Test (if needed)

### Test blur filter directly:
```bash
ffmpeg -i input.mkv -ss 123 -t 22 \
  -filter_complex '[0:v]boxblur=20:20:enable=between(t,123.5,145.0)[v]' \
  -map '[v]' -map 0:a \
  -c:v libx264 -preset medium -crf 23 \
  -c:a copy \
  test_blur.mkv
```

### Test black filter directly:
```bash
ffmpeg -i input.mkv -ss 123 -t 22 \
  -filter_complex '[0:v]drawbox=c=black@1:t=fill:enable=between(t,123.5,145.0)[v]' \
  -map '[v]' -map 0:a \
  -c:v libx264 -preset medium -crf 23 \
  -c:a copy \
  test_black.mkv
```

## Common Issues & Solutions

### Issue: "config_dir is None"
**Solution:** Already fixed - processor.py now passes config_dir

### Issue: "No scene filters found"
**Cause:** Video path mismatch
**Solution:** Check exact path in scene_filters.json vs. what's being processed

### Issue: "video_filters.zone_count"
**Solution:** Already fixed - changed to len(video_filters.skip_zones)

### Issue: "get_mute_time_ranges"
**Solution:** Already fixed - changed to get_mute_segments()

### Issue: FFmpeg filter syntax error
**Cause:** Missing [0:v] prefix or [v] output label
**Solution:** Already fixed - filter_with_labels wraps the filter

## Expected Behavior

### Skip mode (mode="skip"):
- No video modification
- Only profanity muting applies

### Blur mode (mode="blur"):
- Gaussian blur applied during timestamp range
- Video must be re-encoded (slower processing)
- Optional audio muting with mute=true

### Black mode (mode="black"):
- Black box covers entire frame during timestamp range
- Video must be re-encoded (slower processing)
- Optional audio muting with mute=true

## Final Checklist

- [ ] Docker restarted with latest code
- [ ] scene_filters.json exists and contains correct data
- [ ] Video path in JSON matches exactly
- [ ] Debug logs show config_dir is set
- [ ] Debug logs show scene filters loaded
- [ ] Debug logs show FFmpeg command with filters
- [ ] Output video has blur/black effect at correct timestamps
- [ ] Dashboard shows scene_zones_processed count
- [ ] Profanity muting still works
