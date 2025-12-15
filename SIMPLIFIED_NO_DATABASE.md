# Simplified Telegram File Streamer - No Database

## Changes Made

### 1. Removed PostgreSQL Database Completely
- ✅ Deleted `WebStreamer/database.py`
- ✅ Removed `psycopg2-binary` from `requirements.txt`
- ✅ Removed `DATABASE_URL` from `vars.py`
- ✅ Removed database initialization from `__main__.py`
- ✅ Removed all database calls from code

### 2. Removed Authentication System
- ✅ Deleted `WebStreamer/auth.py`
- ✅ Deleted `WebStreamer/server/auth_routes.py`
- ✅ Server no longer loads auth routes

### 3. Simplified to R2 Storage Only
- ✅ R2 is now the ONLY storage for file metadata
- ✅ Format: `{unique_id, bot_user_id: file_id, file_name, file_size, mime_type, ...}`
- ✅ Multiple bot instances can share same R2 network

### 4. Updated Streaming Routes

#### `/link/{channel_id}/{message_id}` endpoint:
- Gets file properties from Telegram
- Stores metadata in R2 ONLY
- Returns permanent download link: `/dl/{unique_file_id}/{file_id}`
- **No expiry, no database, no auth required**

#### `/dl/{unique_file_id}/{file_id}` endpoint:
- Streams file directly using `file_id`
- Optionally checks R2 for metadata (file_name, size, mime_type)
- **No database lookup required**
- If R2 metadata not found, tries to get from Telegram
- Falls back to defaults if nothing available

### 5. Bot Media Handler
- When bot receives media in channel/group
- Stores metadata in R2 ONLY
- Uses format: `bot_user_id: file_id` as you specified
- No database operations

## Architecture

```
┌─────────────────────────────────────────┐
│  /link/{channel_id}/{message_id}       │
│  - Get file from Telegram               │
│  - Store metadata in R2                 │
│  - Return /dl/{unique_id}/{file_id}     │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│  R2 Storage (Cloudflare)                │
│  {                                       │
│    "unique_id": "ABC123",                │
│    "bot_user_id": "file_id_value",      │ ← Multiple bots can use this
│    "file_name": "video.mp4",             │
│    "file_size_bytes": 123456,            │
│    "mime_type": "video/mp4",             │
│    ...                                   │
│  }                                       │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│  /dl/{unique_file_id}/{file_id}         │
│  - Check R2 for metadata (optional)     │
│  - Stream directly using file_id        │
│  - No database required                 │
└─────────────────────────────────────────┘
```

## How Bot Instances Work with R2

When multiple bot instances save to R2:
```json
{
  "unique_id": "AgADGQcAAnA_eVU",
  "6789123456": "BAACAgUAAyEFAATLvnY0AAIw2Gk...",  ← Bot 1's file_id
  "9876543210": "BAACAgUAAyEFAADifferent_file_id",  ← Bot 2's file_id
  "file_name": "video.mp4",
  "file_size_bytes": 1048576,
  "mime_type": "video/mp4"
}
```

Each bot instance:
- Uses its own Telegram user ID as key
- Stores its own file_id as value
- Can retrieve files using its own file_id
- Shares metadata (name, size, type)

## API Endpoints

### 1. Generate Link
```
GET /link/{channel_id}/{message_id}

Response:
{
  "success": true,
  "download_url": "https://your-domain.com/dl/AgADGQcAAnA_eVU/BAACAgUAAyEFAATLvnY0...",
  "file_info": {
    "unique_file_id": "AgADGQcAAnA_eVU",
    "file_name": "video.mp4",
    "file_size": 1048576,
    "file_size_formatted": "1.00 MB",
    "mime_type": "video/mp4"
  }
}
```

### 2. Stream/Download File
```
GET /dl/{unique_file_id}/{file_id}

- Supports range requests (for video streaming)
- Returns proper filename in Content-Disposition header
- Gets metadata from R2 (if available)
- Streams directly using file_id
```

## File Download Fix

The issue you mentioned (files downloading as "file" instead of proper name) is now fixed:

1. **R2 stores complete metadata** including file_name
2. **`/dl` endpoint checks R2** for metadata first
3. **If R2 has metadata**, proper filename is used
4. **If R2 doesn't have it**, tries Telegram as fallback
5. **Content-Disposition header** is set correctly with filename

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your values
nano .env

# Run the bot
python3 -m WebStreamer
```

## Environment Variables Required

See `.env.example` for full list. Key variables:

- `API_ID` - Telegram API ID
- `API_HASH` - Telegram API hash
- `BOT_TOKEN` - Bot token from @BotFather
- `BIN_CHANNEL` - Channel ID for storing files
- `FQDN` - Your domain name
- `R2_Domain` - R2 API domain
- `R2_Folder` - R2 folder name
- `R2_Public` - R2 public domain

## Testing

### Test link generation:
```bash
curl https://your-domain.com/link/channel_id/message_id
```

### Test file streaming:
```bash
curl -I https://your-domain.com/dl/unique_file_id/file_id
```

The filename should now appear in `Content-Disposition` header!

## Benefits

1. ✅ **No database overhead** - Simpler deployment
2. ✅ **No PostgreSQL required** - Reduced dependencies
3. ✅ **R2 for metadata** - Fast, distributed storage
4. ✅ **Proper filenames** - R2 stores complete metadata
5. ✅ **Direct streaming** - file_id used directly
6. ✅ **Multi-bot support** - Multiple instances can share R2
7. ✅ **No authentication** - Simple public links
8. ✅ **No expiry** - Permanent download links

## Summary

The app is now significantly simpler:
- No PostgreSQL database
- No authentication system  
- R2 storage for metadata only
- Direct file streaming using file_id
- Proper filenames from R2 metadata
- Multiple bot instances supported
