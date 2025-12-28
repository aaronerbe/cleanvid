# Cleanvid User Guide

Complete guide to using Cleanvid for automated movie profanity filtering.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Configuration](#configuration)
3. [Processing Videos](#processing-videos)
4. [Monitoring Progress](#monitoring-progress)
5. [Common Workflows](#common-workflows)
6. [Tips & Best Practices](#tips--best-practices)
7. [FAQ](#faq)

---

## Getting Started

### First-Time Setup

#### Docker (Recommended)

```bash
# 1. Initialize configuration
docker run --rm -v /volume1/docker/cleanvid/config:/config cleanvid init

# 2. Edit settings
nano /volume1/docker/cleanvid/config/settings.json

# 3. Edit word list
nano /volume1/docker/cleanvid/config/profanity_words.txt

# 4. Test with one video
docker exec cleanvid cleanvid process --max-videos 1

# 5. Check status
docker exec cleanvid cleanvid status
```

#### Python Installation

```bash
# 1. Install
pip install -e .

# 2. Initialize
cleanvid init

# 3. Edit configuration
nano ~/.config/cleanvid/settings.json

# 4. Test
cleanvid process --max-videos 1

# 5. Check status
cleanvid status
```

---

## Configuration

### Essential Settings

#### settings.json

**Location:** `/config/settings.json` (Docker) or `~/.config/cleanvid/settings.json` (Python)

```json
{
  "processing": {
    "max_daily_processing": 9999,
    "max_processing_time_minutes": 300,
    "video_extensions": [".mkv", ".mp4", ".avi"],
    "mute_padding_before_ms": 500,
    "mute_padding_after_ms": 500
  },
  "paths": {
    "input_dir": "/volume1/movies/original",
    "output_dir": "/volume1/movies/filtered",
    "config_dir": "/config",
    "logs_dir": "/logs"
  },
  "opensubtitles": {
    "enabled": true,
    "language": "en",
    "username": "your_username",
    "password": "your_password"
  },
  "ffmpeg": {
    "threads": 2,
    "audio_codec": "aac",
    "audio_bitrate": "192k",
    "re_encode_video": false
  }
}
```

#### Key Settings Explained

**Processing:**
- `max_daily_processing`: Maximum videos per run (9999 = effectively unlimited)
- `max_processing_time_minutes`: Time limit in minutes (300 = 5 hours)
- `mute_padding_before_ms`: Start muting N milliseconds before profanity
- `mute_padding_after_ms`: Continue muting N milliseconds after profanity

**Paths:**
- `input_dir`: Where original movies are stored (read-only)
- `output_dir`: Where filtered movies are saved
- `config_dir`: Configuration files location
- `logs_dir`: Log files location

**OpenSubtitles:**
- `enabled`: Auto-download subtitles if not found
- `language`: Subtitle language (en, es, fr, etc.)
- `username/password`: OpenSubtitles.org credentials

**FFmpeg:**
- `threads`: CPU cores to use (2-4 recommended)
- `audio_codec`: Audio codec for output (aac recommended)
- `re_encode_video`: false = fast copy, true = re-encode

### Word List Configuration

**Location:** `/config/profanity_words.txt`

```text
# Lines starting with # are comments
# One word per line
# Use * as wildcard

# Mild
damn
hell
crap

# Moderate  
shit
ass
b*tch

# Strong
f*ck
f**k
```

**Wildcard Examples:**
- `f*ck` matches: fuck, feck, fack, f**k
- `sh*t` matches: shit, shot, shat
- `b*tch` matches: bitch, batch (careful!)

**Tips:**
- Start conservative, add words as needed
- Use wildcards for variations
- Test with sample videos first
- Consider context (batch vs bitch)

---

## Processing Videos

### Basic Commands

#### Process Batch (Default Limits)

```bash
cleanvid process
```

Respects `max_daily_processing` and `max_processing_time_minutes` from config.

#### Process with Time Limit

```bash
# Process for 5 hours
cleanvid process --max-time 300

# Process for 2 hours
cleanvid process --max-time 120
```

#### Process with Video Limit

```bash
# Process exactly 10 videos
cleanvid process --max-videos 10
```

#### Process Single Video

```bash
cleanvid process /input/Action/Die\ Hard.mkv
```

#### Force Reprocess

```bash
# Reprocess all videos (ignores processed log)
cleanvid process --force

# Reprocess up to 5 videos
cleanvid process --force --max-videos 5
```

### Processing Output

```
============================================================
Starting batch processing of 100 videos
Time limit: 300 minutes
============================================================

[1/100] Processing: Die Hard.mkv
------------------------------------------------------------
Finding subtitles...
✓ Found subtitle: Die Hard.srt
Detecting profanity...
✓ Found 15 instances
Generating mute segments...
✓ Created 15 segments
Processing video...
✓ Successfully processed
  Segments muted: 15
  Processing time: 3.2 minutes

[2/100] Processing: The Matrix.mkv
------------------------------------------------------------
...

⏱️  Time limit reached (300.1/300 minutes)
Stopping batch processing. Processed 78/100 videos.

============================================================
Batch Processing Complete
============================================================

Total videos found: 78
Successfully processed: 78
Failed: 0
Success rate: 100.0%
Total segments muted: 1,234
Time taken: 5.0 hours
```

---

## Monitoring Progress

### Check Status

```bash
cleanvid status
```

Output:
```
Configuration: ✓ Valid
FFmpeg: ✓ Available (ffmpeg version 4.4.1)

Videos:
  Total: 500
  Processed: 78
  Unprocessed: 422

Library Size:
  Total: 2.3 TB
  Unprocessed: 1.9 TB

Profanity Words: 25
OpenSubtitles: Enabled

Processing Limits:
  Max videos per run: 9999
  Max time per run: 300 minutes (5.0 hours)
```

### View History

```bash
# Last 20 entries
cleanvid history

# Last 50 entries
cleanvid history --limit 50
```

Output:
```
================================================================================
Processing History (Most Recent 20)
================================================================================

✓ 2025-11-28 23:45:12 | SUCCESS | Die Hard.mkv
  Segments muted: 15

✓ 2025-11-28 23:38:24 | SUCCESS | The Matrix.mkv
  Segments muted: 8

✗ 2025-11-28 23:32:15 | FAILED  | Bad Movie.mkv
  Error: No subtitle found

...
```

### Check Logs

**Docker:**
```bash
# Container logs
docker logs -f cleanvid

# Application logs
cat /volume1/docker/cleanvid/logs/cleanvid.log
tail -f /volume1/docker/cleanvid/logs/cleanvid.log
```

**Python:**
```bash
cat ~/.config/cleanvid/logs/cleanvid.log
tail -f ~/.config/cleanvid/logs/cleanvid.log
```

---

## Common Workflows

### Workflow 1: Initial Library Processing

**Goal:** Process 500-movie library over 1 week

**Configuration:**
```json
{
  "processing": {
    "max_daily_processing": 9999,
    "max_processing_time_minutes": 300
  }
}
```

**Schedule:** Daily at midnight

**Timeline:**
- Night 1: Process ~75 movies (0 → 75)
- Night 2: Process ~75 movies (75 → 150)
- ...
- Night 7: Process ~75 movies (425 → 500)

**Commands:**
```bash
# Test first
cleanvid process --max-videos 1

# Then schedule
# DSM Task Scheduler: docker exec cleanvid cleanvid process
```

### Workflow 2: Ongoing Maintenance

**Goal:** Process new movies as added (5-10 per week)

**Configuration:**
```json
{
  "processing": {
    "max_daily_processing": 10,
    "max_processing_time_minutes": 60
  }
}
```

**Schedule:** Daily at 2 AM

**Result:** Automatically processes new movies within 24 hours

### Workflow 3: Weekend Batch

**Goal:** Process during weekends only

**Configuration:**
```json
{
  "processing": {
    "max_daily_processing": 9999,
    "max_processing_time_minutes": 720
  }
}
```

**Schedule:** Saturday/Sunday at midnight

**Result:** 12 hours processing each weekend day

### Workflow 4: Quality Control

**Goal:** Review and reprocess specific movies

**Steps:**
```bash
# 1. Check what was processed
cleanvid history --limit 50

# 2. Reset specific movie
cleanvid reset /input/movie.mkv

# 3. Edit word list (add/remove words)
nano /config/profanity_words.txt

# 4. Reprocess
cleanvid process /input/movie.mkv

# 5. Verify
cleanvid history --limit 5
```

---

## Tips & Best Practices

### Performance Optimization

**Fast Processing (Copy Mode):**
```json
{
  "ffmpeg": {
    "threads": 4,
    "re_encode_video": false
  }
}
```
- Speed: ~1.5x realtime
- Quality: Perfect (bit-for-bit video copy)
- Size: Same as input

**Small Files (Re-encode Mode):**
```json
{
  "ffmpeg": {
    "threads": 2,
    "re_encode_video": true,
    "video_codec": "libx265",
    "video_crf": 23
  }
}
```
- Speed: ~7.5x realtime (slower)
- Quality: Excellent (CRF 23)
- Size: 20-50% smaller

### Subtitle Tips

**If subtitles not found:**
1. Check subtitle file is next to video (.srt extension)
2. Enable OpenSubtitles auto-download
3. Manually download SRT and place next to video
4. Use subliminal CLI to fetch: `subliminal download -l en movie.mkv`

**Best practices:**
- Keep subtitles in same directory as videos
- Use .srt format (most compatible)
- Name subtitle same as video (movie.mkv → movie.srt)

### Word List Tuning

**Start Conservative:**
```text
# Strong words only
f*ck
shit
```

**Expand Gradually:**
```text
# Add medium after testing
damn
hell
ass
```

**Consider Context:**
- "ass" catches "assembly" and "glass"
- "hell" catches "hello" and "shell"
- Use wildcards carefully!

**Test Before Batch:**
```bash
# Test on one movie
cleanvid process --max-videos 1

# Watch result
# Adjust word list
# Repeat
```

### Resource Management

**For Small NAS (2-4 GB RAM):**
```json
{
  "ffmpeg": {
    "threads": 2
  },
  "processing": {
    "max_processing_time_minutes": 180
  }
}
```

**For Powerful NAS (8+ GB RAM):**
```json
{
  "ffmpeg": {
    "threads": 4
  },
  "processing": {
    "max_processing_time_minutes": 480
  }
}
```

### Backup Strategy

**Before bulk processing:**
```bash
# Backup configuration
tar -czf cleanvid-config-backup.tar.gz /config/

# Backup processed log
cp /config/processed_log.json /config/processed_log.json.backup
```

**After processing:**
- Test filtered videos on multiple devices
- Keep originals for 30 days minimum
- Back up processed_log.json regularly

---

## FAQ

### General Questions

**Q: Will this work with Roku/Jellyfin?**  
A: Yes! Cleanvid creates standard video files that work on any device.

**Q: Are original files modified?**  
A: No. Originals remain untouched. Filtered versions saved to output_dir.

**Q: What if I don't like the result?**  
A: Delete filtered version, adjust word list, reset and reprocess.

**Q: Can I use both Plex and Jellyfin?**  
A: Yes. Point Plex at input_dir (originals) and Jellyfin at output_dir (filtered).

### Processing Questions

**Q: How long does processing take?**  
A: Copy mode: ~3-4 minutes per 2-hour 1080p movie (~1.5x realtime)

**Q: Can I pause/resume processing?**  
A: Yes. Stop container/process. Next run continues where it left off.

**Q: What if processing fails mid-video?**  
A: Video is NOT marked as processed. Will retry on next run.

**Q: Can I process while watching?**  
A: Yes, but may cause playback stuttering. Best to process overnight.

### Configuration Questions

**Q: Where is configuration stored?**  
A: Docker: `/volume1/docker/cleanvid/config/`  
   Python: `~/.config/cleanvid/`

**Q: How do I edit word list?**  
A: Edit `/config/profanity_words.txt` directly. Changes apply immediately.

**Q: Can I have multiple word lists?**  
A: Currently one list. Create multiple configs for different profiles.

### Technical Questions

**Q: Does this require re-encoding?**  
A: No (by default). Uses fast copy mode with audio track replacement only.

**Q: What codecs are supported?**  
A: All FFmpeg-supported formats. MKV, MP4, AVI, MOV, M4V tested.

**Q: Can I process 4K/HDR?**  
A: Yes. HDR metadata preserved in copy mode.

**Q: What about multi-audio tracks?**  
A: Currently processes first audio track only. Others copied as-is.

### Troubleshooting

**Q: "FFmpeg not found" error?**  
A: Install FFmpeg or use Docker image (includes FFmpeg).

**Q: "No subtitle found" error?**  
A: Enable OpenSubtitles or manually place .srt file next to video.

**Q: "Permission denied" error?**  
A: Check directory permissions. Docker needs write access to output_dir.

**Q: Processing is slow?**  
A: Increase threads, ensure SSD not HDD, check CPU usage.

**Q: Files are huge?**  
A: Use re-encode mode with libx265 to reduce size.

---

## Getting Help

**Check documentation:**
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Docker Deployment](DOCKER_DEPLOYMENT.md)
- [Time-Based Processing](TIME_BASED_PROCESSING.md)

**Enable debug logging:**
```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

**Collect information:**
```bash
cleanvid status
cleanvid config --validate
cleanvid history --limit 10
docker logs cleanvid
```

**Report issue:**
- Include cleanvid version
- Include error messages
- Include relevant logs
- Describe expected vs actual behavior

---

**Happy filtering! 🎬**
