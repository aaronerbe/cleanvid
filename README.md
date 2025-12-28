# Cleanvid - Automated Movie Profanity Filter

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Automatically filter profanity from your movie library by analyzing subtitles and muting audio at detected timestamps. Perfect for Jellyfin on Roku devices where real-time filtering isn't possible.

---

## 🎯 Features

- ✅ **Automatic subtitle management** - Finds existing SRT files or downloads from OpenSubtitles
- ✅ **Smart profanity detection** - Customizable word lists with wildcard support (`f*ck` matches variations)
- ✅ **Preserves directory structure** - `Action/movie.mkv` → `Action/movie.mkv`
- ✅ **Time-based processing** - Process overnight (e.g., midnight to 5 AM)
- ✅ **Multi-format support** - MKV, MP4, AVI, MOV, M4V
- ✅ **Fast copy mode** - ~1.5x realtime processing (no re-encoding)
- ✅ **Roku/Jellyfin compatible** - Works on any media player
- ✅ **Docker ready** - Easy Synology NAS deployment
- ✅ **Batch processing** - Automated with daily/time limits
- ✅ **Processing history** - Track what's been processed

---

## 🚀 Quick Start

### Method 1: Docker (Recommended for Synology)

```bash
# 1. Build image
docker build -t cleanvid:latest .

# 2. Initialize configuration
docker run --rm -v /volume1/docker/cleanvid/config:/config cleanvid init

# 3. Edit configuration
nano /volume1/docker/cleanvid/config/settings.json
nano /volume1/docker/cleanvid/config/profanity_words.txt

# 4. Run processing
docker run --rm \
  -v /volume1/movies/original:/input:ro \
  -v /volume1/movies/filtered:/output \
  -v /volume1/docker/cleanvid/config:/config \
  cleanvid process --max-time 300
```

See [DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md) for complete setup.

### Method 2: Python Installation

```bash
# 1. Clone and install
git clone https://github.com/yourusername/cleanvid.git
cd cleanvid
pip install -r requirements.txt
pip install -e .

# 2. Initialize
cleanvid init

# 3. Configure
nano ~/.config/cleanvid/settings.json

# 4. Process videos
cleanvid process --max-time 300
```

---

## 📖 Usage

### Initialize Configuration

```bash
cleanvid init
```

Creates configuration files:
- `settings.json` - Main configuration
- `profanity_words.txt` - Word list
- `processed_log.json` - Processing history

### Check Status

```bash
cleanvid status
```

Shows:
- Configuration validity
- FFmpeg availability
- Video counts (total/processed/unprocessed)
- Library size

### Process Videos

```bash
# Batch processing (respects config limits)
cleanvid process

# Process for 5 hours (midnight to 5 AM)
cleanvid process --max-time 300

# Process up to 10 videos
cleanvid process --max-videos 10

# Process single video
cleanvid process /path/to/movie.mkv

# Force reprocess already processed videos
cleanvid process --force
```

### View History

```bash
# Show recent processing
cleanvid history

# Show last 50 entries
cleanvid history --limit 50
```

### Reset Video

```bash
# Mark video as unprocessed (for reprocessing)
cleanvid reset /path/to/movie.mkv
```

### Configuration Management

```bash
# Validate configuration
cleanvid config --validate

# Show configuration summary
cleanvid config --show
```

---

## ⚙️ Configuration

### settings.json

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
    "input_dir": "/volume1/movies/original",
    "output_dir": "/volume1/movies/filtered",
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
    "video_codec": "copy",
    "re_encode_video": false
  }
}
```

### profanity_words.txt

```text
# One word per line
# Lines starting with # are comments
# Use * as wildcard

damn
hell
shit
f*ck
b*tch
ass
```

**Wildcard matching:**
- `f*ck` matches: fuck, feck, fack, f**k
- `sh*t` matches: shit, shot, shat

---

## 🏠 Synology Setup

### Directory Structure

```
/volume1/movies/original/     # Plex library (input, read-only)
/volume1/movies/filtered/     # Jellyfin library (output)
/volume1/docker/cleanvid/config/   # Configuration files
/volume1/docker/cleanvid/logs/     # Log files
```

### Docker Compose

Create `/volume1/docker/cleanvid/docker-compose.yml`:

```yaml
version: '3.8'

services:
  cleanvid:
    image: cleanvid:latest
    container_name: cleanvid
    volumes:
      - /volume1/movies/original:/input:ro
      - /volume1/movies/filtered:/output
      - /volume1/docker/cleanvid/config:/config
      - /volume1/docker/cleanvid/logs:/logs
    environment:
      - TZ=America/New_York
    restart: unless-stopped
```

### Scheduled Processing

**DSM Task Scheduler:**

1. **Control Panel** → **Task Scheduler** → **Create** → **Scheduled Task**
2. **General:**
   - Task: Cleanvid Nightly Processing
   - User: root
3. **Schedule:**
   - Daily at 00:00 (midnight)
4. **Task Settings:**
   ```bash
   docker exec cleanvid cleanvid process --max-time 300
   ```

**Result:** Processes videos from midnight to 5 AM every night!

---

## 📊 Processing Details

### Speed

**Copy mode (default, no re-encoding):**
- 1080p movie (2 hours): ~3-4 minutes
- 4K movie (2 hours): ~4-6 minutes
- **~1.5x realtime speed**

**5-hour overnight window can process:**
- ~60-100 1080p movies
- ~50-75 4K movies

### File Size

**Copy mode (default):**
- Output file ≈ same size as input
- Audio track replaced, video copied as-is

**Re-encode mode:**
- Can reduce file size 20-50%
- Slower processing (~7.5x realtime)

### Quality

- **Audio:** AAC 192k (configurable)
- **Video:** Bit-perfect copy (default) or H.265 re-encode
- **Subtitles:** Preserved in MKV containers

---

## 🔍 How It Works

1. **Scan library** for unprocessed videos
2. **Find subtitles** (existing SRT or download from OpenSubtitles)
3. **Detect profanity** using regex matching
4. **Generate mute segments** with padding (500ms before/after)
5. **Process video** using FFmpeg audio filters
6. **Preserve structure** (Action/movie.mkv → Action/movie.mkv)
7. **Track progress** in processed_log.json

### Example

**Input subtitle:**
```
00:15:23,000 --> 00:15:25,000
What the hell is going on?
```

**Detection:** "hell" found at 15:23.000

**Mute segment:** 15:22.500 to 15:23.500 (with 500ms padding)

**FFmpeg filter:**
```
volume=enable='between(t,923.5,923.5)':volume=0
```

---

## 📁 Project Structure

```
cleanvid/
├── src/cleanvid/
│   ├── models/          # Data models (Pydantic)
│   ├── services/        # Business logic
│   │   ├── config_manager.py
│   │   ├── profanity_detector.py
│   │   ├── subtitle_manager.py
│   │   ├── video_processor.py
│   │   ├── file_manager.py
│   │   └── processor.py
│   ├── utils/           # Utilities
│   │   └── ffmpeg_wrapper.py
│   └── cli/             # Command-line interface
├── tests/               # 620+ unit tests
├── config/              # Configuration templates
├── docs/                # Documentation
├── Dockerfile           # Docker image
└── docker-compose.yml   # Docker compose
```

---

## 🧪 Development

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=cleanvid --cov-report=html

# Specific test file
pytest tests/services/test_processor.py

# Verbose output
pytest -v
```

### Code Quality

```bash
# Type checking
mypy src/

# Linting
flake8 src/

# Formatting
black src/ tests/
```

---

## 📚 Documentation

- [Docker Deployment Guide](docs/DOCKER_DEPLOYMENT.md) - Complete Synology setup
- [Time-Based Processing](docs/TIME_BASED_PROCESSING.md) - Overnight processing guide
- [Architecture](docs/ARCHITECTURE.md) - System design and components
- [API Reference](docs/API.md) - Python API documentation
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FFmpeg** - Video processing engine
- **OpenSubtitles** - Subtitle database
- **Subliminal** - Subtitle download library
- **pysrt** - SRT parsing library

---

## ⚠️ Disclaimer

This tool is for personal use only. Ensure you have legal rights to modify content in your library. The authors are not responsible for misuse.

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/cleanvid/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/cleanvid/discussions)

---

**Made with ❤️ for family-friendly movie nights**
