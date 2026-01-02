# Product Requirements Document: Scene Editor Feature

**Feature Name:** Custom Scene Skip Editor  
**Version:** 1.0  
**Date:** January 1, 2026  
**Status:** In Progress

---

## 1. Overview

### 1.1 Purpose
Enable users to define custom timestamp ranges to skip during video playback (sex scenes, violence, nudity, etc.) with options for audio muting, video blurring, or video blacking out.

### 1.2 Goals
- Provide user-friendly interface for managing scene skip zones
- Support multiple skip zones per video
- Offer flexible processing options (skip only, blur, black out, mute)
- Store skip zones in portable JSON format for sharing
- Maintain backward compatibility with existing profanity filtering

### 1.3 Non-Goals
- Automatic scene detection (future feature)
- Integration with external scene databases
- Real-time video preview during editing

---

## 2. User Stories

**US-1:** As a user, I want to browse my video library and select a movie to edit  
**US-2:** As a user, I want to add multiple skip zones with start/end timestamps  
**US-3:** As a user, I want to label each skip zone with a description (e.g., "sex scene", "violence")  
**US-4:** As a user, I want to choose how to handle each skip zone (skip/blur/black/mute)  
**US-5:** As a user, I want to process videos immediately or queue them for batch processing  
**US-6:** As a user, I want to export/import scene definitions for sharing  
**US-7:** As a user, I want to configure custom input/output directories

---

## 3. Functional Requirements

### 3.1 Scene Editor UI

#### 3.1.1 Video Selection
- **REQ-001:** Dashboard must have "Scene Editor" button in main navigation
- **REQ-002:** Scene Editor page must show file browser for video selection
- **REQ-003:** File browser must respect configured input directory
- **REQ-004:** File browser must filter for video file extensions

#### 3.1.2 Skip Zone Management
- **REQ-005:** Interface must allow adding multiple skip zones per video
- **REQ-006:** Each skip zone must have:
  - Start timestamp (HH:MM:SS or MM:SS format)
  - End timestamp (HH:MM:SS or MM:SS format)
  - Description field (free-form text, max 200 chars)
  - Processing mode (radio buttons: Skip Only / Blur / Black Out)
  - Mute audio checkbox (only enabled when Blur or Black Out selected)
- **REQ-007:** Interface must validate that end timestamp > start timestamp
- **REQ-008:** Interface must allow editing existing skip zones
- **REQ-009:** Interface must allow deleting skip zones
- **REQ-010:** Interface must show preview of all skip zones for selected video

#### 3.1.3 Processing Options
- **REQ-011:** User must be able to choose:
  - "Process Now" - immediate processing
  - "Add to Queue" - queue for batch processing
- **REQ-012:** Queue must be viewable and editable
- **REQ-013:** Batch processing must process all queued videos

### 3.2 Data Storage

#### 3.2.1 Scene Filters File
- **REQ-014:** Skip zones stored in `/config/scene_filters.json`
- **REQ-015:** JSON structure:
```json
{
  "/input/Movies/Terminator.mkv": {
    "title": "The Terminator",
    "skip_zones": [
      {
        "id": "uuid-1",
        "start_time": 2723.5,
        "end_time": 2835.0,
        "start_display": "45:23",
        "end_display": "47:15",
        "description": "Sex scene",
        "mode": "black",
        "mute": true
      }
    ],
    "last_modified": "2026-01-01T12:00:00"
  }
}
```

#### 3.2.2 Processing Queue
- **REQ-016:** Queue stored in `/config/scene_processing_queue.json`
- **REQ-017:** Queue items reference videos in scene_filters.json

### 3.3 Configuration

#### 3.3.1 Path Configuration
- **REQ-018:** `settings.json` must include configurable paths:
```json
{
  "paths": {
    "input_dir": "/volume1/video/jellyfin",
    "output_dir": "/volume1/video/jellyfin-clean",
    "config_dir": "/config",
    "logs_dir": "/logs"
  }
}
```
- **REQ-019:** All code must reference paths from config (no hardcoded paths)
- **REQ-020:** Config validation must ensure paths exist or can be created

### 3.4 Video Processing

#### 3.4.1 Processing Modes
- **REQ-021:** "Skip Only" mode: No video modification, audio only from profanity
- **REQ-022:** "Blur" mode: Apply Gaussian blur to video during timestamp range
- **REQ-023:** "Black Out" mode: Replace video with black frames during timestamp range
- **REQ-024:** Mute audio checkbox: Mute audio during blur/black sections (in addition to profanity muting)

#### 3.4.2 Integration with Existing Processing
- **REQ-025:** Scene skip zones processed independently from profanity detection
- **REQ-026:** Both profanity muting and scene processing applied to same output file
- **REQ-027:** Processing log must track both profanity segments and scene skips

### 3.5 API Endpoints

- **REQ-028:** `GET /api/scene-filters` - Get all scene filters
- **REQ-029:** `GET /api/scene-filters/{video_path}` - Get filters for specific video
- **REQ-030:** `POST /api/scene-filters/{video_path}` - Save/update filters for video
- **REQ-031:** `DELETE /api/scene-filters/{video_path}` - Delete all filters for video
- **REQ-032:** `DELETE /api/scene-filters/{video_path}/{zone_id}` - Delete specific zone
- **REQ-033:** `GET /api/scene-queue` - Get processing queue
- **REQ-034:** `POST /api/scene-queue` - Add video to queue
- **REQ-035:** `POST /api/scene-queue/process` - Process entire queue
- **REQ-036:** `DELETE /api/scene-queue/{video_path}` - Remove from queue

---

## 4. Technical Architecture

### 4.1 Backend Components

#### 4.1.1 New Files
- `src/cleanvid/services/scene_manager.py` - Scene filter management
- `src/cleanvid/services/scene_processor.py` - Video processing with blur/black
- `src/cleanvid/models/scene.py` - Data models for skip zones

#### 4.1.2 Modified Files
- `src/cleanvid/web/app.py` - Add scene editor API endpoints
- `src/cleanvid/services/video_processor.py` - Integrate scene processing
- `src/cleanvid/models/config.py` - Add path configuration validation

#### 4.1.3 New Frontend Files
- `src/cleanvid/web/static/scene_editor.html` - Scene editor page

#### 4.1.4 Modified Frontend Files
- `src/cleanvid/web/static/dashboard.html` - Add "Scene Editor" button

### 4.2 FFmpeg Integration

#### 4.2.1 Blur Implementation
```bash
ffmpeg -i input.mp4 \
  -filter_complex "[0:v]boxblur=20:20:enable='between(t,45.5,47.25)'[v]" \
  -map "[v]" -map 0:a output.mp4
```

#### 4.2.2 Black Out Implementation
```bash
ffmpeg -i input.mp4 \
  -filter_complex "[0:v]drawbox=c=black@1:t=fill:enable='between(t,45.5,47.25)'[v]" \
  -map "[v]" -map 0:a output.mp4
```

#### 4.2.3 Combined Processing
- Multiple blur/black zones can be chained
- Audio muting handled separately via existing profanity muting logic

---

## 5. Success Criteria

- [ ] User can browse videos and add skip zones via UI
- [ ] User can choose blur/black/skip modes with optional muting
- [ ] Scene filters persist across container restarts
- [ ] Processed videos correctly blur/black specified ranges
- [ ] Audio mutes correctly when enabled
- [ ] Existing profanity filtering continues to work
- [ ] scene_filters.json is human-readable and shareable
- [ ] All paths configurable via settings.json
- [ ] No hardcoded paths in codebase

---

## 6. Future Enhancements (Out of Scope)

- Automatic scene detection via ML
- Video preview/scrubbing in editor
- Community scene database integration
- Batch import from CSV/spreadsheet
- Per-user scene preferences
- Parental rating system integration

---

## 7. Dependencies

- FFmpeg (already available)
- Python 3.11+ (already available)
- Existing Cleanvid infrastructure

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| FFmpeg blur/black performance impact | Medium | Test on sample files, document performance expectations |
| Complex timestamp input UX | Low | Provide clear format examples, validation |
| Path config breaking existing deployments | High | Provide migration script, default to current paths |
| Scene filters file corruption | Medium | Auto-backup before writes, validate JSON |

---

**Document Version History:**
- v1.0 (2026-01-01): Initial PRD creation
