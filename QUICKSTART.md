# Cleanvid - Quick Start Guide

---

## 🚀 QUICK REFERENCE COMMANDS

### **Common Operations**

```bash
# Check system status
sudo docker exec cleanvid cleanvid status

# Process a specific video manually
sudo docker exec cleanvid cleanvid process "/input/Action/Movie Name/Movie.Name.2024.mkv"

# Reset a video to reprocess it (after adding subtitle or fixing issues)
sudo docker exec cleanvid cleanvid reset "/input/Action/Movie Name/Movie.Name.2024.mkv"

# Process 10 videos manually
sudo docker exec cleanvid cleanvid process --max-videos 10

# Process for 2 hours
sudo docker exec cleanvid cleanvid process --max-time 120

# View recent processing history
sudo docker exec cleanvid cleanvid history --limit 20

# View ONLY failed videos
sudo docker exec cleanvid cleanvid history | grep "FAILED"

# View configuration
sudo docker exec cleanvid cleanvid config --show

# Find a video file path
find /volume1/Videos -name "*Movie*Name*.mkv"

# Check if subtitle exists for a video
ls -la /volume1/Videos/Action/Movie\ Name/

# View container logs
sudo docker logs cleanvid | tail -50

# View processing log file
cat /volume1/docker/cleanvid/logs/cleanvid.log

# Restart container
cd /volume1/docker/cleanvid
sudo docker-compose down
sudo docker-compose up -d
```

### **Workflow: Manually Add Subtitle and Reprocess**

```bash
# 1. Find the video
find /volume1/Videos -name "127.Hours*.mkv"
# Output: /volume1/Videos/Action/127.Hours.2010/127.Hours.2010.mkv

# 2. Download subtitle from opensubtitles.org
# Save as: 127.Hours.2010.srt
# Upload to: /volume1/Videos/Action/127.Hours.2010/

# 3. Verify subtitle is there
ls -la /volume1/Videos/Action/127.Hours.2010/
# Should show both .mkv and .srt

# 4. Reset the video
sudo docker exec cleanvid cleanvid reset "/input/Action/127.Hours.2010/127.Hours.2010.mkv"

# 5. Process it
sudo docker exec cleanvid cleanvid process "/input/Action/127.Hours.2010/127.Hours.2010.mkv"
```

### **Workflow: Review Failures After Nightly Run**

```bash
# 1. View all failures
sudo docker exec cleanvid cleanvid history | grep "FAILED"

# 2. Get count of failures
sudo docker exec cleanvid cleanvid history | grep "FAILED" | wc -l

# 3. For each failure, download subtitle manually from opensubtitles.org
# Place .srt file next to video with matching name

# 4. Reset and let next nightly run process them
sudo docker exec cleanvid cleanvid reset "/input/path/to/video.mkv"
```

---

## 📋 TABLE OF CONTENTS

1. [System Architecture](#system-architecture)
2. [Prerequisites](#prerequisites)
3. [Part 1: Build Docker Image](#part-1-build-docker-image)
4. [Part 2: Setup Configuration](#part-2-setup-configuration)
5. [Part 3: Create Docker Container](#part-3-create-docker-container)
6. [Part 4: Test Processing](#part-4-test-processing)
7. [Part 5: Schedule Nightly Processing](#part-5-schedule-nightly-processing)
8. [Part 6: Monitoring & Maintenance](#part-6-monitoring--maintenance)
9. [Video Quality Explanation](#video-quality-explanation)
10. [Profanity Word List](#profanity-word-list)
11. [Troubleshooting](#troubleshooting)
12. [TODO: Future Enhancements](#todo-future-enhancements)

---

## 🏗️ SYSTEM ARCHITECTURE

### **What Cleanvid Does**

1. **Scans** your video library (`/volume1/Videos`)
2. **Downloads** English subtitles from OpenSubtitles (or uses existing .srt files)
3. **Detects** profanity in subtitle text using configurable word list
4. **Mutes** audio at profanity timestamps using FFmpeg
5. **Creates** filtered videos in separate directory (`/volume1/Videos-Filtered`)
6. **Preserves** original video quality (stream copy mode - no re-encoding)
7. **Tracks** processed videos to avoid reprocessing

### **Directory Structure**

```
/volume1/
├── Videos/                          # Original videos (read/write for subtitles)
│   ├── Action/
│   │   └── Die Hard/
│   │       ├── Die.Hard.mkv        # Original video
│   │       └── Die.Hard.srt        # Subtitle (auto-downloaded or manual)
│   └── Comedy/
├── Videos-Filtered/                 # Filtered videos (created by cleanvid)
│   ├── Action/
│   │   └── Die Hard/
│   │       └── Die.Hard.mkv        # Filtered video (profanity muted)
│   └── Comedy/
└── docker/
    └── cleanvid/
        ├── config/
        │   ├── settings.json        # Main configuration
        │   ├── profanity_words.txt  # Word list
        │   └── processed_log.json   # Tracks processed videos
        ├── logs/
        │   └── cleanvid.log         # Processing logs
        └── docker-compose.yml       # Container definition
```

---

## 📦 PREREQUISITES

### **Required**
- Synology NAS with Docker/Container Manager
- SSH access to Synology
- Windows PC (for building tar package)
- OpenSubtitles account (free): https://www.opensubtitles.org/register

### **Recommended**
- 500GB+ free space on NAS (for filtered videos)
- 2GB+ RAM available for Docker
- Fast CPU for FFmpeg processing

---

## 🔨 PART 1: BUILD DOCKER IMAGE

### **Step 1: Update Source Code (Windows PC)**

Navigate to project:
```powershell
cd C:\Users\aaron\SynologyDrive\repos\jellyfin\cleanvid
```

**Critical Code Fix (Already Applied):**

File: `src/cleanvid/services/subtitle_manager.py`

Three methods need language parameter fixed to use config default:

**Lines ~128, ~212, ~265** - Changed from:
```python
def method_name(self, video_path: Path, language: str = 'en', ...):
```

To:
```python
def method_name(self, video_path: Path, language: Optional[str] = None, ...):
    # Use config language if not specified
    if language is None:
        language = self.config.language
```

This ensures OpenSubtitles uses the 3-letter language code from config (`eng`) instead of hardcoded 2-letter code (`en`).

---

### **Step 2: Verify requirements.txt**

File: `requirements.txt`

Ensure line 2 has `#` comment:
```
# Cleanvid - Automated Movie Profanity Filter
# Core dependencies for the cleanvid application.
## Core Processing
pydantic>=2.0.0
```

If missing `#`, Docker build will fail with "Invalid requirement" error.

---

### **Step 3: Create Distribution Package (Windows PC)**

```powershell
cd C:\Users\aaron\SynologyDrive\repos\jellyfin\cleanvid

# Delete old tar if exists
del cleanvid.tar.gz

# Create new tar with all files
tar -czf cleanvid.tar.gz *

# Verify created
dir cleanvid.tar.gz
```

Should show file ~200-300 KB.

---

### **Step 4: Upload to Synology**

**Via Synology File Station:**

1. Browser: `http://synology-ip:5000`
2. Log in to DSM
3. Click **File Station**
4. Navigate to `/docker/`
5. Delete old `cleanvid.tar.gz` (if exists)
6. Click **Upload** → **Select files from computer**
7. Select `cleanvid.tar.gz` from Windows PC
8. Wait for upload complete (progress bar finishes)

---

### **Step 5: Extract Files on Synology**

**SSH to Synology:**

```bash
ssh scum@synology-ip
cd /volume1/docker
```

**Clean up old source:**
```bash
sudo rm -rf cleanvid-source
mkdir cleanvid-source
```

**Extract tar:**
```bash
tar -xzf cleanvid.tar.gz -C cleanvid-source
```

**Verify extraction:**
```bash
ls -la cleanvid-source/Dockerfile
ls -la cleanvid-source/src/cleanvid/services/subtitle_manager.py
ls -la cleanvid-source/requirements.txt
```

All three files should exist.

---

### **Step 6: Build Docker Image**

```bash
cd /volume1/docker/cleanvid-source
sudo docker build -t cleanvid:latest .
```

**Build takes 3-5 minutes.** Output will show:
- Step 1/X: FROM python:3.11-slim
- Installing Python packages
- Installing jellyfin-ffmpeg
- Installing system dependencies
- Final: `Successfully built [hash]`
- Final: `Successfully tagged cleanvid:latest`

**Verify image created:**
```bash
sudo docker images | grep cleanvid
```

Should show:
```
cleanvid    latest    [hash]    X minutes ago    ~500MB
```

**If build fails:**
- Check `requirements.txt` has `#` on line 2
- Check Dockerfile exists
- Check network access (downloads packages from internet)

---

## ⚙️ PART 2: SETUP CONFIGURATION

### **Step 7: Create Directory Structure**

```bash
mkdir -p /volume1/docker/cleanvid/config
mkdir -p /volume1/docker/cleanvid/logs
mkdir -p /volume1/Videos-Filtered
```

**Set permissions:**
```bash
sudo chmod 777 /volume1/Videos-Filtered
```

**Create Shared Folder (if not already):**

In Synology DSM:
1. Control Panel → Shared Folder
2. Create → Name: `Videos-Filtered`
3. Set permissions: Your user (Read/Write), jellyfin (Read only)

---

### **Step 8: Initialize Configuration**

```bash
sudo docker run --rm \
  -v /volume1/docker/cleanvid/config:/config \
  cleanvid:latest init
```

Should show:
```
✓ Configuration initialized at: /config
```

**Verify files created:**
```bash
ls -la /volume1/docker/cleanvid/config/
```

Should show:
- `settings.json` (~694 bytes)
- `profanity_words.txt` (~88 bytes)
- `processed_log.json` (2 bytes - empty array)
- `README.md` (~1831 bytes)

---

### **Step 9: Configure settings.json**

```bash
nano /volume1/docker/cleanvid/config/settings.json
```

**Update to this (replace with your OpenSubtitles credentials):**

```json
{
  "processing": {
    "max_daily_processing": 9999,
    "max_processing_time_minutes": 300,
    "video_extensions": [".mkv", ".mp4", ".avi", ".mov", ".m4v"],
    "mute_padding_before_ms": 500,
    "mute_padding_after_ms": 500
  },
  "paths": {
    "input_dir": "/input",
    "output_dir": "/output",
    "config_dir": "/config",
    "logs_dir": "/logs"
  },
  "opensubtitles": {
    "enabled": true,
    "language": "eng",
    "username": "your_opensubtitles_username",
    "password": "your_opensubtitles_password",
    "api_key": null
  },
  "ffmpeg": {
    "threads": 2,
    "audio_codec": "aac",
    "audio_bitrate": "192k",
    "video_codec": "copy",
    "re_encode_video": false
  }
}
```

**Key Settings Explained:**

| Setting | Value | Why |
|---------|-------|-----|
| `max_daily_processing` | `9999` | Process unlimited videos per run |
| `max_processing_time_minutes` | `300` | Stop after 5 hours (midnight-5AM) |
| `language` | `"eng"` | 3-letter ISO code for English |
| `video_codec` | `"copy"` | **Stream copy (no quality loss)** |
| `re_encode_video` | `false` | **No re-encoding (fastest)** |
| `audio_codec` | `"aac"` | Re-encode audio to AAC |
| `audio_bitrate` | `"192k"` | Audio quality (192 kbps) |

**Save:** `Ctrl+X`, `Y`, `Enter`

---

### **Step 10: Configure Profanity Word List**

```bash
nano /volume1/docker/cleanvid/config/profanity_words.txt
```

**Delete existing content and paste the comprehensive word list** (see [Profanity Word List](#profanity-word-list) section below).

**Save:** `Ctrl+X`, `Y`, `Enter`

**Verify word count:**
```bash
wc -l /volume1/docker/cleanvid/config/profanity_words.txt
```

Should show ~150-200 lines (depending on your list).

---

## 🐳 PART 3: CREATE DOCKER CONTAINER

### **Step 11: Create docker-compose.yml**

```bash
nano /volume1/docker/cleanvid/docker-compose.yml
```

**Paste this exactly:**

```yaml
version: '3.8'

services:
  cleanvid:
    image: cleanvid:latest
    container_name: cleanvid
    restart: unless-stopped
    entrypoint: ["/bin/sh"]
    command: ["-c", "while true; do sleep 3600; done"]
    volumes:
      - /volume1/Videos:/input
      - /volume1/Videos-Filtered:/output
      - /volume1/docker/cleanvid/config:/config
      - /volume1/docker/cleanvid/logs:/logs
    environment:
      - TZ=America/New_York
```

**Important Notes:**
- `/volume1/Videos:/input` - **NOT read-only** (needs to write subtitle files)
- `/volume1/Videos-Filtered:/output` - Filtered videos output
- Adjust timezone if needed (e.g., `America/Los_Angeles`, `Europe/London`)

**Save:** `Ctrl+X`, `Y`, `Enter`

**Verify file:**
```bash
cat /volume1/docker/cleanvid/docker-compose.yml
```

---

### **Step 12: Start Container**

```bash
cd /volume1/docker/cleanvid
sudo docker-compose up -d
```

**Expected output:**
```
Creating network "cleanvid_default" with the default driver
Creating cleanvid ... done
```

**Verify container is running:**
```bash
sudo docker ps | grep cleanvid
```

Should show:
```
CONTAINER ID   IMAGE              COMMAND                  CREATED        STATUS        NAMES
[hash]         cleanvid:latest    "/bin/sh -c 'while t…"   X seconds ago  Up X seconds  cleanvid
```

**Status should say "Up X seconds"** (NOT "Restarting")

**If status shows "Restarting":**
```bash
# Check logs for error
sudo docker logs cleanvid

# Stop and remove
sudo docker-compose down

# Verify docker-compose.yml is correct and try again
sudo docker-compose up -d
```

---

### **Step 13: Test Container Commands**

**Test status:**
```bash
sudo docker exec cleanvid cleanvid status
```

**Expected output:**
```
============================================================
Cleanvid System Status
============================================================

Configuration:
✓ Config directory: /config
✓ Settings file: Valid
✓ Profanity words: XXX words loaded

FFmpeg:
✓ FFmpeg available: /usr/lib/jellyfin-ffmpeg/ffmpeg
✓ Version: 7.x.x

Videos:
  Total: XXX
  Processed: 0
  Unprocessed: XXX
  Success rate: N/A

Paths:
  Input: /input
  Output: /output
  Config: /config
  Logs: /logs
============================================================
```

**Test config:**
```bash
sudo docker exec cleanvid cleanvid config --show
```

**Verify:**
- `Max daily videos: 9999`
- `Language: eng`
- `Enabled: True` (OpenSubtitles)
- `Authenticated: True` (if credentials correct)

**If "Authenticated: False":**
- Check OpenSubtitles username/password in settings.json
- Verify account is active on opensubtitles.org

---

## 🧪 PART 4: TEST PROCESSING

### **Step 14: Process Test Videos**

**Start with 2-5 videos to test:**

```bash
sudo docker exec cleanvid cleanvid process --max-videos 5
```

**Expected output:**
```
============================================================
Starting batch processing of 5 videos
Time limit: 300 minutes
============================================================
[1/5] Processing: Movie.Name.2024.mkv
------------------------------------------------------------
Video: Movie.Name.2024.mkv
Status: success
✓ Successfully processed
  Segments muted: 23
  Processing time: 8.5 minutes

[2/5] Processing: Another.Movie.2023.mp4
------------------------------------------------------------
...
```

**Processing time per video:**
- 2-hour movie: ~5-10 minutes
- Download subtitle: 1-3 minutes
- Parse & detect profanity: 5-10 seconds
- FFmpeg processing: 3-5 minutes

**Note:** Some videos may fail with "No subtitle file found" - this is normal. See [Handling Failed Videos](#handling-failed-videos) below.

---

### **Step 15: Verify Results**

**Check processing history:**
```bash
sudo docker exec cleanvid cleanvid history --limit 10
```

**Expected output:**
```
================================================================================
Processing History (Most Recent 10)
================================================================================
✓ 2025-12-25T17:15:14 | SUCCESS | Movie.Name.2024.mkv
  Segments muted: 23

✓ 2025-12-25T17:06:22 | SUCCESS | Another.Movie.2023.mp4
  Segments muted: 15

✗ 2025-12-25T16:54:56 | FAILED  | Obscure.Movie.2020.mkv
  Error: No subtitle file found or could not be downloaded
```

**Check filtered files exist:**
```bash
ls -la /volume1/Videos-Filtered/
```

Should show same directory structure as `/volume1/Videos` with filtered videos.

**Check subtitle files were downloaded:**
```bash
find /volume1/Videos -name "*.srt" | head -10
```

Should show .srt files next to video files.

---

### **Step 16: Test Filtered Video Quality**

**Pick a video that processed successfully and test it:**

1. **Find profanity timestamp in subtitle:**
```bash
cat /volume1/Videos/Action/Movie\ Name/Movie.Name.2024.srt | grep -i "shit"
```

Example output:
```
49
00:05:03,154 --> 00:05:04,088
Shit.
```

2. **Open filtered video in VLC or Jellyfin**
3. **Jump to timestamp:** `00:05:03`
4. **Verify:** Audio should be muted for ~1 second
5. **Check video quality:** Should be identical to original (same resolution, no compression artifacts)

---

### **Step 17: Handling Failed Videos**

**View failures:**
```bash
sudo docker exec cleanvid cleanvid history | grep "FAILED"
```

**Common failure reason:** "No subtitle file found or could not be downloaded"

**Why this happens:**
- Subtitle doesn't exist on OpenSubtitles
- Movie too new or obscure
- Filename doesn't match database entries
- Foreign film without English subtitles

**Solution - Manual Subtitle Download:**

1. **Find video path:**
```bash
find /volume1/Videos -name "Movie.Name*.mkv"
# Output: /volume1/Videos/Action/Movie Name/Movie.Name.2024.mkv
```

2. **Download subtitle manually:**
   - Go to: https://www.opensubtitles.org
   - Search for movie name
   - Download English subtitle (.srt)

3. **Upload subtitle to NAS:**
   - Rename to match video: `Movie.Name.2024.srt`
   - Place in same folder: `/volume1/Videos/Action/Movie Name/`

4. **Verify subtitle exists:**
```bash
ls -la /volume1/Videos/Action/Movie\ Name/
# Should show both .mkv and .srt
```

5. **Reset video:**
```bash
sudo docker exec cleanvid cleanvid reset "/input/Action/Movie Name/Movie.Name.2024.mkv"
```

6. **Process again:**
```bash
sudo docker exec cleanvid cleanvid process "/input/Action/Movie Name/Movie.Name.2024.mkv"
```

Should now succeed!

---

## ⏰ PART 5: SCHEDULE NIGHTLY PROCESSING

### **Step 18: Create Scheduled Task**

**In Synology DSM:**

1. Open browser: `http://synology-ip:5000`
2. **Control Panel** → **Task Scheduler**
3. Click **Create** → **Scheduled Task** → **User-defined script**

---

**General Tab:**
- **Task:** `Cleanvid Nightly Processing`
- **User:** `root` (or your username - both work)
- **Enabled:** ✓ Checked
- Leave other settings default

---

**Schedule Tab:**
- **Date:** Select **Run on the following days** → **Daily**
- **First run time:** `00:00` (midnight)
- **Frequency:** Leave as default
- **Last run time:** Leave blank

---

**Task Settings Tab:**

In the **User-defined script** box, type **exactly**:

```bash
docker exec cleanvid cleanvid process --max-time 300
```

**Do not add anything else** (no sudo, no extra lines).

**Optional - Email Notifications:**
- Leave unchecked (unless you want emails)

---

4. Click **OK**
5. Enter your DSM password when prompted (required for root tasks)
6. Click **OK** to confirm

---

### **Step 19: Verify Scheduled Task**

In Task Scheduler list, verify:

- ✓ Task: `Cleanvid Nightly Processing`
- ✓ Status: **Enabled**
- ✓ Next Run Time: Shows today or tomorrow at **00:00**
- ✓ Last Result: Will show after first run

---

### **Step 20: Manual Test of Scheduled Command**

**Test the exact command that will run nightly:**

```bash
sudo docker exec cleanvid cleanvid process --max-videos 10
```

**Let this run for 30-60 minutes** (processes 10 videos).

**Monitor progress:**
```bash
# In another SSH session
sudo docker logs cleanvid -f
```

**Verify success:**
```bash
sudo docker exec cleanvid cleanvid history --limit 15
```

Should show 10+ processed videos (mix of SUCCESS and FAILED is normal).

---

## 📊 PART 6: MONITORING & MAINTENANCE

### **Daily/Weekly Monitoring**

**Check processing status:**
```bash
sudo docker exec cleanvid cleanvid status
```

**View recent history:**
```bash
sudo docker exec cleanvid cleanvid history --limit 20
```

**Count processed vs remaining:**
```bash
sudo docker exec cleanvid cleanvid status | grep -A 5 "Videos:"
```

**View failures only:**
```bash
sudo docker exec cleanvid cleanvid history | grep "FAILED"
```

**Count failures:**
```bash
sudo docker exec cleanvid cleanvid history | grep "FAILED" | wc -l
```

---

### **Container Management**

**View container logs:**
```bash
sudo docker logs cleanvid | tail -50
```

**Follow logs in real-time:**
```bash
sudo docker logs cleanvid -f
```

**Restart container:**
```bash
cd /volume1/docker/cleanvid
sudo docker-compose restart
```

**Stop container:**
```bash
sudo docker-compose stop
```

**Start container:**
```bash
sudo docker-compose start
```

**Remove and recreate container:**
```bash
sudo docker-compose down
sudo docker-compose up -d
```

---

### **Configuration Changes**

**After changing settings.json or profanity_words.txt:**

1. **No container restart needed** - changes take effect immediately
2. **To reprocess videos with new word list:**
```bash
# Reset specific video
sudo docker exec cleanvid cleanvid reset "/input/path/to/video.mkv"

# Or reset all videos (nuclear option)
sudo docker exec cleanvid cleanvid process --force
```

---

### **Disk Space Management**

**Check disk usage:**
```bash
du -sh /volume1/Videos
du -sh /volume1/Videos-Filtered
```

**Check available space:**
```bash
df -h /volume1
```

**Expected:** Filtered videos are approximately same size as originals (stream copy mode).

---

### **Routine Maintenance Checklist**

**Weekly:**
- [ ] Check processing status
- [ ] Review failed videos
- [ ] Download missing subtitles manually
- [ ] Check disk space

**Monthly:**
- [ ] Review processed_log.json size (should grow over time)
- [ ] Clean up old log files if needed
- [ ] Verify nightly processing is running (check Task Scheduler)
- [ ] Test a few random filtered videos for quality

---

## 🎬 VIDEO QUALITY EXPLANATION

### **Current Configuration: COPY MODE (No Quality Loss)**

**FFmpeg Settings:**
```json
"ffmpeg": {
  "video_codec": "copy",
  "re_encode_video": false,
  "audio_codec": "aac",
  "audio_bitrate": "192k"
}
```

---

### **What This Means:**

**Video Stream:**
- ✅ **Original video stream copied exactly** (bit-for-bit)
- ✅ **No re-encoding**
- ✅ **No quality loss**
- ✅ **No compression artifacts**
- ✅ **Same file size** (±1%)
- ✅ **Fastest processing** (5-10 min per 2-hour movie)

**Audio Stream:**
- 🔄 **Re-encoded to AAC @ 192k**
- 🔇 **Specific segments muted** (profanity timestamps)
- ✅ **Rest of audio preserved at high quality**

---

### **Quality Preservation Examples**

| Original | Filtered | Video Quality | File Size |
|----------|----------|---------------|-----------|
| 1080p Blu-ray (30GB, H.264) | 1080p (30GB, H.264) | **Identical** | Same |
| 4K HDR (50GB, H.265/HEVC) | 4K HDR (50GB, H.265/HEVC) | **Identical** | Same |
| 720p (2GB, H.264) | 720p (2GB, H.264) | **Identical** | Same |
| 480p DVD (1GB, MPEG2) | 480p (1GB, MPEG2) | **Identical** | Same |

---

### **Verify Quality on Your Files**

**Check original video specs:**
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,codec_name,bit_rate /volume1/Videos/Action/Movie/Movie.mkv
```

**Check filtered video specs:**
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,codec_name,bit_rate /volume1/Videos-Filtered/Action/Movie/Movie.mkv
```

**Should be identical:**
- `width` (e.g., 1920)
- `height` (e.g., 1080)
- `codec_name` (e.g., h264)
- `bit_rate` (e.g., 8000000)

---

### **Why Stream Copy?**

**Advantages:**
- ⚡ **10x faster** than re-encoding
- 💾 **No additional disk space** needed
- 🎨 **Perfect quality** preservation
- 🔋 **Low CPU usage**
- ✅ **Works with any codec** (H.264, H.265, VP9, AV1, etc.)
- ✅ **Preserves HDR/Dolby Vision**

**Disadvantages:**
- Cannot change resolution
- Cannot reduce file size
- Audio must be re-encoded (minor quality impact)

---

### **Alternative Modes (Future Enhancement)**

See [TODO: Video Quality Options](#priority-3-video-quality-options) for planned compression modes.

---

## 📝 PROFANITY WORD LIST

### **Comprehensive Default List**

Save this to `/volume1/docker/cleanvid/config/profanity_words.txt`:

```text
# ============================================================
# CLEANVID PROFANITY WORD LIST
# ============================================================
# Lines starting with # are comments
# Use * as wildcard (f*ck matches fuck, feck, f**k, etc.)
# One word per line
# Case insensitive matching

# ============================================================
# STRONG PROFANITY - Explicit Sexual/Vulgar
# ============================================================
f*ck
f**k
fck
fuck
fucker
fucked
fucking
motherfucker
motherf*cker
cocksucker
c*cksucker
pussy
puss
cunt
c*nt
cock
c*ck
dick
prick
twat
asshole
assh*le

# ============================================================
# STRONG PROFANITY - Excrement/Bodily Functions
# ============================================================
shit
sh*t
shite
bullshit
bullsh*t
horseshit
piss
pissed

# ============================================================
# STRONG PROFANITY - Derogatory Terms
# ============================================================
bitch
b*tch
bitches
bastard
bastards
whore
slut
sluts
hooker
hoe

# ============================================================
# MEDIUM PROFANITY - Common Swears
# ============================================================
damn
dammit
damned
goddamn
goddammit
hell
crap
crappy
screw
screwed
suck
sucks
sucked

# ============================================================
# RELIGIOUS - Taking Name in Vain
# ============================================================
# Note: These will also catch legitimate religious references
# Consider carefully before enabling
# jesus
# christ
# god
# oh my god
# for god's sake
# goddammit (already in medium section)

# ============================================================
# MILD PROFANITY - Crude Language
# ============================================================
ass
arse
butt
pissing
balls
ballsy
tit
tits
boob
boobs
fart
farted

# ============================================================
# VARIATIONS - Strong Language
# ============================================================
fuk
fuk*
fvck
mofo
mfer
shitty
shithead
dipshit
chickenshit
apeshit
batshit
jackshit
sonofabitch
son of a bitch
bitchass
dumbass
dumbarse
jackass
smartass
badass
hardass
kissass
fatass
dickhead
dickface
dickwad
asshat
assclown
asswipe
assface
douchebag
douchecanoe

# ============================================================
# BRITISH/AUSTRALIAN SLANG
# ============================================================
bloody
bugger
bollocks
bullocks
wanker
tosser
git
sod
sodding
knob
bellend
prat
pillock
minger
slag
munter
chav
twit
numpty
plonker
muppet
berk
nonce

# ============================================================
# PHRASES - Strong (if you want phrases)
# ============================================================
# piece of shit
# full of shit
# no shit
# holy shit
# eat shit
# pain in the ass
# kiss my ass
# screw you
# fuck you
# fuck off
# piss off
# blow me
# suck it

# ============================================================
# CUSTOM WORDS
# ============================================================
# Add your own words below:


```

---

### **Customization Tips**

**To add words:**
```bash
nano /volume1/docker/cleanvid/config/profanity_words.txt
# Add words, save
# No container restart needed - takes effect immediately
```

**To test new words:**
```bash
# Reset a video that contains the new word
sudo docker exec cleanvid cleanvid reset "/input/path/to/video.mkv"

# Process it
sudo docker exec cleanvid cleanvid process "/input/path/to/video.mkv"
```

**Wildcard usage:**
- `f*ck` matches: fuck, feck, f**k, fock, etc.
- `sh*t` matches: shit, shot, shat, etc.
- Be careful: `ass` will also match: glass, class, pass, bass, etc.

**Phrase matching:**
- Phrases work if all words appear in same subtitle line
- `son of a bitch` only matches if together in one line
- Won't match if split across multiple subtitle entries

---

## 🔧 TROUBLESHOOTING

### **Container Won't Start (Status: Restarting)**

**Check logs:**
```bash
sudo docker logs cleanvid
```

**Common causes:**
- Invalid command in docker-compose.yml
- Missing volume paths
- Incorrect entrypoint

**Solution:**
```bash
sudo docker-compose down
nano docker-compose.yml
# Verify exactly matches template in Step 11
sudo docker-compose up -d
```

---

### **"No Subtitle Found" Errors**

**This is normal** - not all movies have subtitles on OpenSubtitles.

**Expected rate:** 70-80% success, 20-30% failures

**Solutions:**
1. Download subtitles manually from opensubtitles.org
2. Try other subtitle sites (subscene, yifysubtitles)
3. Skip movies without subtitles

---

### **OpenSubtitles Authentication Failed**

**Check credentials:**
```bash
sudo docker exec cleanvid cleanvid config --show | grep -A 3 "OpenSubtitles"
```

If shows `Authenticated: False`:

1. Verify username/password in settings.json
2. Check account is active on opensubtitles.org
3. Try logging in on website to verify credentials
4. Update settings.json with correct credentials

---

### **Filtered Videos Have Poor Quality**

**This should NOT happen with default settings.**

**Check FFmpeg mode:**
```bash
sudo docker exec cleanvid cleanvid config --show | grep -A 5 "FFmpeg"
```

Should show:
```
Audio: aac @ 192k
Re-encode video: False
```

If `Re-encode video: True`:
```bash
nano /volume1/docker/cleanvid/config/settings.json
# Change "re_encode_video": true to false
# Save and reprocess videos
```

---

### **Processing is Slow**

**Normal speed:** 5-10 minutes per 2-hour movie in copy mode.

**If slower than this:**

1. **Check CPU usage:**
```bash
top
# Press 1 to show all cores
# Look for ffmpeg process
```

2. **Check disk I/O:**
```bash
iostat -x 1
# Look for high %util
```

3. **Reduce threads if needed:**
```bash
nano /volume1/docker/cleanvid/config/settings.json
# Change "threads": 2 to "threads": 1
```

---

### **Disk Space Full**

**Check space:**
```bash
df -h /volume1
```

**Solutions:**
1. Delete old/unwanted videos from Videos-Filtered
2. Process fewer videos per night (reduce `max_daily_processing`)
3. Add more storage

**Note:** Filtered videos are approximately same size as originals.

---

### **Task Scheduler Not Running**

**Check task exists:**
- DSM → Control Panel → Task Scheduler
- Find: `Cleanvid Nightly Processing`
- Verify: Enabled checkbox is checked

**Check last result:**
- Click on task
- Look at "Last Result" column
- If error, check "Last Run Time" logs

**Manual test:**
```bash
sudo docker exec cleanvid cleanvid process --max-videos 2
```

If this works, Task Scheduler is likely configured wrong.

---

### **Cannot Find Video Path**

**Find video:**
```bash
find /volume1/Videos -name "*Movie*Name*.mkv"
```

**Remember:** Convert path for Docker:
- Filesystem: `/volume1/Videos/Action/Movie/Movie.mkv`
- Docker: `/input/Action/Movie/Movie.mkv`

---

## 📋 TODO: FUTURE ENHANCEMENTS

---

## **Priority 1: Failed Video Log (Easy to Review)**

### **Goal**
Create separate JSON log file for failed videos that's easy to review and process with scripts.

### **Implementation**

**File:** `src/cleanvid/services/processor.py`

**Add method:**
```python
def _log_failure(self, video_path: Path, error: str):
    """Log failed video to separate failures log."""
    failures_log = self.config_manager.config.paths.config_dir / "failed_videos.json"
    
    # Load existing failures
    if failures_log.exists():
        with open(failures_log, 'r') as f:
            failures = json.load(f)
    else:
        failures = []
    
    # Add new failure
    failures.append({
        "timestamp": datetime.now().isoformat(),
        "video_path": str(video_path),
        "video_name": video_path.name,
        "relative_path": str(video_path.relative_to(self.config.paths.input_dir)),
        "error": error,
        "error_type": self._classify_error(error),
        "retries": 0,
        "status": "pending"
    })
    
    # Save
    with open(failures_log, 'w') as f:
        json.dump(failures, indent=2, fp=f)

def _classify_error(self, error: str) -> str:
    """Classify error type for filtering."""
    if "subtitle" in error.lower():
        return "no_subtitle"
    elif "ffmpeg" in error.lower():
        return "ffmpeg_error"
    elif "permission" in error.lower():
        return "permission_error"
    else:
        return "unknown"
```

**Update:** Call `_log_failure()` in exception handlers.

---

### **Output Format**

**File:** `/volume1/docker/cleanvid/config/failed_videos.json`

```json
[
  {
    "timestamp": "2025-12-25T17:00:00",
    "video_path": "/input/Action/127 Hours/127.Hours.2010.mkv",
    "video_name": "127.Hours.2010.mkv",
    "relative_path": "Action/127 Hours/127.Hours.2010.mkv",
    "error": "No subtitle file found or could not be downloaded",
    "error_type": "no_subtitle",
    "retries": 0,
    "status": "pending"
  },
  {
    "timestamp": "2025-12-25T17:05:00",
    "video_path": "/input/Action/13 Assassins/13.Assassins.2010.mp4",
    "video_name": "13.Assassins.2010.mp4",
    "relative_path": "Action/13 Assassins/13.Assassins.2010.mp4",
    "error": "No subtitle file found or could not be downloaded",
    "error_type": "no_subtitle",
    "retries": 0,
    "status": "pending"
  }
]
```

---

### **CLI Commands to Add**

**View failures:**
```bash
cleanvid failures --list
cleanvid failures --count
cleanvid failures --type no_subtitle
```

**Mark as resolved:**
```bash
cleanvid failures --resolve "/input/path/to/video.mkv"
```

**Clear all resolved:**
```bash
cleanvid failures --clear-resolved
```

---

### **Helper Script: Retry Failed Videos**

**File:** `/volume1/docker/cleanvid/retry_failed.sh`

```bash
#!/bin/bash
# Retry all failed videos that have status "pending"

FAILURES_FILE="/volume1/docker/cleanvid/config/failed_videos.json"

if [ ! -f "$FAILURES_FILE" ]; then
    echo "No failures file found"
    exit 0
fi

# Get list of pending failures
cat "$FAILURES_FILE" | jq -r '.[] | select(.status == "pending") | .video_path' | while read video; do
    echo "========================================="
    echo "Retrying: $video"
    echo "========================================="
    
    # Reset and reprocess
    docker exec cleanvid cleanvid reset "$video"
    docker exec cleanvid cleanvid process "$video"
    
    # Check if succeeded
    if [ $? -eq 0 ]; then
        echo "✓ Success: $video"
        docker exec cleanvid cleanvid failures --resolve "$video"
    else
        echo "✗ Still failing: $video"
    fi
    
    echo ""
done

echo "Retry complete!"
```

**Make executable:**
```bash
chmod +x /volume1/docker/cleanvid/retry_failed.sh
```

**Run:**
```bash
/volume1/docker/cleanvid/retry_failed.sh
```

---

### **Benefits**

✅ Easy to see all failures in one place
✅ Can filter by error type
✅ Script-friendly JSON format
✅ Track retry attempts
✅ Mark resolved vs pending
✅ Can export for manual subtitle hunting

---

## **Priority 2: Manual Timestamp Skipping**

### **Goal**
Allow users to manually specify timestamps to mute without needing subtitles.

**Use cases:**
- Videos without subtitles
- Videos with embedded/burned-in subtitles
- Fine-tune muting beyond subtitle accuracy
- Music videos, documentaries, etc.

---

### **Implementation**

**File:** `config/manual_timestamps.json`

```json
{
  "Action/Die Hard/Die.Hard.mkv": [
    {
      "start": "00:15:30",
      "end": "00:15:32",
      "reason": "profanity - f-word"
    },
    {
      "start": "01:23:45.500",
      "end": "01:23:48.200",
      "reason": "violence - graphic"
    }
  ],
  "Comedy/Superbad/Superbad.2007.mp4": [
    {
      "start": "00:42:10",
      "end": "00:42:12",
      "reason": "profanity"
    }
  ]
}
```

**Format:**
- Key: Relative path from `/input`
- Timestamps: `HH:MM:SS` or `HH:MM:SS.mmm` (milliseconds optional)
- Reason: Optional note for tracking

---

### **Code Changes**

**File:** `src/cleanvid/services/video_processor.py`

**Add method:**
```python
def _load_manual_timestamps(self, video_path: Path) -> List[MuteSegment]:
    """Load manual timestamps for this video."""
    timestamps_file = self.config.paths.config_dir / "manual_timestamps.json"
    
    if not timestamps_file.exists():
        return []
    
    try:
        with open(timestamps_file, 'r') as f:
            manual_timestamps = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load manual timestamps: {e}")
        return []
    
    # Get relative path
    try:
        relative_path = str(video_path.relative_to(self.config.paths.input_dir))
    except ValueError:
        # video_path not under input_dir
        return []
    
    # Find timestamps for this video
    if relative_path in manual_timestamps:
        segments = []
        for ts in manual_timestamps[relative_path]:
            try:
                start = self._parse_timestamp(ts["start"])
                end = self._parse_timestamp(ts["end"])
                reason = ts.get("reason", "manual")
                
                segments.append(MuteSegment(
                    start_time=start,
                    end_time=end,
                    text=f"[Manual: {reason}]"
                ))
            except Exception as e:
                logger.warning(f"Failed to parse manual timestamp: {e}")
                continue
        
        logger.info(f"Loaded {len(segments)} manual timestamps for {video_path.name}")
        return segments
    
    return []

def _parse_timestamp(self, timestamp: str) -> float:
    """Convert HH:MM:SS or HH:MM:SS.mmm to seconds."""
    # Handle HH:MM:SS.mmm format
    if '.' in timestamp:
        main_part, ms_part = timestamp.rsplit('.', 1)
        milliseconds = float(f"0.{ms_part}")
    else:
        main_part = timestamp
        milliseconds = 0.0
    
    # Parse HH:MM:SS
    parts = main_part.split(':')
    if len(parts) != 3:
        raise ValueError(f"Invalid timestamp format: {timestamp}")
    
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    
    total = hours * 3600 + minutes * 60 + seconds + milliseconds
    return total
```

**Update:** `process_video()` method to merge manual + subtitle segments:

```python
def process_video(self, video_path: Path) -> ProcessingResult:
    """Process a video file."""
    # ... existing code ...
    
    # Load subtitle segments
    subtitle_segments = self._detect_profanity(subtitle_file)
    
    # Load manual timestamps
    manual_segments = self._load_manual_timestamps(video_path)
    
    # Merge and sort all segments
    all_segments = subtitle_segments + manual_segments
    all_segments.sort(key=lambda s: s.start_time)
    
    # ... continue with processing ...
```

---

### **CLI Commands to Add**

**Add timestamp manually:**
```bash
cleanvid add-timestamp "/input/Action/Movie/Movie.mkv" \
  --start "00:15:30" \
  --end "00:15:32" \
  --reason "profanity"
```

**Remove timestamp:**
```bash
cleanvid remove-timestamp "/input/Action/Movie/Movie.mkv" --index 0
```

**List manual timestamps:**
```bash
cleanvid list-timestamps "/input/Action/Movie/Movie.mkv"
```

**Import from file:**
```bash
cleanvid import-timestamps timestamps.json
```

---

### **UI Helper Tool (Future)**

Web interface or GUI tool to:
1. Play video
2. Mark start/end points
3. Add reason
4. Export to `manual_timestamps.json`

---

### **Benefits**

✅ Work with videos that have no subtitles
✅ Fine-tune muting precision
✅ Override subtitle timing issues
✅ Handle burned-in/embedded subtitles
✅ Mute non-language content (sounds, music, etc.)

---

## **Priority 3: Video Quality Options**

### **Goal**
Provide multiple quality/speed tradeoff modes beyond current stream-copy mode.

**Current:** Stream copy (fastest, no quality loss)

**Add:** Compression options for users who want smaller files.

---

### **Proposed Modes**

| Mode | Speed | Quality | File Size | Use Case |
|------|-------|---------|-----------|----------|
| **copy** | ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐⭐ | 100% (same) | **Default** - Fastest, perfect quality |
| **fast** | ⚡⚡⚡⚡ | ⭐⭐⭐⭐ | ~80% | Need smaller files, fast processing |
| **balanced** | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | ~60% | Good compression, good quality |
| **quality** | ⚡⚡ | ⭐⭐⭐⭐⭐ | ~50% | Best compression with high quality |
| **archive** | ⚡ | ⭐⭐⭐⭐⭐ | ~40% | Maximum compression, slow |

---

### **Configuration**

**File:** `settings.json`

```json
{
  "ffmpeg": {
    "mode": "copy",
    
    "copy": {
      "video_codec": "copy",
      "audio_codec": "aac",
      "audio_bitrate": "192k"
    },
    
    "fast": {
      "video_codec": "libx264",
      "preset": "ultrafast",
      "crf": 23,
      "audio_codec": "aac",
      "audio_bitrate": "192k"
    },
    
    "balanced": {
      "video_codec": "libx264",
      "preset": "medium",
      "crf": 20,
      "audio_codec": "aac",
      "audio_bitrate": "256k"
    },
    
    "quality": {
      "video_codec": "libx265",
      "preset": "slow",
      "crf": 18,
      "audio_codec": "aac",
      "audio_bitrate": "320k",
      "hdr": "preserve"
    },
    
    "archive": {
      "video_codec": "libx265",
      "preset": "veryslow",
      "crf": 16,
      "audio_codec": "aac",
      "audio_bitrate": "384k",
      "hdr": "preserve",
      "two_pass": true
    }
  }
}
```

---

### **Implementation**

**File:** `src/cleanvid/utils/ffmpeg_wrapper.py`

**Update:** `_build_ffmpeg_command()` method:

```python
def _build_ffmpeg_command(self, video_path: Path, segments: List[MuteSegment], output_path: Path) -> List[str]:
    """Build FFmpeg command based on mode."""
    
    mode = self.config.ffmpeg.get("mode", "copy")
    mode_config = self.config.ffmpeg.get(mode, self.config.ffmpeg["copy"])
    
    cmd = ["ffmpeg", "-i", str(video_path)]
    
    # Video encoding
    if mode_config["video_codec"] == "copy":
        cmd.extend(["-c:v", "copy"])
    else:
        cmd.extend(["-c:v", mode_config["video_codec"]])
        
        if "preset" in mode_config:
            cmd.extend(["-preset", mode_config["preset"]])
        
        if "crf" in mode_config:
            cmd.extend(["-crf", str(mode_config["crf"])])
        
        # HDR preservation
        if mode_config.get("hdr") == "preserve":
            cmd.extend([
                "-pix_fmt", "yuv420p10le",
                "-color_primaries", "bt2020",
                "-color_trc", "smpte2084",
                "-colorspace", "bt2020nc"
            ])
    
    # Audio encoding
    cmd.extend(["-c:a", mode_config["audio_codec"]])
    cmd.extend(["-b:a", mode_config["audio_bitrate"]])
    
    # Audio filter for muting
    filter_str = self._build_audio_filter(segments)
    cmd.extend(["-af", filter_str])
    
    # Two-pass encoding
    if mode_config.get("two_pass"):
        # Implement two-pass logic
        pass
    
    cmd.append(str(output_path))
    return cmd
```

---

### **Processing Time Estimates**

**2-hour 1080p movie:**

| Mode | Time | Output Size |
|------|------|-------------|
| copy | 5 min | 8 GB (same) |
| fast | 15 min | 6.4 GB |
| balanced | 45 min | 4.8 GB |
| quality | 2 hours | 4 GB |
| archive | 4 hours | 3.2 GB |

---

### **CLI Command**

```bash
# Process with specific mode
cleanvid process --mode balanced --max-videos 10

# Change default mode
cleanvid config --set-mode quality
```

---

### **Benefits**

✅ Flexibility for different use cases
✅ Save disk space with compression
✅ Maintain quality for archival
✅ Fast processing for testing
✅ HDR/Dolby Vision preservation

---

## **Additional Future Ideas**

### **4. Web UI Dashboard**
- View processing status
- Manage failed videos
- Edit word list
- Add manual timestamps
- View statistics

### **5. Subtitle Source Priority**
- Try OpenSubtitles first
- Fall back to Subscene
- Fall back to YIFY Subtitles
- Manual upload option

### **6. Multi-Language Support**
- Process multiple subtitle languages
- Create separate filtered versions per language
- Language-specific word lists

### **7. Smart Profanity Detection**
- Machine learning to detect context
- Reduce false positives (e.g., "Scunthorpe problem")
- Severity levels (mild, moderate, strong)

### **8. Integration with Plex/Jellyfin**
- Auto-update library after processing
- Metadata preservation
- Artwork/poster generation

### **9. Statistics & Reports**
- Total videos processed
- Total profanity instances muted
- Most common profane words
- Processing time trends
- Success/failure rates

### **10. Batch Operations**
- Process specific genre
- Process specific year range
- Process by IMDB rating
- Process by file size

---

## 📞 SUPPORT & DOCUMENTATION

### **Getting Help**

1. Check this QUICKSTART guide
2. Review error messages in logs
3. Search GitHub issues (if open source)
4. File new issue with:
   - Synology model
   - DSM version
   - Docker version
   - Error logs
   - Steps to reproduce

### **Useful Links**

- OpenSubtitles: https://www.opensubtitles.org
- FFmpeg Documentation: https://ffmpeg.org/documentation.html
- Docker Documentation: https://docs.docker.com
- Synology DSM Help: https://www.synology.com/support

---

## 📄 LICENSE & CREDITS

**Cleanvid**
- Automated movie profanity filtering system
- Developed for home media servers
- Uses FFmpeg, Python, OpenSubtitles API

**Dependencies:**
- FFmpeg (Jellyfin build)
- Python 3.11
- Pydantic, pysrt, subliminal, babelfish

---

**END OF QUICKSTART GUIDE**

*Last Updated: December 25, 2025*
