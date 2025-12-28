# Cleanvid 2.0 - Deployment Plan

## ✅ Changes Already Applied to Repo

All code changes are DONE! The following files have been updated:

1. ✅ **subtitle_manager.py** - Encoding detection + empty subtitle filtering
2. ✅ **file_manager.py** - @eaDir Synology metadata folder filtering  
3. ✅ **video_processor.py** - Clean videos now copied to output
4. ✅ **Web dashboard files created:**
   - `src/cleanvid/web/__init__.py`
   - `src/cleanvid/web/app.py`
   - `src/cleanvid/web/static/dashboard.html`
5. ✅ **requirements.txt** - Added Flask dependencies
6. ✅ **main.py** - Added web command
7. ✅ **Dockerfile** - Added `EXPOSE 8080`
8. ✅ **docker-compose.yml** - Changed to cleanvid2, added port 8080

---

## 🚀 Deployment Steps (What YOU Need to Do)

### Step 1: Commit and Push Changes (Windows/WSL)

```bash
cd /mnt/c/Users/aaron/SynologyDrive/repos/jellyfin/cleanvid

# Check what changed
git status

# Add all changes
git add .

# Commit
git commit -m "feat: Add web dashboard, fix subtitle bugs, copy clean videos

- Add web dashboard with Flask backend and Tailwind UI
- Fix subtitle encoding detection (UTF-8/ISO-8859-1/Windows-1252/Latin-1)
- Fix empty subtitle entry filtering
- Fix @eaDir Synology metadata folder filtering
- Copy clean videos to output instead of skipping
- Update docker-compose to cleanvid2 with port 8080"

# Push to GitHub
git push
```

---

### Step 2: Deploy to Synology (SSH)

```bash
# SSH to Synology
ssh scum@DeadFishCloud

# Navigate to docker folder
cd /volume1/docker

# Create new cleanvid2 directory (copy from existing)
sudo cp -r cleanvid cleanvid2

# Navigate to new directory
cd cleanvid2

# Pull latest code from GitHub
git pull

# Build new Docker image with tag 2.0
sudo docker-compose build

# Start cleanvid2 container
sudo docker-compose up -d

# Verify both containers are running
sudo docker ps | grep cleanvid
```

**You should see TWO containers:**
- `cleanvid` - Old container (still running)
- `cleanvid2` - New container with web dashboard

---

### Step 3: Access Web Dashboard

Open your browser:
```
http://DeadFishCloud:8080
```

---

### Step 4: Test the New Features

1. ✅ **Access the dashboard** - Should load and show system status
2. ✅ **Test Batman Begins** - Should work now (empty subtitle entries filtered)
3. ✅ **Test a clean video** - Should be copied to output folder
4. ✅ **Check @eaDir filtering** - Should skip Synology metadata folders

Test Batman Begins:
```bash
# Inside Synology via SSH
docker exec cleanvid2 cleanvid process "/input/Marvel & DC/Batman Begins/Batman Begins.m4v"
```

---

### Step 5: Monitor Both Containers

Compare old vs new:

```bash
# View logs for cleanvid2
sudo docker logs -f cleanvid2

# Check processing status
docker exec cleanvid2 cleanvid status

# View web dashboard in browser
http://DeadFishCloud:8080
```

---

## Key Differences: cleanvid vs cleanvid2

| Feature | cleanvid (old) | cleanvid2 (new) |
|---------|----------------|-----------------|
| **Encoding Support** | UTF-8 only | UTF-8, ISO-8859-1, Windows-1252, Latin-1 |
| **Empty Subtitles** | Crashes | Filters out empty entries |
| **@eaDir Folders** | Tries to process | Skips automatically |
| **Clean Videos** | Skipped (not in output) | Copied to output |
| **Web Dashboard** | None | Full dashboard at :8080 |
| **Container Name** | cleanvid | cleanvid2 |
| **Image Tag** | cleanvid:latest | cleanvid:2.0 |
| **Port** | None | 8080 |
| **Default Command** | --help | web (dashboard) |

---

## Rollback Plan

If cleanvid2 has issues:

```bash
# SSH to Synology
ssh scum@DeadFishCloud

# Stop cleanvid2
cd /volume1/docker/cleanvid2
sudo docker-compose down

# Old cleanvid container is still running - just use that!
```

Both containers can run simultaneously since they use different:
- Container names (`cleanvid` vs `cleanvid2`)
- Ports (cleanvid has none, cleanvid2 has 8080)
- Docker compose files (separate directories)

---

## Optional: Switch to cleanvid2 as Primary

Once you've tested and cleanvid2 works well:

```bash
# Stop old cleanvid
cd /volume1/docker/cleanvid
sudo docker-compose down

# Rename cleanvid2 to cleanvid (optional)
cd /volume1/docker
sudo mv cleanvid cleanvid-old
sudo mv cleanvid2 cleanvid
cd cleanvid

# Update container name in docker-compose.yml back to "cleanvid"
sudo nano docker-compose.yml
# Change: cleanvid2 -> cleanvid

# Restart
sudo docker-compose down
sudo docker-compose up -d
```

---

## Files Changed Summary

**Bug Fixes:**
- `src/cleanvid/services/subtitle_manager.py` - Encoding + empty entry handling
- `src/cleanvid/services/file_manager.py` - @eaDir filtering
- `src/cleanvid/services/video_processor.py` - Copy clean videos

**Web Dashboard:**
- `src/cleanvid/web/__init__.py` - Package init
- `src/cleanvid/web/app.py` - Flask backend (350 lines)
- `src/cleanvid/web/static/dashboard.html` - Frontend UI (600+ lines)

**Configuration:**
- `requirements.txt` - Added Flask dependencies
- `src/cleanvid/cli/main.py` - Added web command
- `Dockerfile` - Added EXPOSE 8080
- `docker-compose.yml` - Updated to cleanvid2 with port 8080

---

## Summary

**All code is ready in your repo!**

You just need to:
1. Commit and push (Step 1)
2. SSH to Synology and deploy (Step 2)
3. Access dashboard at :8080 (Step 3)
4. Test the new features (Step 4)

**That's it!** 🚀
