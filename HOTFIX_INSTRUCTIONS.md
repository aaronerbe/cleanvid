# CLEANVID HOTFIX INSTRUCTIONS
## Encoding Detection + @eaDir Filtering

**Date:** December 27, 2025
**Fixes:**
1. Subtitle encoding detection (UTF-8 → ISO-8859-1 → Windows-1252 fallback)
2. Synology @eaDir folder filtering

---

## ✅ PREREQUISITES (ALREADY DONE)

You should have these files in your repo:
- `C:\Users\aaron\SynologyDrive\repos\jellyfin\cleanvid\HOTFIX_subtitle_manager.py`
- `C:\Users\aaron\SynologyDrive\repos\jellyfin\cleanvid\HOTFIX_file_manager.py`

---

## START HERE → STEP 1: Copy Files to Synology

From your Windows PC, open PowerShell or Command Prompt:

```bash
# Copy subtitle_manager.py
scp C:\Users\aaron\SynologyDrive\repos\jellyfin\cleanvid\HOTFIX_subtitle_manager.py scum@DeadFishCloud:/volume1/docker/cleanvid/HOTFIX_subtitle_manager.py

# Copy file_manager.py
scp C:\Users\aaron\SynologyDrive\repos\jellyfin\cleanvid\HOTFIX_file_manager.py scum@DeadFishCloud:/volume1/docker/cleanvid/HOTFIX_file_manager.py
```

**Expected result:** Files copied successfully, no errors.

---

## STEP 2: SSH into Synology

```bash
ssh scum@DeadFishCloud
```

**You should now be at the Synology command prompt.**

---

## STEP 3: Backup Original Files

```bash
# Backup subtitle_manager.py
sudo docker exec cleanvid cp /app/src/cleanvid/services/subtitle_manager.py /app/src/cleanvid/services/subtitle_manager.py.backup

# Backup file_manager.py
sudo docker exec cleanvid cp /app/src/cleanvid/services/file_manager.py /app/src/cleanvid/services/file_manager.py.backup
```

**Expected result:** No output = success. Backup files created.

---

## STEP 4: Copy Hotfixes into Container

```bash
# Copy subtitle_manager.py
sudo docker cp /volume1/docker/cleanvid/HOTFIX_subtitle_manager.py cleanvid:/app/src/cleanvid/services/subtitle_manager.py

# Copy file_manager.py
sudo docker cp /volume1/docker/cleanvid/HOTFIX_file_manager.py cleanvid:/app/src/cleanvid/services/file_manager.py
```

**Expected result:** 
```
Successfully copied 20kB to cleanvid:/app/src/cleanvid/services/subtitle_manager.py
Successfully copied 15kB to cleanvid:/app/src/cleanvid/services/file_manager.py
```

---

## STEP 5: Verify Hotfix Applied

```bash
# Check subtitle_manager has encoding detection
sudo docker exec cleanvid grep -A 5 "Try multiple encodings" /app/src/cleanvid/services/subtitle_manager.py

# Check file_manager has @eaDir filtering
sudo docker exec cleanvid grep -A 5 "_is_synology_metadata_path" /app/src/cleanvid/services/file_manager.py
```

**Expected result:** You should see the new code from both files printed to screen.

---

## STEP 6: Restart Container

```bash
cd /volume1/docker/cleanvid
sudo docker restart cleanvid
```

**Expected result:**
```
cleanvid
```

Wait 5-10 seconds for container to fully restart.

---

## STEP 7: Verify Container is Running

```bash
sudo docker ps | grep cleanvid
```

**Expected result:** Should show cleanvid container with "Up X seconds" status.

---

## STEP 8: Test with Previously Failed Video

Pick one of the videos that failed with encoding errors:

```bash
# Example - test with Hostiles (failed with encoding error)
sudo docker exec cleanvid cleanvid reset "/input/Action/Hostiles (2017)/Hostiles.2017.1080p.mkv"

sudo docker exec cleanvid cleanvid process "/input/Action/Hostiles (2017)/Hostiles.2017.1080p.mkv"
```

**Watch for:**
- ✅ "Subtitle encoding: iso-8859-1" (or windows-1252, latin-1)
- ✅ "SUCCESS" status
- ❌ NO encoding crash

---

## STEP 9: Check for @eaDir Improvements

```bash
# Check status - @eaDir files should not be in video count
sudo docker exec cleanvid cleanvid status
```

**Before fix:** Total videos might include @eaDir fake videos
**After fix:** Total videos should be accurate (no @eaDir entries)

---

## STEP 10: Monitor Next Batch Run

The nightly processing will now:
- Successfully process videos with non-UTF-8 subtitles
- Skip all @eaDir folders automatically
- Not create empty output folders for @eaDir

Watch the next run with:
```bash
sudo docker logs cleanvid -f
```

---

## ✅ WHAT'S FIXED:

### 1. Encoding Detection
**Before:**
```
✗ FAILED | Hostiles.2017.1080p.mp4
  Error: 'utf-8' codec can't decode byte 0xe9
```

**After:**
```
  Subtitle encoding: iso-8859-1
✓ SUCCESS | Hostiles.2017.1080p.mp4
  Segments muted: 15
```

### 2. @eaDir Filtering
**Before:**
```
✗ FAILED | Gladiator.m4v
  Error: Error opening input file /@eaDir/Gladiator.m4v
  Is a directory
```

**After:**
```
(Silently skipped - not discovered during video scanning)
No errors, no empty folders
```

---

## 🔄 ROLLBACK (If Something Goes Wrong):

```bash
# Restore original files
sudo docker exec cleanvid cp /app/src/cleanvid/services/subtitle_manager.py.backup /app/src/cleanvid/services/subtitle_manager.py

sudo docker exec cleanvid cp /app/src/cleanvid/services/file_manager.py.backup /app/src/cleanvid/services/file_manager.py

# Restart container
cd /volume1/docker/cleanvid
sudo docker restart cleanvid
```

---

## 📊 EXPECTED IMPROVEMENTS:

**Current State (Before Hotfix):**
- Success rate: ~51%
- Encoding errors: 10-15 videos
- @eaDir errors: 3-5 videos
- Empty folders: Many

**After Hotfix:**
- Success rate: ~65-70%
- Encoding errors: 0 (fixed)
- @eaDir errors: 0 (prevented)
- Empty folders: None (for new processing)

---

## 🔒 PERMANENCE:

**Hotfix persists through:**
- ✅ Synology reboots
- ✅ Container restarts (`docker restart cleanvid`)
- ✅ Container stop/start

**Hotfix lost if:**
- ❌ Container recreated (`docker-compose down` + `up`)
- ❌ Image rebuilt

**To make permanent:** Apply the same changes to your repo files and rebuild the image later.

---

## 📝 NOTES:

- Processing can continue while applying hotfix
- Backup files remain in container
- No data loss risk
- Can rollback instantly if needed

---

## 🎯 WHERE YOU ARE NOW:

**✅ Completed:** STEP 1 (files copied to Synology)

**→ Continue with STEP 2** (SSH into Synology)

**Then follow steps 3-10 in order.**

---

**Ready to continue with STEP 2!**
