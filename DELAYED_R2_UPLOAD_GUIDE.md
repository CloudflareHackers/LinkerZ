# Delayed R2 Upload Strategy - Implementation Guide

## Overview

The bot now uses a **delayed upload strategy** to ensure all bot file_ids are collected before uploading to R2. This prevents multiple R2 writes for the same file and ensures R2 always has complete data.

## Problem Solved

### Before (Immediate Upload)
```
Bot 1 sees file → Upload to R2 (only b_1_file_id)
Bot 2 sees file → Update PostgreSQL (R2 still missing b_2_file_id) ❌
Bot 3 sees file → Update PostgreSQL (R2 still missing b_3_file_id) ❌
Result: R2 has incomplete data!
```

### After (Delayed Upload)
```
Bot 1 sees file → Store in DB → Schedule R2 upload (15s delay)
Bot 2 sees file → Store in DB → Skip scheduling (already scheduled)
Bot 3 sees file → Store in DB → Skip scheduling
...
After 15s → Collect ALL bot file_ids from DB → Upload to R2 ONCE ✅
Result: R2 has complete data with all bot file_ids!
```

## How It Works

### 1. Tracking Mechanism

```python
# Global set to track files with pending R2 uploads
pending_r2_uploads = set()

# R2 upload delay (configurable)
R2_UPLOAD_DELAY = 15  # seconds
```

### 2. First Bot Detection

When a bot sees a new file:

```python
is_first_bot = unique_file_id not in pending_r2_uploads

if is_first_bot:
    # Mark as pending
    pending_r2_uploads.add(unique_file_id)
    
    # Schedule delayed upload task
    asyncio.create_task(delayed_r2_upload(...))
else:
    # Another bot already scheduled the upload
    # Just store in database
```

### 3. Delayed Upload Task

```python
async def delayed_r2_upload(unique_file_id, ...):
    # Wait for all bots to report
    await asyncio.sleep(15)
    
    # Fetch ALL bot file_ids from database
    file_data = db.get_file_ids(unique_file_id)
    
    # Build complete bot_file_ids dict
    bot_file_ids = {
        "b_1_file_id": "...",
        "b_2_file_id": "...",
        "b_3_file_id": "...",
        ...
    }
    
    # Upload to R2 with ALL bot file_ids
    r2.upload_file_data(unique_file_id, data)
    
    # Remove from pending
    pending_r2_uploads.remove(unique_file_id)
```

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     TELEGRAM CHANNEL                             │
│                    File Posted (Same File)                       │
└──────────┬────────────┬────────────┬─────────────────────────────┘
           │            │            │
    ┌──────▼──────┐ ┌──▼──────┐ ┌───▼─────┐
    │   Bot 1     │ │  Bot 2  │ │  Bot 3  │  ... (up to Bot 11)
    │ t=0s        │ │ t=1s    │ │ t=2s    │
    └──────┬──────┘ └──┬──────┘ └───┬─────┘
           │           │            │
           │           │            │
    ┌──────▼───────────▼────────────▼───────────────────────┐
    │           media_handler.py (per bot)                   │
    │                                                         │
    │  Bot 1:                                                │
    │  • Check R2: Not found                                 │
    │  • Store in PostgreSQL (b_1)                           │
    │  • Check pending_r2_uploads: Empty                     │
    │  • Add unique_file_id to pending_r2_uploads            │
    │  • Schedule delayed_r2_upload task (15s)               │
    │                                                         │
    │  Bot 2:                                                │
    │  • Check R2: Not found (upload not done yet)           │
    │  • Store in PostgreSQL (b_2)                           │
    │  • Check pending_r2_uploads: Already present!          │
    │  • Skip scheduling (already scheduled by Bot 1)        │
    │                                                         │
    │  Bot 3:                                                │
    │  • Check R2: Not found                                 │
    │  • Store in PostgreSQL (b_3)                           │
    │  • Check pending_r2_uploads: Already present!          │
    │  • Skip scheduling                                     │
    └─────────────────────────────────────────────────────────┘
                              │
                              │ Time passes...
                              │
    ┌─────────────────────────▼─────────────────────────────┐
    │         t = 15s: Delayed Upload Task Executes         │
    │                                                         │
    │  1. Wake up after 15 second delay                      │
    │  2. Query PostgreSQL for unique_file_id                │
    │  3. Get ALL bot file_ids (b_1, b_2, b_3, ...)         │
    │  4. Format R2 data with complete bot_file_ids          │
    │  5. Upload to R2 (SINGLE write with ALL data)          │
    │  6. Remove from pending_r2_uploads                     │
    └─────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────┐
    │                 R2 Storage (Complete Data)              │
    │                                                         │
    │  {                                                      │
    │    "unique_id": "AgAD-A0AAij8UVE",                     │
    │    "bot_file_ids": {                                   │
    │      "b_1_file_id": "BQACAgQ...",  ← From Bot 1        │
    │      "b_2_file_id": "BQACAgQ...",  ← From Bot 2        │
    │      "b_3_file_id": "BQACAgQ...",  ← From Bot 3        │
    │      ...                                                │
    │    },                                                   │
    │    ...                                                  │
    │  }                                                      │
    └─────────────────────────────────────────────────────────┘
```

## Timeline Example

```
Time    Event                                           Database State       R2 State
─────── ─────────────────────────────────────────────── ──────────────────── ────────────
T+0s    Bot 1 sees file AgAD-A0AAij8UVE                b_1: BQACAgQ...      (empty)
        → Stores in DB
        → Schedules R2 upload (t+15s)
        → pending_r2_uploads: {AgAD-A0AAij8UVE}

T+1s    Bot 2 sees same file                           b_1: BQACAgQ...      (empty)
        → Stores in DB                                  b_2: BQACAgQ...
        → Sees pending, skips scheduling
        → pending_r2_uploads: {AgAD-A0AAij8UVE}

T+2s    Bot 3 sees same file                           b_1: BQACAgQ...      (empty)
        → Stores in DB                                  b_2: BQACAgQ...
        → Sees pending, skips scheduling               b_3: BQACAgQ...
        → pending_r2_uploads: {AgAD-A0AAij8UVE}

T+3s    Bot 4 sees same file                           b_1: BQACAgQ...      (empty)
        → Stores in DB                                  b_2: BQACAgQ...
        → Sees pending, skips scheduling               b_3: BQACAgQ...
        → pending_r2_uploads: {AgAD-A0AAij8UVE}        b_4: BQACAgQ...

T+15s   Delayed upload task executes                   b_1: BQACAgQ...      Complete!
        → Queries database                              b_2: BQACAgQ...      {
        → Gets all 4 bot file_ids                       b_3: BQACAgQ...        b_1_file_id,
        → Uploads to R2 (ONCE)                          b_4: BQACAgQ...        b_2_file_id,
        → Removes from pending                                                 b_3_file_id,
        → pending_r2_uploads: {}                                               b_4_file_id
                                                                             }
```

## Configuration

### Delay Time

The delay is configurable in `media_handler.py`:

```python
# R2 upload delay in seconds (wait for all bots to see the file)
R2_UPLOAD_DELAY = 15
```

**Considerations:**
- **Too short** (< 5s): May miss slower bots
- **Too long** (> 30s): Unnecessary wait, delayed R2 backup
- **Recommended**: 10-15 seconds for most setups

### Adjusting the Delay

Edit `/app/WebStreamer/bot/plugins/media_handler.py`:

```python
# Change this value
R2_UPLOAD_DELAY = 20  # Increase to 20 seconds if needed
```

## Benefits

### 1. Single R2 Write Per File
- **Before**: Multiple uploads (one per bot) ❌
- **After**: Single upload with all data ✅

### 2. Complete Data in R2
- **Before**: R2 only has first bot's file_id
- **After**: R2 has all bot file_ids

### 3. Database Updated Immediately
- Each bot stores its file_id in PostgreSQL instantly
- No waiting for other bots
- Local data always available

### 4. No Race Conditions
- `pending_r2_uploads` set prevents duplicate scheduling
- Thread-safe with asyncio

### 5. Efficient Resource Usage
- Reduced R2 API calls
- Lower bandwidth consumption
- Better cost efficiency

## User Experience

### New File Message (First Bot)

```
📁 File Stored Successfully

Name: Movie.2020.1080p.mkv
Size: 1.65 GB
Type: video/x-matroska
Location: DC 4

⏱️ Collecting all bot IDs... R2 upload in 15s

🔗 View and download at: https://your-domain.com/files/AgAD...

[📥 View File]
```

### New File Message (Subsequent Bots)

```
📁 File Stored Successfully

Name: Movie.2020.1080p.mkv
Size: 1.65 GB
Type: video/x-matroska
Location: DC 4

🔗 View and download at: https://your-domain.com/files/AgAD...

[📥 View File]
```

(No mention of R2 upload delay since it's already scheduled)

## Monitoring

### Log Messages to Watch

```bash
# First bot sees file
[Bot 1] New file detected: AgAD-A0AAij8UVE
[Bot 1] Scheduling R2 upload in 15s: AgAD-A0AAij8UVE

# Other bots see same file
[Bot 2] New file detected: AgAD-A0AAij8UVE
[Bot 2] R2 upload already scheduled by another bot: AgAD-A0AAij8UVE

[Bot 3] New file detected: AgAD-A0AAij8UVE
[Bot 3] R2 upload already scheduled by another bot: AgAD-A0AAij8UVE

# After delay
[R2 Upload] Waiting 15s for all bots to report: AgAD-A0AAij8UVE
[R2 Upload] Collected 3 bot file_ids for AgAD-A0AAij8UVE
[R2 Upload] Successfully uploaded to R2 with 3 bot file_ids: AgAD-A0AAij8UVE
[R2 Upload] Removed from pending: AgAD-A0AAij8UVE
```

### Viewing Logs

```bash
# View all logs
tail -f streambot.log

# Filter R2 upload logs
tail -f streambot.log | grep "R2 Upload"

# Filter specific file
tail -f streambot.log | grep "AgAD-A0AAij8UVE"
```

## Edge Cases Handled

### 1. R2 Check Returns 404 Initially
- Multiple bots may all get "not found" from R2
- All try to schedule upload
- Only first bot actually schedules (set prevents duplicates)
- ✅ Handled correctly

### 2. Bot Crashes Before Delay Completes
- Task is lost, R2 never receives upload
- Next time file is posted: R2 check fails → reschedule
- ✅ Self-healing on retry

### 3. File Already in R2
- All bots check R2 first
- If found: skip upload, just update database
- ✅ No unnecessary work

### 4. Partial Bot Reporting
- Some bots see file, others don't
- After 15s: upload with whatever was collected
- Better than no upload at all
- ✅ Graceful degradation

## Testing

### Manual Test

1. **Setup**: Configure multiple bots in your environment
2. **Action**: Post a file in a channel where all bots are added
3. **Observe**: Check logs for:
   - First bot scheduling upload
   - Other bots skipping schedule
   - After 15s: upload with all bot file_ids

### Test Script

```bash
cd /app
python3 test_delayed_r2_upload.py
```

Shows conceptual flow and expected behavior.

## Troubleshooting

### Multiple R2 Uploads for Same File

**Symptom**: Logs show multiple "Successfully uploaded to R2" for same file

**Cause**: Race condition in checking pending_r2_uploads

**Solution**: Already handled with set-based tracking (should not occur)

### Missing Bot File IDs in R2

**Symptom**: R2 has b_1 and b_2, but missing b_3

**Cause**: Bot 3 reported after the 15-second delay

**Solution**: 
- Increase `R2_UPLOAD_DELAY` (e.g., to 20 seconds)
- Or ensure all bots are equally fast

### R2 Upload Never Happens

**Symptom**: Logs show "Scheduling R2 upload" but never "Successfully uploaded"

**Cause**: Task was cancelled or bot restarted

**Solution**: 
- Check for bot crashes in logs
- Ensure bot stays running for at least 15 seconds after file post
- Next file post will self-heal (reschedule upload)

## Code Reference

### Key Components

1. **`pending_r2_uploads`**: Set tracking scheduled uploads
2. **`R2_UPLOAD_DELAY`**: Configurable delay time (15s)
3. **`delayed_r2_upload()`**: Async task that waits and uploads
4. **`store_channel_media()`**: Main handler with scheduling logic

### File Location

All code in: `/app/WebStreamer/bot/plugins/media_handler.py`

## Summary

✅ **Single R2 write per file** (not multiple)  
✅ **Complete data in R2** (all bot file_ids)  
✅ **Immediate database updates** (per bot)  
✅ **No race conditions** (set-based tracking)  
✅ **Configurable delay** (currently 15 seconds)  
✅ **Self-healing** (reschedules on retry)  
✅ **Efficient** (reduced API calls)

The delayed upload strategy ensures R2 always has complete, accurate data while minimizing unnecessary writes.
