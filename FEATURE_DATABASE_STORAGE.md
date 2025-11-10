# Database Storage Feature

## Overview
This feature adds PostgreSQL database storage for media files (video, audio, documents) received by the bot(s). It supports up to 11 bots and enables file streaming via unique file IDs.

## Key Features

### 1. Automatic Media Tracking
- Monitors media files (video, audio, documents) sent to bot or posted in channels
- Stores file metadata in PostgreSQL database
- Tracks multiple bot file_ids for the same file

### 2. Multi-Bot Support
- Supports up to 11 bots (b_1 through b_11)
- Each bot stores its own file_id for the same unique file
- Useful when multiple bots are in the same channel

### 3. Download Endpoint
- New endpoint: `/download/<unique_file_id>`
- Streams media files directly using stored file_ids
- Random selection from available bot file_ids
- Automatic fallback if one bot's file_id fails

## Database Schema

```sql
CREATE TABLE media_files (
    unique_file_id TEXT PRIMARY KEY,      -- Telegram's unique file ID
    b_1 TEXT,                              -- File ID from bot 1
    b_2 TEXT,                              -- File ID from bot 2
    b_3 TEXT,                              -- File ID from bot 3
    ...                                     -- Up to b_11
    b_11 TEXT,                             -- File ID from bot 11
    file_name TEXT,                        -- Original filename
    file_size BIGINT,                      -- File size in bytes
    mime_type TEXT,                        -- MIME type (video/mp4, audio/mpeg, etc.)
    created_at TIMESTAMP DEFAULT NOW(),    -- When first stored
    updated_at TIMESTAMP DEFAULT NOW()     -- Last update time
);
```

## How It Works

### Storage Flow
1. Bot receives a media file (video/audio/document)
2. Extract metadata: unique_file_id, file_id, file_name, file_size, mime_type
3. Identify which bot received it (b_1 to b_11)
4. Store in database:
   - If file doesn't exist: Create new record
   - If file exists: Update that bot's file_id column

### Download Flow
1. Client requests: `GET /download/<unique_file_id>`
2. Database lookup: Find all available bot file_ids
3. Random selection: Pick a random bot that has the file
4. Stream file: Use selected bot's file_id to stream
5. Auto-retry: If streaming fails, try next available bot

## API Endpoints

### Download Media File
```
GET /download/<unique_file_id>
```

**Example:**
```bash
curl "https://your-domain.com/download/AgADYQADr6cxGw"
```

**Response:**
- Success (200/206): Media file stream
- Not Found (404): File not in database
- Internal Error (500): All bots failed to stream

**Features:**
- Range requests supported (for video seeking)
- Content-Type based on stored mime_type
- Content-Disposition: inline for video/audio, attachment for documents

## File Types Supported

### Tracked Media Types
- ✅ Video files (`message.video`)
- ✅ Audio files (`message.audio`)
- ✅ Documents (`message.document`)

### Not Tracked
- ❌ Photos (can be added if needed)
- ❌ Voice messages (can be added if needed)
- ❌ Stickers (can be added if needed)

## Configuration

### Environment Variables
Add to `.env` or Heroku config:

```bash
DATABASE_URL=postgresql://user:password@host:port/database
```

### Heroku Setup
```bash
heroku config:set DATABASE_URL="postgresql://user:password@host:port/database"
```

## Files Modified/Created

### New Files
1. `/app/WebStreamer/database.py` - Database operations module
2. `/app/WebStreamer/bot/plugins/media_handler.py` - Media tracking plugin
3. `/app/test_database.py` - Database testing script

### Modified Files
1. `/app/WebStreamer/__main__.py` - Added database initialization
2. `/app/WebStreamer/vars.py` - Added DATABASE_URL configuration
3. `/app/WebStreamer/server/stream_routes.py` - Added /download endpoint
4. `/app/requirements.txt` - Added psycopg2-binary==2.9.11
5. `/app/.env` - Added DATABASE_URL

## Testing

### Test Database Operations
```bash
python3 test_database.py
```

### Test Storage (when bot is running)
1. Send a video/audio/document to the bot
2. Check logs for: `Stored media: <filename> (unique_id: ..., bot: b_1)`
3. Verify in database:
```sql
SELECT * FROM media_files WHERE unique_file_id = 'your_unique_id';
```

### Test Download
```bash
curl -v "https://your-domain.com/download/<unique_file_id>"
```

## Multi-Bot Scenario

### Setup
1. Configure multiple bot tokens (MULTI_CLIENT mode)
2. Add all bots to the same channel
3. Post a media file in the channel

### Expected Behavior
- Each bot receives the file independently
- Each bot stores its own file_id (b_1, b_2, etc.)
- Database record has multiple file_ids for same unique_file_id
- Download endpoint can use any available bot

### Example Database Entry
```
unique_file_id: AgADYQADr6cxGw
b_1: BAADBQAD...xyz123
b_2: BAADBQAD...abc456
b_3: BAADBQAD...def789
file_name: awesome_video.mp4
file_size: 52428800
mime_type: video/mp4
```

## Advantages

### Redundancy
- If one bot's file_id becomes invalid, others still work
- Automatic failover in download endpoint

### Load Distribution
- Random selection distributes load across bots
- Prevents single bot from being overloaded

### Persistence
- Files tracked even if bot restarts
- Historical record of all media files

### Simple API
- Clean `/download/<unique_file_id>` endpoint
- No need to know channel_id or message_id
- Works across multiple channels

## Troubleshooting

### Database Connection Failed
```bash
# Test connection
python3 -c "import psycopg2; psycopg2.connect('DATABASE_URL')"
```

### Files Not Being Stored
1. Check logs for media handler errors
2. Verify DATABASE_URL is set
3. Ensure bot is in the channel
4. Check table exists: `\dt media_files`

### Download Not Working
1. Verify unique_file_id exists in database
2. Check at least one bot file_id is present
3. Ensure bots are running and authenticated
4. Review server logs for streaming errors

## Future Enhancements

### Possible Additions
- [ ] Photo storage support
- [ ] Voice message tracking
- [ ] File search API
- [ ] Statistics endpoint
- [ ] Automatic cleanup of old files
- [ ] File download analytics
- [ ] Duplicate file detection

## Security Notes

### Production Deployment
1. ⚠️ Never commit DATABASE_URL to git
2. ⚠️ Use environment variables for credentials
3. ⚠️ Consider adding authentication to /download endpoint
4. ⚠️ Implement rate limiting on download endpoint
5. ⚠️ Monitor database size and set up retention policies

### Current Implementation
- No authentication on /download endpoint (add if needed)
- No rate limiting (add if needed)
- No file access logging (add if needed)

## Support

For issues or questions:
1. Check Heroku logs: `heroku logs --tail`
2. Check database: `heroku pg:psql`
3. Review error logs in application

---

**Version:** 1.0  
**Date:** November 2025  
**Status:** Production Ready ✅
