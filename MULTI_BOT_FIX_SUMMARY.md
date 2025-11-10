# Multi-Bot File Storage Fix

## Problem Statement
When files were posted in a channel with multiple bots, only bot 0's file ID was being stored in the database (b_1 column). Other bots' file IDs were not being captured (b_2, b_3, etc. remained NULL).

**Example of the issue:**
```
Log: Inserted new file AgADrQYAAhgj6UU with b_1 = BAACAgEAAyEFAATA8Lz2...
Database: b_1 ✅ | b_2 ❌ | b_3 ❌ | ... (only b_1 populated)
```

## Root Cause
The media handler was only registered on `StreamBot` (the base bot, bot 0). When messages were posted in channels:
- StreamBot received and processed messages → stored in b_1
- Multi-clients (bot 1, 2, 3...) never received messages → b_2, b_3... stayed NULL
- This happened because handlers were not registered on multi-clients

## Solution Implemented

### 1. Refactored Media Handler (`/app/WebStreamer/bot/plugins/media_handler.py`)

**Changes:**
- Created `store_channel_media()` function with parameters:
  - `bot_index`: Which bot is processing (0-10)
  - `should_reply`: Whether to send user-facing reply message
  
- **Base bot (bot 0):** Stores file_id in b_1 AND sends reply message
- **Multi-clients (bot 1-10):** Store file_ids in b_2 to b_11 silently (no reply)

- Added `register_multi_client_handlers()` function:
  - Dynamically registers handlers on all multi-clients
  - Uses proper closure to capture bot_index for each handler
  - Logs registration for verification

**Key code snippet:**
```python
async def store_channel_media(client, message: Message, bot_index: int, should_reply: bool = False):
    # ... stores file with correct bot_index
    logging.info(f"[Bot {bot_index + 1}] Stored media: {file_name} ...")
    
    # Only reply if this is the base bot
    if should_reply:
        await message.reply_text(reply_text, reply_markup=keyboard)
```

### 2. Updated Client Initialization (`/app/WebStreamer/bot/clients.py`)

**Changes:**
- After multi_clients are initialized, calls `register_multi_client_handlers()`
- Ensures all bots have handlers registered before processing messages
- Logs how many additional bots got handlers registered

**Key code snippet:**
```python
if len(multi_clients) != 1:
    Var.MULTI_CLIENT = True
    print("Multi-Client Mode Enabled")
    
    # Register media handlers on all multi clients
    from WebStreamer.bot.plugins.media_handler import register_multi_client_handlers
    register_multi_client_handlers()
    print(f"Registered media handlers on {len(multi_clients) - 1} additional bot(s)")
```

## How It Works Now

### Flow Diagram:
```
File posted in channel
         ↓
    ┌────┴────┐
    ↓         ↓
  Bot 0     Bot 1 ... Bot N
    ↓         ↓         ↓
Stores in  Stores in  Stores in
  b_1       b_2  ...    b_N
    ↓         ↓         ↓
  Sends    Silent    Silent
  Reply
    ↓
Database: b_1 ✅ | b_2 ✅ | b_3 ✅ | ... (all populated!)
```

### Example Database Result:
```sql
unique_file_id    | b_1                          | b_2                          | b_3
------------------+------------------------------+------------------------------+--------
AgADrQYAAhgj6UU   | BAACAgEAAyEFAATA8Lz2...     | BAACAgEAAyEFABBB9Mx3...     | ...
```

### Example Logs:
```
[INFO] Multi-Client Mode Enabled
[INFO] Registered media handlers on 2 additional bot(s)
[INFO] Registered media handler on bot 2 (b_2)
[INFO] Registered media handler on bot 3 (b_3)
...
[INFO] [Bot 1] Stored media: video.mp4 (unique_id: AgADrQYAAhgj6UU, file_id: BAACAgE...)
[INFO] [Bot 2] Stored media: video.mp4 (unique_id: AgADrQYAAhgj6UU, file_id: BAACAgE...)
[INFO] [Bot 3] Stored media: video.mp4 (unique_id: AgADrQYAAhgj6UU, file_id: BAACAgE...)
```

## Deployment Instructions

### For Production:

1. **Deploy the code:**
   ```bash
   # Pull latest changes
   git pull origin main
   
   # Or if you're using a different deployment method
   # copy the updated files to production
   ```

2. **Restart the bot service:**
   ```bash
   # If using systemd
   sudo systemctl restart webstreamer
   
   # If using PM2
   pm2 restart webstreamer
   
   # If running manually
   pkill -f "python -m WebStreamer"
   python -m WebStreamer &
   
   # If using Docker
   docker-compose restart
   ```

3. **Verify logs:**
   ```bash
   # Check for successful handler registration
   tail -f /path/to/logs/streambot.log | grep "Registered media handler"
   
   # Expected output:
   # Registered media handler on bot 2 (b_2)
   # Registered media handler on bot 3 (b_3)
   ```

## Verification Steps

### 1. Post a Test File
Post any video/audio/document in your channel where all bots are members.

### 2. Check Database
```bash
# Connect to your database
psql $DATABASE_URL

# Query latest file
SELECT unique_file_id, b_1, b_2, b_3, b_4, b_5, file_name 
FROM media_files 
ORDER BY created_at DESC 
LIMIT 1;
```

**Expected Result:**
- ✅ Multiple b_X columns should have values (not NULL)
- ✅ Each bot stores its own unique file_id

### 3. Check Logs
```bash
# Look for storage confirmations from all bots
grep "Stored media" /path/to/logs/streambot.log | tail -5
```

**Expected Output:**
```
[Bot 1] Stored media: test.mp4 (unique_id: AgAD...)
[Bot 2] Stored media: test.mp4 (unique_id: AgAD...)
```

### 4. Verify User Experience
- ✅ Only ONE reply message appears (from base bot)
- ✅ File can be streamed from any available bot
- ✅ Load balancing works across all bots

## Benefits

1. **Load Distribution:** Files can now be streamed from any bot, distributing load
2. **Redundancy:** If one bot goes down, others have the file_id
3. **Scalability:** Supports 1-11 bots dynamically
4. **Better Performance:** Random bot selection for streaming reduces per-bot load

## Troubleshooting

### Issue: Only b_1 is populated after fix

**Possible causes:**
1. ❌ Not all bots are added as members to the channel
2. ❌ Handlers didn't register (check logs)
3. ❌ Bots don't have proper permissions
4. ❌ Service wasn't restarted after code changes

**Solutions:**
1. Verify all bots are channel members with admin rights
2. Check logs for "Registered media handler on bot X"
3. Ensure all bots have "Post messages" permission
4. Restart the service completely

### Issue: No messages being processed

**Check:**
1. Are bots online? Check with BotFather
2. Is DATABASE_URL correct and accessible?
3. Are environment variables (MULTI_TOKEN_X) set correctly?
4. Check bot logs for connection errors

## Technical Details

### Handler Registration
- Uses Pyrogram's `MessageHandler` with proper filters
- Handlers are added to each client's handler list
- Group priority: 1 (standard priority)
- Filters: `(filters.channel | filters.group) & MEDIA_FILTER`

### Thread Safety
- Each bot runs in its own handler context
- Database operations are atomic (PostgreSQL)
- No race conditions between bots storing the same file

### Performance Impact
- Minimal overhead: Each bot processes messages independently
- Database: One UPDATE per bot per file
- No network calls between bots
- Async processing prevents blocking

## Files Modified

1. **`/app/WebStreamer/bot/plugins/media_handler.py`** (62 lines changed)
   - Refactored storage logic
   - Added multi-client handler registration
   - Improved logging

2. **`/app/WebStreamer/bot/clients.py`** (7 lines changed)
   - Added handler registration call
   - Added logging for verification

## Support

If you encounter any issues:
1. Check bot logs: `/var/log/supervisor/` or `streambot.log`
2. Verify database connectivity: `psql $DATABASE_URL -c "SELECT 1;"`
3. Test with a single bot first, then add more
4. Ensure all environment variables are set correctly

---

**Status:** ✅ Fix implemented and ready for deployment
**Version:** 1.0
**Date:** 2025-11-10
