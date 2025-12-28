# Troubleshooting Guide

Common issues and solutions for Cleanvid.

---

## Installation Issues

### FFmpeg Not Found

**Error:**
```
Error: FFmpeg not available
Please install FFmpeg and ensure it's in your PATH
```

**Solution (Docker):**
Docker image includes FFmpeg. Rebuild:
```bash
docker build -t cleanvid:latest --no-cache .
```

**Solution (Python):**
Install FFmpeg:
```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
# Add to PATH
```

Verify:
```bash
ffmpeg -version
which ffmpeg  # Should show path
```

### Python Dependencies Failed

**Error:**
```
ERROR: Could not find a version that satisfies the requirement...
```

**Solution:**
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install with verbose output
pip install -r requirements.txt -v

# Try specific versions
pip install pysrt==1.1.2 subliminal==2.1.0
```

---

## Configuration Issues

### Invalid Configuration

**Error:**
```
✗ Configuration has errors:
  - paths.input_dir: field required
```

**Solution:**
```bash
# Validate config
cleanvid config --validate

# Reinitialize (creates templates)
cleanvid init

# Check JSON syntax
python -m json.tool /config/settings.json
```

### Configuration Not Found

**Error:**
```
Configuration file not found
```

**Solution:**
```bash
# Docker: Check mount
docker inspect cleanvid | grep Mounts

# Python: Create config
cleanvid init

# Specify custom location
cleanvid --config /path/to/config process
```

### Word List Empty

**Error:**
```
Warning: No profanity words loaded
```

**Solution:**
```bash
# Check file exists
ls -la /config/profanity_words.txt

# Create if missing
cat > /config/profanity_words.txt << EOF
damn
hell
shit
f*ck
EOF

# Verify
cleanvid config --show
```

---

## Processing Issues

### No Videos Found

**Error:**
```
No unprocessed videos found
```

**Causes:**
1. All videos already processed
2. Wrong input directory
3. No supported video extensions

**Solution:**
```bash
# Check input directory
cleanvid status
ls -la /input/

# Check processed log
cat /config/processed_log.json

# Force reprocess
cleanvid process --force --max-videos 1

# Reset specific video
cleanvid reset /input/movie.mkv
```

### No Subtitles Found

**Error:**
```
✗ No subtitle file found or downloaded for: movie.mkv
```

**Causes:**
1. No .srt file next to video
2. OpenSubtitles disabled
3. Subtitle not available
4. OpenSubtitles credentials invalid

**Solution:**

**Option 1: Manual subtitle:**
```bash
# Download .srt file
# Place next to video with same name
/input/movie.mkv
/input/movie.srt  # ← Same name

# Retry
cleanvid process /input/movie.mkv
```

**Option 2: Enable OpenSubtitles:**
```json
{
  "opensubtitles": {
    "enabled": true,
    "language": "en",
    "username": "your_username",
    "password": "your_password"
  }
}
```

**Option 3: Use subliminal CLI:**
```bash
pip install subliminal
subliminal download -l en /input/movie.mkv
```

### Processing Fails Mid-Video

**Error:**
```
✗ Processing failed: movie.mkv
  Error: FFmpeg error: Conversion failed
```

**Causes:**
1. Corrupted video file
2. Insufficient disk space
3. Permission issues
4. Unsupported codec

**Solution:**
```bash
# Check video file
ffmpeg -i /input/movie.mkv 2>&1 | grep "Invalid"

# Check disk space
df -h /output

# Check permissions
ls -la /output/
chmod 755 /output/

# Try different settings
{
  "ffmpeg": {
    "re_encode_video": true,
    "video_codec": "libx264"
  }
}
```

### Processing Very Slow

**Symptoms:**
- Taking 10+ minutes per video
- High CPU usage
- System unresponsive

**Causes:**
1. Re-encoding enabled
2. Too many threads
3. Low RAM
4. Using HDD not SSD

**Solution:**

**Use copy mode (fastest):**
```json
{
  "ffmpeg": {
    "threads": 2,
    "re_encode_video": false,
    "video_codec": "copy"
  }
}
```

**Reduce resource usage:**
```json
{
  "ffmpeg": {
    "threads": 1
  }
}
```

**Process fewer videos:**
```json
{
  "processing": {
    "max_daily_processing": 5,
    "max_processing_time_minutes": 60
  }
}
```

---

## Docker Issues

### Container Won't Start

**Error:**
```
Error response from daemon: invalid mount config
```

**Solution:**
```bash
# Check volume paths exist
ls -la /volume1/movies/original
ls -la /volume1/movies/filtered
ls -la /volume1/docker/cleanvid/config

# Create if missing
mkdir -p /volume1/movies/filtered
mkdir -p /volume1/docker/cleanvid/{config,logs}

# Check docker-compose.yml syntax
docker-compose config
```

### Permission Denied

**Error:**
```
Permission denied: '/output/movie.mkv'
```

**Solution:**
```bash
# Check ownership
ls -la /volume1/movies/filtered

# Fix permissions
chmod -R 755 /volume1/movies/filtered
chown -R 1000:1000 /volume1/movies/filtered

# Or run as root (docker-compose.yml)
user: "0:0"
```

### Volume Not Mounted

**Error:**
```
No such file or directory: '/input'
```

**Solution:**
```bash
# Check mounts
docker inspect cleanvid | grep Mounts

# Verify paths in docker-compose.yml
volumes:
  - /volume1/movies/original:/input:ro  # ← Check this path
  
# Recreate container
docker-compose down
docker-compose up -d
```

---

## Subtitle Issues

### Wrong Language Subtitles

**Problem:** Downloaded Spanish subtitles for English movie

**Solution:**
```json
{
  "opensubtitles": {
    "language": "en"  # ← Set correct language
  }
}
```

**Supported languages:**
- `en` - English
- `es` - Spanish
- `fr` - French
- `de` - German
- `it` - Italian
- [Full list](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)

### Subtitle Sync Issues

**Problem:** Words detected at wrong timestamps

**Causes:**
1. Subtitle file out of sync
2. Wrong subtitle file
3. Different video cut

**Solution:**
```bash
# Verify subtitle matches video
mkvinfo movie.mkv  # Check duration
head -20 movie.srt  # Check subtitle content

# Try different subtitle source
subliminal download -l en movie.mkv --provider opensubtitles

# Manually sync subtitle (use Subtitle Edit tool)
```

### Subtitle Encoding Issues

**Error:**
```
UnicodeDecodeError: 'utf-8' codec can't decode
```

**Solution:**
```bash
# Convert to UTF-8
iconv -f ISO-8859-1 -t UTF-8 movie.srt > movie_utf8.srt
mv movie_utf8.srt movie.srt

# Or use dos2unix
dos2unix movie.srt
```

---

## Word Detection Issues

### Too Many False Positives

**Problem:** "hello" detected because word list has "hell"

**Solution:**
```text
# Be more specific in word list
# Instead of:
hell

# Use:
# hell  (comment out if too broad)

# Or require word boundaries in regex (future feature)
```

**Workaround:**
- Remove broad words from list
- Test on sample video first
- Review muted segments manually

### Word Not Detected

**Problem:** Word in subtitle but not muted

**Causes:**
1. Case sensitivity
2. Word not in list
3. Typo in word list

**Solution:**
```bash
# Check word list
cat /config/profanity_words.txt

# Add word
echo "newword" >> /config/profanity_words.txt

# Verify (case-insensitive by default)
grep -i "word" /config/profanity_words.txt

# Reset and reprocess
cleanvid reset /input/movie.mkv
cleanvid process /input/movie.mkv
```

---

## Output Issues

### Output File Too Large

**Problem:** Filtered file larger than original

**Causes:**
1. Audio re-encoded at higher bitrate
2. Video re-encoded unnecessarily

**Solution:**
```json
{
  "ffmpeg": {
    "audio_codec": "aac",
    "audio_bitrate": "128k",  // ← Lower bitrate
    "re_encode_video": false  // ← Use copy mode
  }
}
```

### Output File Missing

**Problem:** Processing succeeded but no output file

**Solution:**
```bash
# Check output directory
ls -la /output/

# Check processed log
cat /config/processed_log.json | grep movie.mkv

# Check disk space
df -h /output

# Try manual processing
cleanvid process /input/movie.mkv

# Check FFmpeg output
docker logs cleanvid | grep ERROR
```

### Directory Structure Not Preserved

**Problem:** All outputs in root, not in subdirectories

**Causes:**
1. `preserve_structure` disabled
2. Videos outside input_dir

**Solution:**
```python
# This is preserved by default in FileManager
# If custom code, ensure preserve_structure=True
output_path = file_manager.generate_output_path(
    input_path,
    preserve_structure=True  # ← This
)
```

---

## Performance Issues

### Slow Network I/O

**Problem:** Processing slow on network storage

**Solution:**
```bash
# Use local SSD for temporary processing
{
  "paths": {
    "temp_dir": "/tmp/cleanvid"  # Fast local storage
  }
}

# Or reduce network traffic
# Process locally, copy results to NAS
```

### Memory Issues

**Error:**
```
MemoryError: Unable to allocate array
```

**Solution:**
```bash
# Reduce threads
{
  "ffmpeg": {
    "threads": 1
  }
}

# Process one at a time
cleanvid process --max-videos 1

# Increase Docker memory limit
deploy:
  resources:
    limits:
      memory: 4G
```

### CPU Overload

**Symptoms:**
- System very slow
- Other services affected
- High temperature

**Solution:**
```bash
# Limit CPU usage (docker-compose.yml)
deploy:
  resources:
    limits:
      cpus: '2.0'

# Reduce threads
{
  "ffmpeg": {
    "threads": 1
  }
}

# Schedule during off-hours only
# DSM Task Scheduler: Run at 2 AM
```

---

## Debugging

### Enable Debug Logging

```json
{
  "logging": {
    "level": "DEBUG",
    "file": "/logs/cleanvid.log"
  }
}
```

### Collect Debug Information

```bash
# System info
cleanvid --version
python --version
ffmpeg -version

# Configuration
cleanvid config --show
cleanvid config --validate

# Status
cleanvid status

# Recent history
cleanvid history --limit 20

# Logs
docker logs cleanvid
cat /config/processed_log.json
cat /logs/cleanvid.log
```

### Test Individual Components

```python
# Test FFmpeg
from cleanvid.utils import FFmpegWrapper

ffmpeg = FFmpegWrapper()
available, version = ffmpeg.check_available()
print(f"FFmpeg: {available} - {version}")

metadata = ffmpeg.get_metadata("/input/movie.mkv")
print(f"Duration: {metadata.duration_seconds}s")

# Test subtitle parsing
from cleanvid.services import SubtitleManager

sub_mgr = SubtitleManager()
subtitles = sub_mgr.load_subtitle_file("/input/movie.srt")
print(f"Subtitle count: {len(subtitles)}")

# Test profanity detection
from cleanvid.services import ProfanityDetector

detector = ProfanityDetector()
detected = detector.detect_in_text("what the hell")
print(f"Detected: {detected}")
```

---

## Getting Help

### Before Asking for Help

1. **Check documentation:**
   - README.md
   - USER_GUIDE.md
   - DOCKER_DEPLOYMENT.md

2. **Validate configuration:**
   ```bash
   cleanvid config --validate
   ```

3. **Check logs:**
   ```bash
   docker logs cleanvid
   cat /logs/cleanvid.log
   ```

4. **Try minimal test:**
   ```bash
   cleanvid process --max-videos 1
   ```

### Reporting Issues

Include:
- **Cleanvid version:** `cleanvid --version`
- **Environment:** Docker or Python, OS, NAS model
- **Error message:** Complete error output
- **Steps to reproduce:** What you did
- **Expected vs actual:** What should happen vs what happened
- **Configuration:** `cleanvid config --show` (redact passwords)
- **Logs:** Relevant log excerpts

### Community Resources

- **GitHub Issues:** Bug reports and feature requests
- **Discussions:** General questions and help
- **Documentation:** Complete guides and API reference

---

**Still stuck? Open a GitHub issue with debug info!**
