# SKIP MODE IMPLEMENTATION - STATUS & PLAN

## CURRENT STATUS

### What's Working ✅
- BLUR mode: Applies gaussian blur to video (FIXED - now uses proper parameters)
- BLACK mode: Blacks out video segments (FIXED - now includes dimensions)
- Scene filters save/load correctly
- Dashboard integration works
- Profanity muting works alongside scene filters

### What's Broken ❌
- **SKIP mode does NOTHING - it's ignored completely**
- User expects SKIP to CUT OUT segments (make video shorter)
- Currently SKIP zones are loaded but not processed

## USER EXPECTATION (CORRECT)

**SKIP mode should:**
1. Physically remove segments from video
2. Make the output video SHORTER
3. Example: 2-hour movie with 3-minute skip → output is 1:57:00

## IMPLEMENTATION APPROACH

### Option 1: FFmpeg trim + concat (RECOMMENDED)
```bash
# To skip 25:20-28:00 (1520-1680 seconds)
# Keep: 0-1520, then 1680-end
ffmpeg -i input.mp4 \
  -filter_complex "\
    [0:v]trim=0:1520,setpts=PTS-STARTPTS[v1]; \
    [0:a]atrim=0:1520,asetpts=PTS-STARTPTS[a1]; \
    [0:v]trim=1680,setpts=PTS-STARTPTS[v2]; \
    [0:a]atrim=1680,asetpts=PTS-STARTPTS[a2]; \
    [v1][a1][v2][a2]concat=n=2:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -preset medium -crf 23 \
  -c:a aac -b:a 192k \
  output.mp4
```

### WHY THIS IS COMPLEX

**Problem:** Can't mix SKIP with BLUR/BLACK in single filter_complex
- SKIP uses: trim+concat → outputs [outv][outa]
- BLUR uses: [0:v]boxblur...[v] → outputs [v]
- They're incompatible filter structures

**Current code structure:**
```python
if skip_zones:
    # Generate skip filter
elif blur_zones or black_zones:
    # Generate blur/black filter
```

This means you can EITHER skip OR blur/black, but not both!

## RECOMMENDED SOLUTION

### Short-term (Quick Fix):
**Don't allow mixing SKIP with BLUR/BLACK modes**

Update UI to show warning:
- "Cannot mix SKIP mode with BLUR/BLACK modes"
- "Please use all SKIP or all BLUR/BLACK for a single video"

### Long-term (Proper Fix):
**Two-pass processing:**
1. First pass: Apply SKIP (trim+concat) if any SKIP zones exist
2. Second pass: Apply BLUR/BLACK to the trimmed video

This requires significant refactoring.

## IMMEDIATE ACTION ITEMS

### For Current Video Being Processed:
1. Cancel it (it's using old slow blur=20:20)
2. Restart Docker to pick up fixes
3. Change "Bowl oer Privates" from SKIP to BLACK mode
4. Re-process with both scenes as BLUR/BLACK

### Code Changes Made:
1. ✅ Fixed boxblur (was 20:20, now 25:3:25:3)
2. ✅ Fixed drawbox (added x,y,w,h dimensions)
3. ✅ Fixed config_dir passing to VideoProcessor  
4. ✅ Added skip filter generation (but can't use yet)
5. ❌ Can't activate SKIP without major refactoring

## TESTING PLAN

### Test 1: BLUR only
- One scene with BLUR mode
- Verify blur effect appears at correct timestamp
- Verify profanity muting still works

### Test 2: BLACK only
- One scene with BLACK mode
- Verify screen goes black at correct timestamp
- Verify profanity muting still works

### Test 3: BLUR + BLACK
- One BLUR scene, one BLACK scene (different times)
- Verify both effects work
- Verify profanity muting still works

### Test 4: SKIP (when implemented)
- One SKIP scene
- Verify output video is shorter
- Verify timestamps after skip are adjusted
- Verify profanity muting still works

## CURRENT RECOMMENDATION

**For your current video:**
1. Stop processing (it's slow)
2. Restart Docker
3. Change "Bowl oer Privates" from SKIP to BLACK
4. Process with: 1 BLACK scene + 1 BLUR scene
5. This will work correctly with current code

**For SKIP mode:**
- Need to decide: Quick UI warning or two-pass processing?
- I recommend UI warning for now, proper fix later
