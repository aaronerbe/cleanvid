# Docker Deployment Guide

## Quick Start

### 1. Build the Docker Image

```bash
cd /path/to/cleanvid
docker build -t cleanvid:latest .
```

### 2. Initialize Configuration

```bash
docker run --rm \
  -v /volume1/docker/cleanvid/config:/config \
  cleanvid:latest init
```

### 3. Edit Configuration

```bash
# Edit settings
nano /volume1/docker/cleanvid/config/settings.json

# Edit word list
nano /volume1/docker/cleanvid/config/profanity_words.txt
```

### 4. Run Processing

```bash
docker run --rm \
  -v /volume1/movies/original:/input:ro \
  -v /volume1/movies/filtered:/output \
  -v /volume1/docker/cleanvid/config:/config \
  -v /volume1/docker/cleanvid/logs:/logs \
  cleanvid:latest process --max-time 300
```

---

## Synology Setup

### Method 1: Docker Compose (Recommended)

1. **Create directory structure:**
```bash
mkdir -p /volume1/docker/cleanvid/{config,logs}
```

2. **Copy docker-compose.yml to your NAS:**
```bash
# Upload docker-compose.yml to /volume1/docker/cleanvid/
```

3. **Edit docker-compose.yml paths:**
```yaml
volumes:
  - /volume1/movies/original:/input:ro
  - /volume1/movies/filtered:/output
  - /volume1/docker/cleanvid/config:/config
  - /volume1/docker/cleanvid/logs:/logs
```

4. **Build and initialize:**
```bash
cd /volume1/docker/cleanvid
docker-compose build
docker-compose run --rm cleanvid init
```

5. **Edit configuration:**
```bash
nano /volume1/docker/cleanvid/config/settings.json
```

6. **Set up scheduled processing (DSM Task Scheduler):**
- **Task Name:** Cleanvid Nightly Processing
- **User:** root
- **Schedule:** Daily at 00:00
- **Command:**
```bash
docker exec cleanvid cleanvid process --max-time 300
```

### Method 2: Docker Container (Manual)

1. **Pull/Build image:**
```bash
docker build -t cleanvid:latest /path/to/cleanvid
```

2. **Create container:**
```bash
docker create \
  --name=cleanvid \
  -v /volume1/movies/original:/input:ro \
  -v /volume1/movies/filtered:/output \
  -v /volume1/docker/cleanvid/config:/config \
  -v /volume1/docker/cleanvid/logs:/logs \
  -e TZ=America/New_York \
  --restart unless-stopped \
  cleanvid:latest
```

3. **Initialize:**
```bash
docker exec cleanvid cleanvid init
```

4. **Configure:**
```bash
nano /volume1/docker/cleanvid/config/settings.json
```

5. **Schedule processing:**
Same as Method 1.

---

## Configuration

### Required Settings

Edit `/volume1/docker/cleanvid/config/settings.json`:

```json
{
  "processing": {
    "max_daily_processing": 9999,
    "max_processing_time_minutes": 300,
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
    "language": "en",
    "username": "your_username",
    "password": "your_password",
    "api_key": null
  },
  "ffmpeg": {
    "threads": 2,
    "audio_codec": "aac",
    "audio_bitrate": "192k",
    "re_encode_video": false
  }
}
```

### Word List

Edit `/volume1/docker/cleanvid/config/profanity_words.txt`:

```text
# Add your profanity words, one per line
damn
hell
shit
f*ck
```

---

## Usage

### Check Status
```bash
docker exec cleanvid cleanvid status
```

### Process Videos
```bash
# Process batch (respects config limits)
docker exec cleanvid cleanvid process

# Process with time limit (5 hours)
docker exec cleanvid cleanvid process --max-time 300

# Process with video limit
docker exec cleanvid cleanvid process --max-videos 10

# Process single video
docker exec cleanvid cleanvid process /input/Action/movie.mkv

# Force reprocess all
docker exec cleanvid cleanvid process --force
```

### View History
```bash
docker exec cleanvid cleanvid history
docker exec cleanvid cleanvid history --limit 50
```

### Reset Video
```bash
docker exec cleanvid cleanvid reset /input/movie.mkv
```

### Validate Configuration
```bash
docker exec cleanvid cleanvid config --validate
docker exec cleanvid cleanvid config --show
```

---

## Synology Task Scheduler Setup

### Nightly Processing (Recommended)

**Control Panel → Task Scheduler → Create → Scheduled Task → User-defined script**

**General:**
- Task: Cleanvid Nightly Processing
- User: root
- Enabled: ✓

**Schedule:**
- Date: Daily
- Time: 00:00 (midnight)

**Task Settings:**
- User-defined script:
```bash
docker exec cleanvid cleanvid process --max-time 300
```

**Result:** Processes from midnight to 5 AM every night

### Alternative: Multiple Time Windows

**Early Morning (2 AM - 6 AM):**
```bash
docker exec cleanvid cleanvid process --max-time 240
```

**Late Night (11 PM - 2 AM):**
```bash
docker exec cleanvid cleanvid process --max-time 180
```

---

## Volume Mounts Explained

| Container Path | Your NAS Path | Purpose | Mode |
|----------------|---------------|---------|------|
| `/input` | `/volume1/movies/original` | Source videos | Read-only |
| `/output` | `/volume1/movies/filtered` | Filtered videos | Read-write |
| `/config` | `/volume1/docker/cleanvid/config` | Configuration | Read-write |
| `/logs` | `/volume1/docker/cleanvid/logs` | Log files | Read-write |

---

## Troubleshooting

### Check Logs
```bash
docker logs cleanvid
cat /volume1/docker/cleanvid/logs/cleanvid.log
```

### Container Not Starting
```bash
docker logs cleanvid
docker exec -it cleanvid /bin/bash
```

### FFmpeg Not Found
```bash
docker exec cleanvid which ffmpeg
docker exec cleanvid ffmpeg -version
```

### Permission Issues
```bash
# Check volume permissions
ls -la /volume1/docker/cleanvid/config
ls -la /volume1/movies/filtered

# Fix if needed
chmod -R 755 /volume1/docker/cleanvid
chmod -R 755 /volume1/movies/filtered
```

### Configuration Errors
```bash
docker exec cleanvid cleanvid config --validate
```

### Reset Everything
```bash
docker stop cleanvid
docker rm cleanvid
rm -rf /volume1/docker/cleanvid/config/*
# Then start over from Step 1
```

---

## Performance Tips

### For Faster Processing:
```json
{
  "ffmpeg": {
    "threads": 4,              // Use more CPU cores
    "re_encode_video": false   // Keep copy mode (faster)
  }
}
```

### For Smaller Files:
```json
{
  "ffmpeg": {
    "threads": 2,
    "re_encode_video": true,   // Re-encode video
    "video_codec": "libx265",  // HEVC codec
    "video_crf": 23            // Quality (lower = better)
  }
}
```

### Resource Limits (docker-compose.yml):
```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'      // Max 4 CPU cores
      memory: 4G       // Max 4GB RAM
```

---

## Monitoring Progress

### Watch Live Processing
```bash
docker logs -f cleanvid
tail -f /volume1/docker/cleanvid/logs/cleanvid.log
```

### Check Processed Count
```bash
docker exec cleanvid cleanvid status
```

### View Processing History
```bash
docker exec cleanvid cleanvid history --limit 10
```

---

## Backup

### Backup Configuration
```bash
cd /volume1/docker/cleanvid
tar -czf cleanvid-config-$(date +%Y%m%d).tar.gz config/
```

### Backup Processed Log
```bash
cp /volume1/docker/cleanvid/config/processed_log.json \
   /volume1/docker/cleanvid/config/processed_log.json.backup
```

---

## Updates

### Update Container
```bash
cd /volume1/docker/cleanvid
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Update Configuration
```bash
docker exec cleanvid cleanvid init  # Reinitialize (safe, won't overwrite)
```

---

## Complete Example Workflow

```bash
# 1. Build
docker build -t cleanvid /path/to/cleanvid

# 2. Initialize
docker run --rm -v /volume1/docker/cleanvid/config:/config cleanvid init

# 3. Configure
nano /volume1/docker/cleanvid/config/settings.json
nano /volume1/docker/cleanvid/config/profanity_words.txt

# 4. Create container
docker create \
  --name=cleanvid \
  -v /volume1/movies/original:/input:ro \
  -v /volume1/movies/filtered:/output \
  -v /volume1/docker/cleanvid/config:/config \
  -v /volume1/docker/cleanvid/logs:/logs \
  cleanvid

# 5. Test
docker exec cleanvid cleanvid status
docker exec cleanvid cleanvid process --max-videos 1

# 6. Schedule (DSM Task Scheduler)
docker exec cleanvid cleanvid process --max-time 300
```

Done! Your movies will be filtered every night! 🎬
