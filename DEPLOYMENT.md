# Cleanvid 2.0 Deployment Guide

**Date:** December 28, 2025  
**Version:** 2.0 (with Web Dashboard)  
**Deployment Method:** Manual tarball upload to Synology NAS

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Steps](#deployment-steps)
4. [Configuration](#configuration)
5. [Testing & Verification](#testing--verification)
6. [Troubleshooting](#troubleshooting)
7. [Maintenance](#maintenance)

---

## Overview

### What Changed in 2.0

**New Features:**
- 🌐 **Web Dashboard** - Browser-based interface on port 8080
- 📊 **Real-time Stats** - System status, video counts, processing history
- ⚙️ **Settings Viewer** - View configuration without SSH
- 🎬 **Manual Processing** - Trigger video processing from web UI

**Technical Stack:**
- Flask web framework
- REST API with 7 endpoints
- Tailwind CSS UI
- Runs alongside CLI tools

### Architecture

```
cleanvid2 Container (Port 8080)
├── Flask Web Server
│   ├── /api/status
│   ├── /api/history
│   ├── /api/config
│   ├── /api/process
│   └── /static/dashboard.html
└── CLI Tools (cleanvid command)
```

---

## Prerequisites

### Required
- Synology NAS with Docker/Container Manager
- SSH access to Synology
- Windows PC (for creating tarball)
- OpenSubtitles account

### Existing Setup
- Old `cleanvid` container (optional - can coexist)
- Existing configuration files (settings.json, profanity_words.txt)
- Processed video log (processed_log.json)

---

## Deployment Steps

### Phase 1: Prepare Files on Windows

#### Step 1: Navigate to Project Directory

```powershell
cd C:\Users\aaron\SynologyDrive\repos\jellyfin\cleanvid
```

#### Step 2: Verify requirements.txt Fix

**CRITICAL:** Line 2 must have a `#` comment symbol.

Check the file:
```powershell
Get-Content requirements.txt | Select-Object -First 3
```

**Should show:**
```
# Cleanvid - Automated Movie Profanity Filter
# Core dependencies for the cleanvid application.

## Core Processing
```

**If line 2 is missing `#`, the Docker build will fail.**

#### Step 3: Delete Old Tarball

```powershell
del cleanvid.tar.gz
```

#### Step 4: Create New Tarball

```powershell
tar -czf cleanvid.tar.gz *
```

**Expected size:** ~800-900 KB (larger than before due to web dashboard files)

#### Step 5: Verify Tarball Created

```powershell
dir cleanvid.tar.gz
```

---

### Phase 2: Upload to Synology

#### Step 6: Open Synology DSM

1. Browser → `http://DeadFishCloud:5000` (or use IP address)
2. Log in to DSM
3. Open **File Station**

#### Step 7: Navigate to Docker Folder

In File Station left sidebar:
- Click **docker** folder

You should see:
- `cleanvid/` (old container)
- `cleanvid-source/` (old source files)
- `cleanvid.tar.gz` (old tarball)

#### Step 8: Delete Old Tarball

1. Right-click on `cleanvid.tar.gz`
2. Click **Delete**
3. Confirm

#### Step 9: Upload New Tarball

1. Click **Upload** button
2. Click **Select files from computer**
3. Navigate to: `C:\Users\aaron\SynologyDrive\repos\jellyfin\cleanvid\`
4. Select `cleanvid.tar.gz`
5. Click **Open**
6. Wait for upload to complete (~5-10 seconds)

**Verify:** New `cleanvid.tar.gz` appears in docker folder (~878 KB)

---

### Phase 3: Extract and Build on Synology

#### Step 10: SSH to Synology

```bash
ssh scum@DeadFishCloud
```

#### Step 11: Navigate to Docker Directory

```bash
cd /volume1/docker
```

#### Step 12: Verify Tarball Exists

```bash
ls -lh cleanvid.tar.gz
```

**Expected:** `~878K` file

#### Step 13: Create cleanvid2 Directory

```bash
sudo mkdir cleanvid2
```

#### Step 14: Extract Tarball

```bash
tar -xzf cleanvid.tar.gz -C cleanvid2
```

**Note:** You may see warnings about `SCHILY.fflags` - these are harmless.

#### Step 15: Verify Extraction

```bash
ls -la cleanvid2/
```

**Should see:**
- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`
- `src/` directory
- `config/` directory
- `tests/` directory

#### Step 16: Verify Web Dashboard Files

```bash
ls -la cleanvid2/src/cleanvid/web/
```

**Should see:**
- `__init__.py`
- `app.py` (~350 lines)
- `static/` directory with `dashboard.html`

---

### Phase 4: Build Docker Image

#### Step 17: Navigate to cleanvid2 Directory

```bash
cd cleanvid2
```

#### Step 18: Fix requirements.txt (if needed)

**CRITICAL CHECK:** Verify line 2 has `#`

```bash
head -n 5 requirements.txt
```

**Should show:**
```
# Cleanvid - Automated Movie Profanity Filter
# Core dependencies for the cleanvid application.

## Core Processing
```

**If line 2 is missing `#`:**

```bash
nano requirements.txt
# Add # to beginning of line 2
# Save: Ctrl+X, Y, Enter
```

#### Step 19: Build Docker Image

```bash
sudo docker build -t cleanvid:2.0 .
```

**Build time:** 3-5 minutes

**Expected output:**
```
Successfully built [hash]
Successfully tagged cleanvid:2.0
```

**Warnings you can ignore:**
- "DEPRECATED: The legacy builder..." (harmless)
- "WARNING: Running pip as root..." (expected in Docker)

#### Step 20: Verify Image Created

```bash
sudo docker images | grep cleanvid
```

**Should show:**
```
cleanvid  2.0     [hash]  X minutes ago  ~635MB
cleanvid  latest  [hash]  X days ago     ~631MB
```

---

### Phase 5: Setup Configuration

#### Step 21: Create Config/Logs Directories

```bash
cd /volume1/docker
sudo mkdir -p cleanvid2-config cleanvid2-logs
```

#### Step 22: Initialize Configuration

```bash
sudo docker run --rm \
  -v /volume1/docker/cleanvid2-config:/config \
  cleanvid:2.0 init
```

**Expected output:**
```
✓ Configuration initialized at: /config
```

#### Step 23: Copy Configuration from Old cleanvid

**Copy profanity words:**
```bash
sudo cp /volume1/docker/cleanvid/config/profanity_words.txt \
        /volume1/docker/cleanvid2-config/
```

**Copy settings (OpenSubtitles credentials):**
```bash
sudo cp /volume1/docker/cleanvid/config/settings.json \
        /volume1/docker/cleanvid2-config/
```

**Copy processed log (prevent reprocessing):**
```bash
sudo cp /volume1/docker/cleanvid/config/processed_log.json \
        /volume1/docker/cleanvid2-config/
```

#### Step 24: Verify Copies

```bash
# Check profanity word count
wc -l /volume1/docker/cleanvid2-config/profanity_words.txt

# Check OpenSubtitles username
grep "username" /volume1/docker/cleanvid2-config/settings.json

# Check processed video count
grep '"video_path":' /volume1/docker/cleanvid2-config/processed_log.json | wc -l
```

---

### Phase 6: Create docker-compose.yml

#### Step 25: Create docker-compose.yml File

```bash
nano /volume1/docker/cleanvid2/docker-compose.yml
```

**Paste this content:**

```yaml
version: '3.8'

services:
  cleanvid2:
    image: cleanvid:2.0
    container_name: cleanvid2
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - /volume1/Videos:/input
      - /volume1/Videos-Filtered:/output
      - /volume1/docker/cleanvid2-config:/config
      - /volume1/docker/cleanvid2-logs:/logs
    environment:
      - TZ=America/New_York
    command: web
```

**Save:** `Ctrl+X`, `Y`, `Enter`

**Key settings:**
- `ports: "8080:8080"` - Web dashboard access
- `command: web` - Starts Flask web server (not CLI)
- `restart: unless-stopped` - Auto-restart on reboot

#### Step 26: Verify File

```bash
cat /volume1/docker/cleanvid2/docker-compose.yml
```

---

### Phase 7: Start Container

#### Step 27: Start cleanvid2 Container

```bash
cd /volume1/docker/cleanvid2
sudo docker-compose up -d
```

**Expected output:**
```
Creating network "cleanvid2_default" with the default driver
Creating cleanvid2 ... done
```

#### Step 28: Verify Container Running

```bash
sudo docker ps | grep cleanvid2
```

**Expected status:** `Up X seconds` (NOT "Restarting")

**Should show:**
```
[hash]  cleanvid:2.0  "cleanvid web"  ... Up X seconds  0.0.0.0:8080->8080/tcp  cleanvid2
```

#### Step 29: Check Container Logs

```bash
sudo docker logs cleanvid2
```

**Expected output:**
```
Starting Cleanvid web dashboard on http://0.0.0.0:8080
 * Serving Flask app 'cleanvid.web.app'
 * Running on http://127.0.0.1:8080
```

**Warning about "development server" is expected and fine for home use.**

---

## Configuration

### Web Dashboard Access

**URL:** `http://DeadFishCloud:8080`  
**Alternative:** `http://192.168.x.x:8080` (use Synology IP)

### Available Pages

1. **Overview** - System stats, video counts, processing overview
2. **History** - Recent processing activity, successes/failures
3. **Settings** - Configuration viewer (read-only)
4. **Manual Process** - Trigger processing manually

### API Endpoints

```
GET  /api/status      - System status and stats
GET  /api/history     - Processing history (limit parameter)
GET  /api/config      - Configuration details
POST /api/process     - Trigger manual processing
GET  /api/logs        - Recent log entries
GET  /api/videos      - Video list (processed/unprocessed)
POST /api/reset       - Reset video for reprocessing
```

---

## Testing & Verification

### Test 1: Web Dashboard Access

1. Open browser
2. Go to: `http://DeadFishCloud:8080`
3. Verify page loads with Cleanvid branding
4. Check stats show correct numbers

### Test 2: API Status Check

```bash
curl http://localhost:8080/api/status
```

**Should return JSON with:**
- `processed_videos`: (number)
- `unprocessed_videos`: (number)
- `total_videos`: (number)
- `ffmpeg_available`: true

### Test 3: CLI Status Check

```bash
sudo docker exec cleanvid2 cleanvid status
```

**Should show:**
```
============================================================
Cleanvid Status
============================================================
Configuration:
  ✓ Valid
FFmpeg:
  ✓ Available
Videos:
  Total: XXXX
  Processed: XXX
  Unprocessed: XXXX
```

### Test 4: Restart Container

If web dashboard shows wrong stats (cached data):

```bash
cd /volume1/docker/cleanvid2
sudo docker-compose restart
```

Wait 5 seconds, then refresh browser.

---

## Troubleshooting

### Problem: Container Won't Start (Status: Restarting)

**Check logs:**
```bash
sudo docker logs cleanvid2
```

**Common causes:**
- Invalid docker-compose.yml syntax
- Missing volume paths
- Port 8080 already in use

**Solution:**
```bash
sudo docker-compose down
nano docker-compose.yml  # Verify syntax
sudo docker-compose up -d
```

### Problem: Web Dashboard Shows 404

**Check if web server started:**
```bash
sudo docker logs cleanvid2 | grep "Running on"
```

**Should see:** `Running on http://0.0.0.0:8080`

**If not, check the command:**
```bash
sudo docker inspect cleanvid2 | grep -A 5 "Cmd"
```

**Should show:** `"web"`

### Problem: Dashboard Shows Wrong Stats (Cached)

**Solution:** Restart container
```bash
cd /volume1/docker/cleanvid2
sudo docker-compose restart
```

### Problem: Docker Build Fails - "Invalid requirement"

**Error:**
```
ERROR: Invalid requirement: 'Core dependencies for the cleanvid application.'
```

**Cause:** Line 2 of `requirements.txt` is missing `#` comment symbol

**Solution:**
```bash
nano cleanvid2/requirements.txt
# Add # to beginning of line 2
# Save and rebuild
sudo docker build -t cleanvid:2.0 .
```

### Problem: Port 8080 Already in Use

**Check what's using port 8080:**
```bash
sudo netstat -tlnp | grep 8080
```

**Change port in docker-compose.yml:**
```yaml
ports:
  - "8081:8080"  # Use 8081 instead
```

---

## Maintenance

### Scheduled Nightly Processing

**Update existing Synology Task Scheduler task:**

1. DSM → Control Panel → Task Scheduler
2. Find: `Cleanvid Nightly Processing`
3. Edit task
4. Change script to:

```bash
docker exec cleanvid2 cleanvid process --max-time 720
```

**Settings:**
- Run time: `00:00` (midnight)
- Max time: `720` minutes (12 hours)

### Stop Old cleanvid Container

**If keeping both containers:**
```bash
cd /volume1/docker/cleanvid
sudo docker-compose stop
```

**Or disable in Container Manager (DSM GUI)**

### Manual Processing

**Via Web Dashboard:**
1. Go to: `http://DeadFishCloud:8080`
2. Click "Manual Process" tab
3. Enter number of videos or time limit
4. Click "Start Processing"

**Via CLI:**
```bash
# Process 10 videos
sudo docker exec cleanvid2 cleanvid process --max-videos 10

# Process for 2 hours
sudo docker exec cleanvid2 cleanvid process --max-time 120
```

### View Logs

**Container logs:**
```bash
sudo docker logs cleanvid2 -f  # Follow mode
sudo docker logs cleanvid2 --tail 50  # Last 50 lines
```

**Application logs:**
```bash
cat /volume1/docker/cleanvid2-logs/cleanvid.log
```

### Update Configuration

**Edit settings.json:**
```bash
nano /volume1/docker/cleanvid2-config/settings.json
```

**Edit profanity words:**
```bash
nano /volume1/docker/cleanvid2-config/profanity_words.txt
```

**No restart needed** - changes take effect immediately for new processing.

### Upgrade to New Version

**When new code is available:**

1. Create new tarball on Windows
2. Upload to Synology
3. Extract to `cleanvid2/` (overwrite)
4. Rebuild image:
   ```bash
   cd /volume1/docker/cleanvid2
   sudo docker build -t cleanvid:2.1 .
   ```
5. Update docker-compose.yml image tag
6. Restart container:
   ```bash
   sudo docker-compose down
   sudo docker-compose up -d
   ```

---

## Command Reference

### Container Management

```bash
# Start container
cd /volume1/docker/cleanvid2
sudo docker-compose up -d

# Stop container
sudo docker-compose stop

# Restart container
sudo docker-compose restart

# Remove container
sudo docker-compose down

# View logs
sudo docker logs cleanvid2
sudo docker logs cleanvid2 -f  # Follow mode
```

### CLI Commands

```bash
# Status
sudo docker exec cleanvid2 cleanvid status

# History
sudo docker exec cleanvid2 cleanvid history --limit 20

# Process videos
sudo docker exec cleanvid2 cleanvid process --max-videos 10
sudo docker exec cleanvid2 cleanvid process --max-time 120

# Reset video
sudo docker exec cleanvid2 cleanvid reset "/input/path/to/video.mkv"

# Config
sudo docker exec cleanvid2 cleanvid config --show
```

### API Calls

```bash
# Status
curl http://localhost:8080/api/status

# History
curl http://localhost:8080/api/history?limit=10

# Config
curl http://localhost:8080/api/config

# Trigger processing (POST)
curl -X POST http://localhost:8080/api/process \
  -H "Content-Type: application/json" \
  -d '{"max_videos": 5}'
```

---

## Directory Structure

```
/volume1/docker/
├── cleanvid/                    # Old container (stopped)
│   ├── config/
│   │   ├── settings.json
│   │   ├── profanity_words.txt
│   │   └── processed_log.json
│   ├── logs/
│   └── docker-compose.yml
│
├── cleanvid2/                   # New container source
│   ├── src/
│   │   └── cleanvid/
│   │       ├── web/
│   │       │   ├── app.py
│   │       │   └── static/dashboard.html
│   │       ├── services/
│   │       ├── models/
│   │       └── cli/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
│
├── cleanvid2-config/            # Runtime config
│   ├── settings.json
│   ├── profanity_words.txt
│   └── processed_log.json
│
└── cleanvid2-logs/              # Runtime logs
    └── cleanvid.log
```

---

## Deployment Checklist

Use this checklist when deploying to a new system or upgrading:

### Pre-Deployment
- [ ] Windows PC has latest code
- [ ] requirements.txt line 2 has `#` symbol
- [ ] OpenSubtitles credentials available

### Build Phase
- [ ] Tarball created (~800KB)
- [ ] Uploaded to Synology /docker/
- [ ] Extracted to cleanvid2/
- [ ] requirements.txt verified (line 2 has `#`)
- [ ] Docker image built successfully (cleanvid:2.0)

### Configuration Phase
- [ ] Config directories created (cleanvid2-config, cleanvid2-logs)
- [ ] Configuration initialized
- [ ] settings.json copied/configured
- [ ] profanity_words.txt copied
- [ ] processed_log.json copied (if migrating)

### Container Phase
- [ ] docker-compose.yml created
- [ ] Container started
- [ ] Container status = "Up"
- [ ] Logs show Flask server running

### Testing Phase
- [ ] Web dashboard accessible (port 8080)
- [ ] Dashboard shows correct stats
- [ ] API returns valid JSON
- [ ] CLI commands work

### Production Phase
- [ ] Old cleanvid container stopped
- [ ] Scheduled task updated
- [ ] Test processing run successful

---

## Support & Resources

### Documentation
- **QUICKSTART.md** - Full user guide
- **README.md** - Project overview
- **PRD.md** - Product requirements

### Useful Commands
- OpenSubtitles: https://www.opensubtitles.org
- FFmpeg Docs: https://ffmpeg.org/documentation.html
- Docker Docs: https://docs.docker.com
- Flask Docs: https://flask.palletsprojects.com

---

**Last Updated:** December 28, 2025  
**Deployed By:** Aaron  
**Deployment Target:** Synology NAS (DeadFishCloud)  
**Container Name:** cleanvid2  
**Image Tag:** cleanvid:2.0
