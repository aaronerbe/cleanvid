# Cleanvid Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2025-12-28

### Added
- **Web Dashboard** - Browser-based interface accessible on port 8080
  - Overview page with system stats and video counts
  - History page showing recent processing activity
  - Settings page for viewing configuration
  - Manual Process page for triggering processing on demand
  
- **Flask Web Application** (`src/cleanvid/web/`)
  - `app.py` - Main Flask application with 7 REST API endpoints
  - `static/dashboard.html` - Single-page application UI with Tailwind CSS
  
- **API Endpoints**
  - `GET /api/status` - System status and statistics
  - `GET /api/history` - Processing history with limit parameter
  - `GET /api/config` - Configuration details (read-only)
  - `POST /api/process` - Trigger manual processing
  - `GET /api/logs` - Recent log entries
  - `GET /api/videos` - List of processed/unprocessed videos
  - `POST /api/reset` - Reset video for reprocessing

- **New Dependencies**
  - Flask >=2.3.0 - Web framework
  - Flask-CORS >=4.0.0 - Cross-origin resource sharing

- **Docker Configuration**
  - Added `EXPOSE 8080` in Dockerfile
  - Added port mapping in docker-compose.yml
  - Added `command: web` to start Flask server

### Changed
- Updated `docker-compose.yml` to include port 8080 exposure
- Modified Dockerfile to expose port 8080 for web dashboard
- Container now runs Flask web server by default (command: web)

### Fixed
- **CRITICAL:** Fixed `requirements.txt` line 2 missing `#` comment symbol
  - Before: `Core dependencies for the cleanvid application.`
  - After: `# Core dependencies for the cleanvid application.`
  - This prevented Docker build failures with "Invalid requirement" error

### Documentation
- Added `DEPLOYMENT.md` - Comprehensive deployment guide with step-by-step instructions
- Added `QUICK_REFERENCE.md` - Quick command reference for common operations
- Updated with tarball-based deployment workflow

### Deployment Notes
- Deployed as `cleanvid2` container running alongside original `cleanvid`
- Configuration copied from cleanvid to cleanvid2-config
- Processed log synchronized (297 videos already processed)
- Old cleanvid container stopped, cleanvid2 now handles all processing
- Scheduled task updated to use cleanvid2

### Migration from 1.0
1. Old `cleanvid` container stopped
2. New `cleanvid2` container created with web dashboard
3. Configuration files copied:
   - settings.json (OpenSubtitles credentials)
   - profanity_words.txt (154 words)
   - processed_log.json (297 videos)
4. Scheduled task command changed from:
   - `docker exec cleanvid cleanvid process --max-time 300`
   - To: `docker exec cleanvid2 cleanvid process --max-time 720`

---

## [1.0.0] - 2025-12-25

### Initial Release

#### Core Features
- **CLI Interface** - Command-line tool for video processing
- **Subtitle Management**
  - Automatic subtitle download from OpenSubtitles
  - Support for existing .srt files
  - Multiple encoding support (UTF-8, ISO-8859-1, Windows-1252, Latin-1)
  
- **Profanity Detection**
  - Configurable word list with 154+ profanity words
  - Wildcard support (e.g., f*ck matches variations)
  - Case-insensitive matching
  
- **Video Processing**
  - FFmpeg-based audio muting at profanity timestamps
  - Stream copy mode (no video quality loss)
  - 500ms padding before/after profanity
  - Progress tracking and status reporting
  
- **Configuration Management**
  - JSON-based settings (settings.json)
  - Pydantic validation
  - OpenSubtitles API integration
  
- **Processing Features**
  - Batch processing with video limits
  - Time-based processing limits
  - Processed video tracking (prevents reprocessing)
  - Comprehensive error handling and logging

#### CLI Commands
- `init` - Initialize configuration
- `status` - Show system status
- `process` - Process videos
- `history` - View processing history
- `reset` - Reset video for reprocessing
- `config` - View/edit configuration

#### Docker Support
- Dockerfile for containerized deployment
- docker-compose.yml for easy container management
- Volume mounts for Videos, config, and logs
- Automatic restart on failure

#### Testing
- 620+ unit tests
- 85% code coverage
- 100% type hint coverage
- Zero known bugs at release

#### Dependencies
- Python 3.11
- pysrt - SRT subtitle parsing
- subliminal - Subtitle download
- ffmpeg-python - Video processing wrapper
- pydantic - Data validation
- requests - HTTP client
- babelfish - Language codes
- chardet - Character encoding detection

#### Deployment
- Deployed on Synology NAS via Docker
- Input: /volume1/Videos
- Output: /volume1/Videos-Filtered
- Config: /volume1/docker/cleanvid/config
- Logs: /volume1/docker/cleanvid/logs

#### Limitations
- No web interface (CLI only)
- No real-time processing status
- Manual subtitle download required for failures
- No multi-language support

---

## Development History

### Phase 1-11 (Nov 28 - Dec 25, 2025)
- Initial development and testing
- Core processing engine implementation
- Subtitle manager with encoding fixes
- FFmpeg wrapper development
- Configuration system with Pydantic
- Comprehensive test suite (620+ tests)
- Docker containerization
- Production deployment on Synology

### Hotfixes (Dec 27, 2025)
- Fixed subtitle encoding issues
- Fixed empty subtitle filtering
- Fixed @eaDir metadata directory filtering
- Added clean video copying for non-profanity videos

### Web Dashboard Development (Dec 28, 2025)
- Flask web application created
- REST API with 7 endpoints
- Tailwind CSS-based UI
- Real-time stats and history
- Manual processing interface
- Deployed as cleanvid2

---

## Roadmap

### Planned Features (Future)

#### Priority 1: Failed Video Log
- Separate failed_videos.json log
- CLI commands for failure management
- Retry script for failed videos
- Error type classification

#### Priority 2: Manual Timestamp Support
- manual_timestamps.json configuration
- CLI commands for timestamp management
- Support for videos without subtitles
- Fine-tuning capability

#### Priority 3: Video Quality Options
- Multiple encoding modes (copy, fast, balanced, quality, archive)
- Configurable quality/speed tradeoffs
- HDR/Dolby Vision preservation
- File size optimization options

#### Priority 4: Enhanced Web Dashboard
- Edit configuration via web UI
- Add manual timestamps via UI
- Video player with timestamp marking
- Statistics and reports
- Real-time processing progress

#### Priority 5: Additional Integrations
- Plex/Jellyfin auto-update
- Multiple subtitle source support (Subscene, YIFY)
- Multi-language processing
- Smart profanity detection (ML-based)

---

## Version Numbering

This project uses [Semantic Versioning](https://semver.org/):
- MAJOR version for incompatible API changes
- MINOR version for new features (backwards-compatible)
- PATCH version for bug fixes (backwards-compatible)

Current: **2.0.0**
- Major: 2 (Added web dashboard - significant new feature)
- Minor: 0 (Initial web dashboard release)
- Patch: 0 (No patches yet)
