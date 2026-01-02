# Scene Editor Implementation Checklist

**Branch:** feature/scene_edit  
**Started:** 2026-01-01  
**Status:** In Progress

---

## Progress Overview
- **Phase 1:** ✅ Complete
- **Phase 2:** ✅ Complete
- **Phase 3:** ✅ Complete
- **Phase 4:** ✅ Complete
- **Phase 5:** ✅ Complete
- **Phase 6:** ⬜ Testing Pending

---

## Phase 1: Configuration & Data Models

### Task 1.1: Create Scene Data Models ✅
**Status:** Complete  
**Estimated:** 1 hour

**Subtasks:**
- [ ] Create `src/cleanvid/models/scene.py`
- [ ] Implement `ProcessingMode` enum (SKIP, BLUR, BLACK)
- [ ] Implement `SkipZone` class with validation
- [ ] Implement `VideoSceneFilters` class
- [ ] Add timestamp parsing helpers (HH:MM:SS or MM:SS to seconds)
- [ ] Add timestamp display helpers (seconds to HH:MM:SS)
- [ ] Add JSON serialization methods
- [ ] Write unit tests

**Files to create:**
- `src/cleanvid/models/scene.py`

---

### Task 1.2: Update Configuration Schema ⬜
**Status:** Not Started  
**Estimated:** 30 minutes

**Subtasks:**
- [ ] Paths already exist in config.py - verify they're being used
- [ ] Ensure PathConfig has proper validation
- [ ] Test loading existing settings.json

**Files to check:**
- `src/cleanvid/models/config.py`
- `config/settings.json`

---

### Task 1.3: Audit Hardcoded Paths ⬜
**Status:** Not Started  
**Estimated:** 1 hour

**Subtasks:**
- [ ] Search for hardcoded "/input"
- [ ] Search for hardcoded "/output"
- [ ] Search for hardcoded "/config"
- [ ] Replace with config.paths references
- [ ] Test with custom paths

---

## Phase 2: Scene Manager Backend

### Task 2.1: Create Scene Manager Service ⬜
**Status:** Not Started  
**Estimated:** 2 hours

**Subtasks:**
- [ ] Create `src/cleanvid/services/scene_manager.py`
- [ ] Implement `load_scene_filters()`
- [ ] Implement `save_scene_filters()` with auto-backup
- [ ] Implement `get_video_filters(video_path)`
- [ ] Implement `add_skip_zone(video_path, zone)`
- [ ] Implement `update_skip_zone(video_path, zone_id, zone)`
- [ ] Implement `delete_skip_zone(video_path, zone_id)`
- [ ] Implement `delete_video_filters(video_path)`
- [ ] Implement `get_all_videos_with_filters()`
- [ ] Add JSON validation
- [ ] Write unit tests

**Files to create:**
- `src/cleanvid/services/scene_manager.py`

---

### Task 2.2: Create Scene Processor Service ⬜
**Status:** Not Started  
**Estimated:** 3 hours

**Subtasks:**
- [ ] Create `src/cleanvid/services/scene_processor.py`
- [ ] Implement `generate_blur_filter(zones)` for FFmpeg
- [ ] Implement `generate_black_filter(zones)` for FFmpeg
- [ ] Implement `combine_video_filters(blur_zones, black_zones)`
- [ ] Implement `apply_scene_filters(input, output, zones, mute_ranges)`
- [ ] Test FFmpeg filter generation
- [ ] Test actual video processing with blur
- [ ] Test actual video processing with black
- [ ] Write unit tests

**Files to create:**
- `src/cleanvid/services/scene_processor.py`

---

### Task 2.3: Create Queue Manager ⬜
**Status:** Not Started  
**Estimated:** 1 hour

**Subtasks:**
- [ ] Create `src/cleanvid/services/queue_manager.py`
- [ ] Implement `load_queue()`
- [ ] Implement `save_queue(queue)`
- [ ] Implement `add_to_queue(video_path)`
- [ ] Implement `remove_from_queue(video_path)`
- [ ] Implement `get_queue()`
- [ ] Implement `clear_queue()`
- [ ] Write unit tests

**Files to create:**
- `src/cleanvid/services/queue_manager.py`

---

## Phase 3: API Endpoints

### Task 3.1: Add Scene Filter Endpoints ⬜
**Status:** Not Started  
**Estimated:** 2 hours

**Subtasks:**
- [ ] Add `GET /api/scene-filters`
- [ ] Add `GET /api/scene-filters/<path:video_path>`
- [ ] Add `POST /api/scene-filters/<path:video_path>`
- [ ] Add `DELETE /api/scene-filters/<path:video_path>`
- [ ] Add `DELETE /api/scene-filters/<path:video_path>/<zone_id>`
- [ ] Add input validation
- [ ] Add error handling
- [ ] Test with curl

**Files to modify:**
- `src/cleanvid/web/app.py`

---

### Task 3.2: Add Queue Endpoints ⬜
**Status:** Not Started  
**Estimated:** 1.5 hours

**Subtasks:**
- [ ] Add `GET /api/scene-queue`
- [ ] Add `POST /api/scene-queue`
- [ ] Add `POST /api/scene-queue/process`
- [ ] Add `DELETE /api/scene-queue/<path:video_path>`
- [ ] Test queue operations

**Files to modify:**
- `src/cleanvid/web/app.py`

---

## Phase 4: Scene Editor UI

### Task 4.1: Create Scene Editor HTML Page ⬜
**Status:** Not Started  
**Estimated:** 3 hours

**Subtasks:**
- [ ] Create `src/cleanvid/web/static/scene_editor.html`
- [ ] Add header with back button
- [ ] Add video browser section
- [ ] Add skip zone form (timestamp inputs, description, mode radio, mute checkbox)
- [ ] Add skip zone preview list
- [ ] Add action buttons (Process Now, Add to Queue)
- [ ] Add queue viewer modal
- [ ] Style with Tailwind CSS

**Files to create:**
- `src/cleanvid/web/static/scene_editor.html`

---

### Task 4.2: Implement Scene Editor JavaScript ⬜
**Status:** Not Started  
**Estimated:** 3 hours

**Subtasks:**
- [ ] Implement `loadVideos()` - Browse video library
- [ ] Implement `selectVideo(path)` - Load existing filters
- [ ] Implement `addSkipZone()` - Add new zone to list
- [ ] Implement `editSkipZone(id)` - Edit existing zone
- [ ] Implement `deleteSkipZone(id)` - Remove zone
- [ ] Implement timestamp validation (HH:MM:SS format)
- [ ] Implement end > start validation
- [ ] Implement mode selection logic (enable/disable mute)
- [ ] Implement `saveFilters()` - Save to API
- [ ] Implement `processNow()` - Trigger immediate processing
- [ ] Implement `addToQueue()` - Add to queue
- [ ] Implement queue management UI

**Files to modify:**
- `src/cleanvid/web/static/scene_editor.html` (embedded JS)

---

### Task 4.3: Add Scene Editor Link to Dashboard ⬜
**Status:** Not Started  
**Estimated:** 15 minutes

**Subtasks:**
- [ ] Add "Scene Editor" button to dashboard
- [ ] Link to /scene_editor.html
- [ ] Style consistently
- [ ] Test navigation

**Files to modify:**
- `src/cleanvid/web/static/dashboard.html`

---

## Phase 5: Video Processing Integration

### Task 5.1: Integrate Scene Processing ⬜
**Status:** Not Started  
**Estimated:** 2 hours

**Subtasks:**
- [ ] Modify `video_processor.py` to load scene filters
- [ ] Extract blur zones, black zones, mute zones
- [ ] Merge scene mute zones with profanity mute segments
- [ ] Apply FFmpeg blur/black filters
- [ ] Update processing result with scene info
- [ ] Ensure backward compatibility
- [ ] Test combined profanity + scene processing

**Files to modify:**
- `src/cleanvid/services/video_processor.py`

---

### Task 5.2: Update Processing Log ⬜
**Status:** Not Started  
**Estimated:** 1 hour

**Subtasks:**
- [ ] Add `scene_zones_processed` to log
- [ ] Add `scene_zones_count` to log
- [ ] Add `has_custom_scenes` boolean
- [ ] Update dashboard to show scene info
- [ ] Test log entries

**Files to modify:**
- `src/cleanvid/services/file_manager.py`
- `src/cleanvid/web/static/dashboard.html`

---

## Phase 6: Testing & Documentation

### Task 6.1: Integration Testing ⬜
**Status:** Not Started  
**Estimated:** 2 hours

**Subtasks:**
- [ ] Test end-to-end scene editing workflow
- [ ] Test video processing with blur mode
- [ ] Test video processing with black mode
- [ ] Test video processing with skip mode
- [ ] Test mute combinations
- [ ] Test queue processing
- [ ] Test combined profanity + scene filtering

---

### Task 6.2: Documentation ⬜
**Status:** Not Started  
**Estimated:** 1 hour

**Subtasks:**
- [ ] Update README with Scene Editor section
- [ ] Create example scene_filters.json
- [ ] Document FFmpeg requirements
- [ ] Create user guide
- [ ] Update API documentation

**Files to modify:**
- `README.md`

**Files to create:**
- `examples/scene_filters_example.json`
- `docs/SCENE_EDITOR.md`

---

## Summary

**Total Estimated Time:** ~24 hours

**Current Status:**
- Tasks Completed: 0/18
- Overall Progress: 0%

---

## Notes

- Working on feature/scene_edit branch
- All file paths use config references
- Backward compatible with existing profanity filtering
- JSON files auto-backed up before modification
- FFmpeg filters tested for performance
- UI follows existing Tailwind CSS patterns

---

## Next Steps

1. Start with Phase 1: Create scene data models
2. Build scene manager backend
3. Add API endpoints
4. Create UI
5. Integrate with video processing
6. Test and document

---

**Last Updated:** 2026-01-01 (Initial creation)
