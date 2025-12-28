# Time-Based Processing Guide

## Overview

Cleanvid now supports **both** count-based and time-based processing limits, giving you flexible control over overnight processing.

---

## Configuration Options

### In `settings.json`:

```json
{
  "processing": {
    "max_daily_processing": 5,              // Max number of videos per run
    "max_processing_time_minutes": 300,     // Max time in minutes (5 hours)
    "mute_padding_before_ms": 500,
    "mute_padding_after_ms": 500
  }
}
```

### How Limits Work

**Processing stops when EITHER limit is reached:**
- Processed `max_daily_processing` videos, OR
- `max_processing_time_minutes` has elapsed

**Set to `null` to disable:**
```json
"max_processing_time_minutes": null   // No time limit
```

---

## Usage Examples

### Example 1: Overnight Processing (Midnight to 5 AM)

**Goal:** Process as many videos as possible between midnight and 5am (5 hours)

```json
{
  "processing": {
    "max_daily_processing": 1000,           // High number (won't be reached)
    "max_processing_time_minutes": 300      // 5 hours limit
  }
}
```

**Schedule via Synology Task Scheduler:**
```bash
# Run daily at 12:00 AM
docker exec cleanvid cleanvid process
```

**What happens:**
- Starts at midnight
- Processes videos one by one
- Stops at 5:00 AM (or when all videos done)
- Next night, continues with remaining videos

---

### Example 2: Limited Daily Processing

**Goal:** Process only 5 videos per day, no time limit

```json
{
  "processing": {
    "max_daily_processing": 5,
    "max_processing_time_minutes": null     // No time limit
  }
}
```

**What happens:**
- Processes exactly 5 videos
- May take 1 hour or 10 hours depending on video length
- Stops after 5 videos

---

### Example 3: Both Limits (Safer)

**Goal:** Process up to 10 videos OR 2 hours, whichever comes first

```json
{
  "processing": {
    "max_daily_processing": 10,
    "max_processing_time_minutes": 120      // 2 hours
  }
}
```

**What happens:**
- If videos process quickly: stops after 10 videos
- If videos are slow: stops after 2 hours (may be fewer than 10)
- Provides predictable end time

---

## Recommended Setups

### For Large Libraries (500+ movies)

**Nightly processing (midnight to 6 AM):**
```json
{
  "processing": {
    "max_daily_processing": 9999,
    "max_processing_time_minutes": 360      // 6 hours
  }
}
```

Synology Task Scheduler:
```
Schedule: Daily at 00:00
User: root
Command: docker exec cleanvid cleanvid process
```

**Result:** Processes ~20-40 videos per night (depending on length)

---

### For Small Libraries (< 100 movies)

**Quick daily processing:**
```json
{
  "processing": {
    "max_daily_processing": 5,
    "max_processing_time_minutes": 60       // 1 hour safety limit
  }
}
```

**Result:** Processes 5 videos/day, done in <1 hour

---

### For Testing

**Process just a few videos quickly:**
```json
{
  "processing": {
    "max_daily_processing": 2,
    "max_processing_time_minutes": 30
  }
}
```

---

## Python API Usage

### Time-based processing:
```python
from cleanvid.services import Processor

processor = Processor()

# Process for up to 5 hours
stats = processor.process_batch(
    max_time_minutes=300,    # 5 hours
    max_videos=9999          # Effectively unlimited
)
```

### Count-based processing:
```python
# Process up to 10 videos (no time limit)
stats = processor.process_batch(
    max_videos=10,
    max_time_minutes=None
)
```

### Both limits:
```python
# Process up to 20 videos OR 2 hours
stats = processor.process_batch(
    max_videos=20,
    max_time_minutes=120
)
```

---

## Processing Time Estimates

**With copy mode (default, fast):**
- 1080p movie (2 hours): ~3-4 minutes processing
- 4K movie (2 hours): ~4-6 minutes processing

**5 hour window can process:**
- ~60-100 1080p movies
- ~50-75 4K movies

**Your 500-movie library:**
- Full processing: ~5-10 nightly runs
- Complete in: **1-2 weeks**

---

## Output Examples

### Time limit reached:
```
[1/100] Processing: movie1.mkv
✓ Successfully processed (12.3 minutes)

[2/100] Processing: movie2.mkv
✓ Successfully processed (10.1 minutes)

...

[23/100] Processing: movie23.mkv

⏱️  Time limit reached (300.2/300 minutes)
Stopping batch processing. Processed 22/100 videos.

Batch Processing Complete
Total videos found: 22
Successfully processed: 22
Time taken: 5.0 hours
```

### Count limit reached:
```
[1/5] Processing: movie1.mkv
✓ Successfully processed

...

[5/5] Processing: movie5.mkv
✓ Successfully processed

Batch Processing Complete
Total videos found: 5
Successfully processed: 5
Time taken: 1.2 hours
```

---

## Tips

1. **Start conservative:** Use 2-3 hour limit first to test
2. **Monitor logs:** Check processing times to optimize
3. **Adjust based on results:** If finishing early, increase time
4. **Consider file size:** 4K movies take longer
5. **Use both limits:** Provides safety and predictability

---

## FAQ

**Q: What if I want to process all videos in one run?**
```json
{
  "max_daily_processing": 99999,
  "max_processing_time_minutes": null
}
```

**Q: Can I override config from command line?**
Yes, when CLI is added:
```bash
cleanvid process --max-time 300 --max-videos 9999
```

**Q: What happens to partially processed videos?**
If time limit is hit mid-video, that video is NOT marked as processed.
It will be retried next run.

**Q: How do I see what was processed?**
```python
processor.get_recent_history(limit=50)
```

Or check: `/config/processed_log.json`

---

**Your setup:** Schedule at midnight with 5-hour time limit → Process entire library in 1-2 weeks! 🚀
