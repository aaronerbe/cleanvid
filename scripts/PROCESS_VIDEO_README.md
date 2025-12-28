# PROCESS VIDEO SCRIPT - INSTALLATION

Quick helper script for processing individual videos without dealing with paths.

---

## INSTALL

### Step 1: Copy Script to Synology

From Windows PowerShell:

```bash
scp C:\Users\aaron\SynologyDrive\repos\jellyfin\cleanvid\scripts\process_video.sh scum@DeadFishCloud:/volume1/docker/cleanvid/scripts/process_video.sh
```

---

### Step 2: Make Executable

SSH into Synology:

```bash
ssh scum@DeadFishCloud
chmod +x /volume1/docker/cleanvid/scripts/process_video.sh
```

---

## USAGE

### Basic Usage:

```bash
cd /volume1/docker/cleanvid/scripts
./process_video.sh "movie name"
```

### Examples:

```bash
# Process Hostiles
./process_video.sh "Hostiles"

# Process Free Guy
./process_video.sh "Free Guy"

# Process Ford v Ferrari
./process_video.sh "Ford Ferrari"

# Partial match works too
./process_video.sh "hostile"
./process_video.sh "free"
```

---

## HOW IT WORKS

1. **Searches** for the video file (case-insensitive)
2. **Finds** first match in `/volume1/Videos`
3. **Shows** you what it found
4. **Resets** the video (if already processed)
5. **Processes** the video

---

## EXAMPLES

### Success:
```bash
$ ./process_video.sh "Hostiles"
Searching for: Hostiles

✓ Found: /volume1/Videos/Action/Hostiles (2017)/Hostiles.2017.1080p.mp4

Processing: Hostiles.2017.1080p.mp4
------------------------------------------------------------

✓ Reset processing status for: Hostiles.2017.1080p.mp4
  Video will be reprocessed on next run.

Processing: Hostiles.2017.1080p.mp4
------------------------------------------------------------
  Subtitle encoding: iso-8859-1
  Profanity: 15 detections
  Segments: Creating mute segments...
  FFmpeg: Processing video...
  Status: SUCCESS
```

### Not Found:
```bash
$ ./process_video.sh "Nonexistent Movie"
Searching for: Nonexistent Movie

❌ Video not found: Nonexistent Movie

Tip: Try a shorter search term
Example: Instead of 'Hostiles 2017', try just 'Hostiles'
```

---

## TIPS

**✅ DO:**
- Use short search terms: "Hostiles" instead of "Hostiles 2017"
- Use unique words from the title
- Case doesn't matter: "hostiles" works same as "Hostiles"

**❌ DON'T:**
- Include file extensions: ~~"Hostiles.mp4"~~
- Use full paths: ~~"/volume1/Videos/Action/..."~~
- Include year unless needed: "Hostiles" finds it faster than "Hostiles 2017"

---

## MULTIPLE MATCHES

If multiple movies match, the script picks the **first one found** (alphabetically).

**Example:** Searching "Die Hard" might find:
- Die Hard (1988)
- Die Hard 2 (1990)
- Die Hard 4 (2007)

**Solution:** Be more specific:
```bash
./process_video.sh "Die Hard 2"  # Gets Die Hard 2
```

---

## CREATE ALIAS (OPTIONAL)

To use from anywhere:

```bash
# Add to ~/.bashrc
echo 'alias pv="/volume1/docker/cleanvid/scripts/process_video.sh"' >> ~/.bashrc
source ~/.bashrc

# Now use it anywhere:
pv "Hostiles"
pv "Free Guy"
```

---

## TROUBLESHOOTING

**Script not found:**
```bash
# Check if it exists
ls -la /volume1/docker/cleanvid/scripts/process_video.sh

# Make sure it's executable
chmod +x /volume1/docker/cleanvid/scripts/process_video.sh
```

**Permission denied:**
```bash
# Run as root if needed
sudo /volume1/docker/cleanvid/scripts/process_video.sh "Hostiles"
```

**Video not found but you know it exists:**
- Try shorter search term
- Check spelling
- Video might be in unexpected location

---

**Ready to use! 🚀**
