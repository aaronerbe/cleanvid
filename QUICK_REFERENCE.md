# Cleanvid 2.0 - Quick Reference

**Version:** 2.0 (Web Dashboard)  
**Container:** cleanvid2  
**Port:** 8080

---

## Web Dashboard

**URL:** http://DeadFishCloud:8080

**Pages:**
- Overview - System stats
- History - Processing log
- Settings - Configuration
- Manual Process - Trigger processing

---

## Common Commands

### Container Management
```bash
# Start/stop/restart
cd /volume1/docker/cleanvid2
sudo docker-compose up -d
sudo docker-compose stop
sudo docker-compose restart

# View logs
sudo docker logs cleanvid2
sudo docker logs cleanvid2 -f  # Follow mode
```

### Processing
```bash
# Check status
sudo docker exec cleanvid2 cleanvid status

# Process videos
sudo docker exec cleanvid2 cleanvid process --max-videos 10
sudo docker exec cleanvid2 cleanvid process --max-time 120

# View history
sudo docker exec cleanvid2 cleanvid history --limit 20

# Reset video for reprocessing
sudo docker exec cleanvid2 cleanvid reset "/input/path/to/video.mkv"
```

### Configuration
```bash
# View config
sudo docker exec cleanvid2 cleanvid config --show

# Edit settings
nano /volume1/docker/cleanvid2-config/settings.json

# Edit profanity words
nano /volume1/docker/cleanvid2-config/profanity_words.txt
```

---

## Scheduled Task

**Task:** Cleanvid Nightly Processing  
**Schedule:** Daily at 00:00 (midnight)  
**Command:**
```bash
docker exec cleanvid2 cleanvid process --max-time 720
```

---

## Troubleshooting

### Dashboard shows wrong stats
```bash
cd /volume1/docker/cleanvid2
sudo docker-compose restart
```

### Container won't start
```bash
# Check logs
sudo docker logs cleanvid2

# Verify docker-compose.yml
cat docker-compose.yml
```

### Port 8080 already in use
```bash
# Find what's using it
sudo netstat -tlnp | grep 8080

# Change port in docker-compose.yml
# ports: "8081:8080"
```

---

## API Endpoints

```bash
# Status
curl http://localhost:8080/api/status

# History
curl http://localhost:8080/api/history?limit=10

# Config
curl http://localhost:8080/api/config
```

---

## File Locations

**Config:** `/volume1/docker/cleanvid2-config/`
- settings.json
- profanity_words.txt
- processed_log.json

**Logs:** `/volume1/docker/cleanvid2-logs/`
- cleanvid.log

**Source:** `/volume1/docker/cleanvid2/`

**Videos:**
- Input: `/volume1/Videos/`
- Output: `/volume1/Videos-Filtered/`

---

## Deployment Quick Steps

1. **Windows:** Create tarball
   ```powershell
   cd C:\Users\aaron\SynologyDrive\repos\jellyfin\cleanvid
   tar -czf cleanvid.tar.gz *
   ```

2. **Upload:** Via File Station to `/docker/`

3. **Extract:**
   ```bash
   cd /volume1/docker
   sudo mkdir cleanvid2
   tar -xzf cleanvid.tar.gz -C cleanvid2
   ```

4. **Build:**
   ```bash
   cd cleanvid2
   sudo docker build -t cleanvid:2.0 .
   ```

5. **Start:**
   ```bash
   sudo docker-compose up -d
   ```

---

## Version History

**2.0 (Dec 28, 2025)**
- ✅ Added web dashboard
- ✅ Flask API with 7 endpoints
- ✅ Real-time stats and history
- ✅ Manual processing interface

**1.0 (Dec 25, 2025)**
- ✅ CLI-only version
- ✅ Automated subtitle download
- ✅ FFmpeg video processing
- ✅ OpenSubtitles integration
