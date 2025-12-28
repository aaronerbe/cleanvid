# Product Requirements Document (PRD)
## Cleanvid Automated Movie Filter

**Version:** 1.0  
**Date:** November 28, 2025  
**Author:** Aaron  
**Status:** Development

---

## 1. Executive Summary

### 1.1 Product Vision
An automated, server-side movie filtering system that processes video files to mute profanity based on subtitle analysis, creating family-friendly versions while preserving original files.

### 1.2 Target Users
- Families wanting filtered content on Roku/mobile devices
- Home media server administrators (Synology NAS users)
- Users with dual Plex/Jellyfin setups

### 1.3 Success Criteria
- ✅ Process movies with 95%+ accuracy
- ✅ Auto-download missing subtitles
- ✅ Support multiple video formats (mkv, mp4, avi, mov, m4v)
- ✅ Run unattended on schedule
- ✅ Compatible with all Jellyfin clients (Roku, web, mobile)

---

## 2. Product Overview

### 2.1 Problem Statement
Users want to watch movies on Roku devices with profanity filtered, but:
- Jellyfin plugins cannot control Roku playback
- Real-time filtering requires client-side modifications
- No existing solution works across all devices

### 2.2 Solution
Pre-process video files on Synology NAS to create filtered versions with:
- Muted audio at profanity timestamps
- Cleaned subtitle tracks
- Original video quality preserved
- Separate library structure (Plex = original, Jellyfin = filtered)

### 2.3 Core Value Proposition
- **Works on any client** - No app modifications needed
- **Set and forget** - Automated nightly processing
- **Non-destructive** - Original files untouched
- **Scalable** - Handles libraries of any size

---

## 3. Functional Requirements

### 3.1 Subtitle Management

#### FR-1.1: Subtitle Detection
- **Priority:** P0 (Critical)
- **Description:** Check for existing subtitle files before processing
- **Acceptance Criteria:**
  - Detect .srt, .sub, .ass, .ssa, .vtt files
  - Check for language-tagged subtitles (e.g., movie.en.srt)
  - Detect embedded subtitles using ffprobe
  - Log subtitle availability status

#### FR-1.2: Subtitle Download
- **Priority:** P0 (Critical)
- **Description:** Auto-download subtitles from OpenSubtitles if missing
- **Acceptance Criteria:**
  - Integrate with OpenSubtitles API
  - Support credential configuration
  - Match by movie hash and filename
  - Respect API rate limits (200/day)
  - Retry logic for failed downloads
  - Log download success/failure

#### FR-1.3: Subtitle Parsing
- **Priority:** P0 (Critical)
- **Description:** Parse subtitle files to extract timing and text
- **Acceptance Criteria:**
  - Support SRT format (minimum)
  - Extract start time, end time, text content
  - Handle malformed subtitle entries gracefully
  - UTF-8 encoding support

### 3.2 Profanity Detection

#### FR-2.1: Word List Management
- **Priority:** P0 (Critical)
- **Description:** Configurable profanity word list
- **Acceptance Criteria:**
  - Load from text file (one word per line)
  - Support wildcards (* character)
  - Case-insensitive matching
  - Comments supported (# prefix)
  - Easy to edit and update

#### FR-2.2: Pattern Matching
- **Priority:** P0 (Critical)
- **Description:** Detect profanity in subtitle text
- **Acceptance Criteria:**
  - Match whole words only (avoid false positives)
  - Support wildcard patterns
  - Handle punctuation variations
  - Return timestamp ranges for matches
  - Configurable padding (before/after word)

#### FR-2.3: False Positive Prevention
- **Priority:** P1 (High)
- **Description:** Minimize incorrect muting
- **Acceptance Criteria:**
  - Word boundary detection (avoid "bass" matching "ass")
  - Context-aware matching where possible
  - User-configurable whitelist

### 3.3 Video Processing

#### FR-3.1: Audio Muting
- **Priority:** P0 (Critical)
- **Description:** Mute audio segments using FFmpeg
- **Acceptance Criteria:**
  - Preserve original video stream (no re-encoding)
  - Mute audio at detected timestamps
  - Support multiple audio tracks
  - Configurable audio codec (copy or re-encode)
  - Maintain A/V sync

#### FR-3.2: Subtitle Generation
- **Priority:** P1 (High)
- **Description:** Create "clean" subtitle track
- **Acceptance Criteria:**
  - Replace profanity with asterisks (****)
  - Preserve timing information
  - Save as separate .srt file
  - UTF-8 encoding

#### FR-3.3: Format Support
- **Priority:** P0 (Critical)
- **Description:** Process multiple video formats
- **Acceptance Criteria:**
  - MKV (primary)
  - MP4
  - AVI
  - MOV
  - M4V

### 3.4 File Management

#### FR-4.1: Directory Structure
- **Priority:** P0 (Critical)
- **Description:** Maintain organized file structure
- **Acceptance Criteria:**
  - Mirror input directory structure in output
  - Preserve movie folder organization
  - Create directories as needed
  - Handle nested subdirectories

#### FR-4.2: Processing Log
- **Priority:** P0 (Critical)
- **Description:** Track processed movies
- **Acceptance Criteria:**
  - JSON-based log file
  - Store file hash for deduplication
  - Record processing date/time
  - Track success/failure status
  - Store processing duration
  - Prevent reprocessing

#### FR-4.3: Error Handling
- **Priority:** P0 (Critical)
- **Description:** Graceful failure handling
- **Acceptance Criteria:**
  - Continue processing on single file failure
  - Log detailed error messages
  - Skip corrupted files
  - Report summary statistics

### 3.5 Automation & Scheduling

#### FR-5.1: Batch Processing
- **Priority:** P0 (Critical)
- **Description:** Process multiple movies in one run
- **Acceptance Criteria:**
  - Scan entire input directory
  - Filter already-processed files
  - Configurable batch size limit
  - Process oldest/newest first option

#### FR-5.2: Progress Reporting
- **Priority:** P1 (High)
- **Description:** Provide processing feedback
- **Acceptance Criteria:**
  - Console output for manual runs
  - Detailed log files
  - Processing statistics (success/fail counts)
  - Estimated time remaining

#### FR-5.3: Performance Optimization
- **Priority:** P2 (Medium)
- **Description:** Efficient resource usage
- **Acceptance Criteria:**
  - Configurable CPU thread count
  - Stream processing (avoid full file loads)
  - Incremental processing (resume on failure)

---

## 4. Non-Functional Requirements

### 4.1 Performance
- **NFR-1.1:** Process 1080p 2-hour movie in < 15 minutes
- **NFR-1.2:** CPU usage < 80% during processing
- **NFR-1.3:** Memory usage < 2GB per movie

### 4.2 Reliability
- **NFR-2.1:** 95% success rate on well-formed inputs
- **NFR-2.2:** Graceful degradation on missing subtitles
- **NFR-2.3:** Zero data loss (original files never modified)

### 4.3 Maintainability
- **NFR-3.1:** Object-oriented architecture
- **NFR-3.2:** Comprehensive unit tests (>80% coverage)
- **NFR-3.3:** Clear logging and error messages
- **NFR-3.4:** Modular design for easy updates

### 4.4 Usability
- **NFR-4.1:** Simple configuration (text files)
- **NFR-4.2:** Docker-based deployment
- **NFR-4.3:** Minimal dependencies
- **NFR-4.4:** Clear documentation

### 4.5 Compatibility
- **NFR-5.1:** Python 3.9+
- **NFR-5.2:** FFmpeg dependency
- **NFR-5.3:** Synology Docker support
- **NFR-5.4:** Linux/Unix file systems

---

## 5. Technical Architecture

### 5.1 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Cleanvid Application                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Subtitle   │  │  Profanity   │  │    Video     │     │
│  │   Manager    │  │   Detector   │  │  Processor   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │             │
│         └──────────────────┴──────────────────┘             │
│                          │                                  │
│                ┌─────────────────┐                          │
│                │  File Manager   │                          │
│                └─────────────────┘                          │
│                          │                                  │
│                ┌─────────────────┐                          │
│                │  Config Manager │                          │
│                └─────────────────┘                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Class Structure

#### SubtitleManager
- **Responsibilities:** Subtitle detection, download, parsing
- **Key Methods:**
  - `has_subtitle(video_path) -> bool`
  - `download_subtitle(video_path) -> Path`
  - `parse_subtitle(subtitle_path) -> List[SubtitleEntry]`

#### ProfanityDetector
- **Responsibilities:** Word matching, timestamp generation
- **Key Methods:**
  - `load_word_list(path) -> List[str]`
  - `detect_profanity(subtitles) -> List[MuteSegment]`
  - `merge_overlapping_segments(segments) -> List[MuteSegment]`

#### VideoProcessor
- **Responsibilities:** FFmpeg integration, video muting
- **Key Methods:**
  - `mute_segments(input_path, output_path, segments) -> bool`
  - `create_clean_subtitles(input_srt, output_srt, words) -> bool`

#### FileManager
- **Responsibilities:** File operations, directory management
- **Key Methods:**
  - `find_unprocessed_videos() -> List[Path]`
  - `create_output_path(input_path) -> Path`
  - `is_processed(video_hash) -> bool`
  - `mark_processed(video_hash, metadata) -> None`

#### ConfigManager
- **Responsibilities:** Configuration loading, validation
- **Key Methods:**
  - `load_config() -> Config`
  - `get_word_list() -> List[str]`
  - `get_opensubtitles_creds() -> Credentials`

### 5.3 Data Models

#### SubtitleEntry
```python
@dataclass
class SubtitleEntry:
    index: int
    start_time: float  # seconds
    end_time: float    # seconds
    text: str
```

#### MuteSegment
```python
@dataclass
class MuteSegment:
    start_time: float  # seconds
    end_time: float    # seconds
    word: str
    confidence: float  # 0.0 - 1.0
```

#### ProcessingResult
```python
@dataclass
class ProcessingResult:
    video_path: Path
    success: bool
    duration_seconds: float
    segments_muted: int
    error_message: Optional[str]
```

### 5.4 Technology Stack

- **Language:** Python 3.9+
- **Key Libraries:**
  - `subliminal` - Subtitle download
  - `pysrt` - SRT parsing
  - `ffmpeg-python` - Video processing
  - `pytest` - Testing
  - `pydantic` - Data validation
- **External Tools:**
  - FFmpeg (video/audio processing)
  - FFprobe (media inspection)

---

## 6. Configuration

### 6.1 Configuration Files

#### config/profanity_words.txt
```
# One word per line
# Use * for wildcards
# Lines starting with # are comments
damn
hell
shit
f*ck
```

#### config/settings.json
```json
{
  "processing": {
    "max_daily_processing": 5,
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
    "language": "en"
  },
  "ffmpeg": {
    "threads": 2,
    "audio_codec": "aac",
    "audio_bitrate": "192k",
    "re_encode_video": false
  }
}
```

---

## 7. Deployment

### 7.1 Docker Container

**Base Image:** `python:3.9-slim`

**Additional Packages:**
- ffmpeg
- ffprobe
- Python dependencies

**Volumes:**
- `/input` - Read-only movie library
- `/output` - Filtered movie output
- `/config` - Configuration files
- `/logs` - Log files

**Environment Variables:**
- `PUID` - User ID
- `PGID` - Group ID
- `TZ` - Timezone

### 7.2 Directory Layout

```
/volume1/docker/cleanvid/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── config/
│   ├── settings.json
│   ├── profanity_words.txt
│   ├── opensubtitles_creds.txt
│   └── processed_log.json
├── scripts/
│   └── (generated Python application)
└── logs/
    └── cleanvid.log
```

---

## 8. Testing Strategy

### 8.1 Unit Tests
- Test each class independently
- Mock external dependencies (FFmpeg, OpenSubtitles API)
- Cover edge cases (missing files, malformed data)
- Target: >80% code coverage

### 8.2 Integration Tests
- End-to-end processing of sample video
- Subtitle download verification
- FFmpeg command validation
- Output file verification

### 8.3 Test Data
- Sample video files (various formats)
- Sample subtitle files (with/without profanity)
- Mock OpenSubtitles API responses
- Edge cases (empty files, corrupted data)

---

## 9. Success Metrics

### 9.1 Key Performance Indicators (KPIs)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Processing Success Rate | >95% | Successful / Total Movies |
| Average Processing Time | <15 min/movie | Time per 2-hour 1080p movie |
| Subtitle Availability | >90% | Found/Downloaded subtitles |
| False Positive Rate | <2% | Incorrectly muted segments |
| User Satisfaction | >90% | Feedback survey |

### 9.2 Monitoring

- **Processing Logs:** Track all operations
- **Error Logs:** Capture failures for analysis
- **Performance Metrics:** Processing times, resource usage
- **Summary Reports:** Daily processing statistics

---

## 10. Future Enhancements

### 10.1 Phase 2 Features (Post-MVP)

#### Multi-Severity Levels
- Different word lists (mild, moderate, strict)
- User-selectable filtering strength
- Multiple output directories

#### Advanced Detection
- AI-powered speech recognition (Whisper)
- Scene detection for visual content
- Context-aware word matching

#### User Interface
- Web dashboard for monitoring
- Manual processing triggers
- Word list management UI
- Processing queue visualization

#### Integration
- Jellyfin plugin for metadata
- Plex support
- Notification system (email, Discord, Slack)

### 10.2 Optimization Opportunities
- Parallel processing (multiple movies simultaneously)
- GPU acceleration for video encoding
- Distributed processing across multiple servers
- Incremental subtitle scanning

---

## 11. Risks & Mitigations

### 11.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Subtitle unavailable | High | Medium | Graceful skip, manual upload option |
| FFmpeg compatibility | High | Low | Pin FFmpeg version, test on Synology |
| Processing errors | Medium | Medium | Robust error handling, logging |
| Storage space | High | High | Monitor disk usage, alert system |
| API rate limits | Medium | Low | Cache, respect limits, fallback |

### 11.2 Operational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| False positives | Medium | Medium | Whitelist, user feedback |
| False negatives | Low | Medium | Regular word list updates |
| Performance degradation | Medium | Low | Resource monitoring, optimization |
| User errors | Low | Medium | Clear documentation, validation |

---

## 12. Open Questions

1. **Subtitle Language Support:** Should we support multiple languages beyond English?
2. **Quality Presets:** Should we offer low/medium/high quality output options?
3. **Notification System:** Email alerts for processing completion?
4. **Manual Overrides:** UI for manually specifying mute segments?
5. **Backup Strategy:** Automatic backups of configuration?

---

## 13. Approval & Sign-off

**Product Owner:** Aaron  
**Technical Lead:** Aaron  
**Status:** ✅ Approved for Development

**Start Date:** November 28, 2025  
**Target MVP:** December 15, 2025 (2-3 weeks)

---

## Appendix A: Glossary

- **EDL:** Edit Decision List - File format for specifying edit points
- **FFmpeg:** Open-source video processing tool
- **SRT:** SubRip Text - Common subtitle format
- **Mute Segment:** Time range where audio is silenced
- **Clean Subtitle:** Subtitle with profanity replaced by asterisks

---

## Appendix B: References

- [Cleanvid GitHub](https://github.com/mmguero/cleanvid)
- [Subliminal Docs](https://subliminal.readthedocs.io/)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [OpenSubtitles API](https://www.opensubtitles.com/en/consumers)
