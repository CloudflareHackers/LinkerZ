# R2 Data Structure Update - Implementation Summary

## Overview

Updated the R2 storage integration to send complete file metadata matching the exact structure required by the R2 API.

## Changes Made

### 1. Updated `r2_storage.py`

**File**: `/app/WebStreamer/r2_storage.py`

**Changes**:
- Removed `bot_user_id` parameter from `format_file_metadata()`
- Changed `bot_file_ids` structure from `{bot_user_id: file_id}` to `{"b_1_file_id": file_id}`
- Added new optional parameters:
  - `caption` - Message caption text
  - `file_type` - Type of file ("video", "audio", or "document")
  - `video_duration` - Video duration in seconds
  - `video_width` - Video width in pixels
  - `video_height` - Video height in pixels

**New Data Structure**:
```json
{
  "unique_id": "AgAD-00AAhqIaEg",
  "bot_file_ids": {
    "b_1_file_id": "BAACAgIAAx0CcG2DSwABCs3oaQ9lMYrg..."
  },
  "file_name": "video.mp4",
  "file_size_bytes": 2180655398,
  "mime_type": "video/mp4",
  "original_message_id": 708072,
  "source_channel_id": -1001886225227,
  "caption": "Video caption text",
  "file_type": "video",
  "video_duration_seconds": 2829,
  "video_width": 1920,
  "video_height": 1080
}
```

### 2. Updated `media_handler.py`

**File**: `/app/WebStreamer/bot/plugins/media_handler.py`

**Changes**:
- Extract caption from `message.caption`
- Determine file_type based on media type (video/audio/document)
- Extract video metadata (duration, width, height) for video files
- Pass all fields to `format_file_metadata()`
- Upload happens instantly (no delayed upload)

**Key Updates**:
```python
# Extract caption
caption = message.caption or None

# Determine file type
file_type = None
if message.video:
    file_type = "video"
elif message.audio:
    file_type = "audio"
elif message.document:
    file_type = "document"

# Extract video metadata for videos
video_duration = None
video_width = None
video_height = None
if message.video:
    video_duration = getattr(media, 'duration', None)
    video_width = getattr(media, 'width', None)
    video_height = getattr(media, 'height', None)
```

### 3. Updated `stream_routes.py`

**File**: `/app/WebStreamer/server/stream_routes.py`

**Changes**:
- Updated `/link/{channel_id}/{message_id}` endpoint to use new format
- Determine file_type from mime_type
- Removed bot_user_id parameter

## Data Examples

### Video File (Complete Metadata)
```json
{
  "unique_id": "AgAD-00AAhqIaEg",
  "bot_file_ids": {
    "b_1_file_id": "BAACAgIAAx0CcG2DSwABCs3oaQ9lMYrg8LPNn3X-Pm3J8kSjxtgAAvtNAAIaiGhIosrwrSqhpeMeBA"
  },
  "caption": "Reislin - [OnlyFans.com] - [2023] - Mimi Cica, Reislin x Girthmasterr.mp4\n\nUploaded by Channel: -1002087056849\nChannel Invite Link: https://t.me/+MVZeKRpxKdI0YTk1",
  "file_size_bytes": 2180655398,
  "file_type": "video",
  "original_message_id": 708072,
  "source_channel_id": -1001886225227,
  "file_name": "Reislin - [OnlyFans.com] - [2023] - Mimi Cica, Reislin x.mp4",
  "mime_type": "video/mp4",
  "video_duration_seconds": 2829,
  "video_width": 1920,
  "video_height": 1080
}
```

### Document File (Without Video Metadata)
```json
{
  "unique_id": "AgADXYZABC123",
  "bot_file_ids": {
    "b_1_file_id": "BQACAgQAAx0CaZ9HgwACGQJovW8pV30uZFBM3pcyXd3px7l03wAC"
  },
  "file_name": "Important_Document.pdf",
  "file_size_bytes": 5242880,
  "mime_type": "application/pdf",
  "original_message_id": 12345,
  "source_channel_id": -1001234567890,
  "caption": "Important company document",
  "file_type": "document"
}
```

### Audio File
```json
{
  "unique_id": "AgADAUDIO123",
  "bot_file_ids": {
    "b_1_file_id": "CQACAgQAAx0CaZ9HgwACGQJovW8pV30uZFBM3pcyXd3px7l03wAC"
  },
  "file_name": "Song.mp3",
  "file_size_bytes": 8388608,
  "mime_type": "audio/mpeg",
  "original_message_id": 54321,
  "source_channel_id": -1001234567890,
  "caption": "Great music track",
  "file_type": "audio"
}
```

## Field Descriptions

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `unique_id` | string | ✅ | Telegram's unique file identifier | "AgAD-00AAhqIaEg" |
| `bot_file_ids` | object | ✅ | File IDs from different bots (single bot uses b_1_file_id) | `{"b_1_file_id": "BAAC..."}` |
| `file_name` | string | ✅ | Original file name | "video.mp4" |
| `file_size_bytes` | integer | ✅ | File size in bytes | 2180655398 |
| `mime_type` | string | ✅ | MIME type | "video/mp4" |
| `original_message_id` | integer | ✅ | Telegram message ID | 708072 |
| `source_channel_id` | integer | ✅ | Telegram channel ID | -1001886225227 |
| `caption` | string | ❌ | Message caption text | "Video description..." |
| `file_type` | string | ❌ | File category | "video", "audio", "document" |
| `video_duration_seconds` | integer | ❌ | Video length (videos only) | 2829 |
| `video_width` | integer | ❌ | Video width in pixels (videos only) | 1920 |
| `video_height` | integer | ❌ | Video height in pixels (videos only) | 1080 |

## How It Works

### Flow Diagram
```
Telegram Message → Bot Receives Media
                        ↓
            Extract All Metadata:
            - unique_id, file_id
            - file_name, file_size
            - mime_type, caption
            - file_type (video/audio/document)
            - video metadata (if applicable)
                        ↓
            Format Data Structure
            (with b_1_file_id format)
                        ↓
            Upload to R2 INSTANTLY
            (no delay, single bot)
                        ↓
            Reply with DL Link Button
```

### Key Features

1. **Single Bot Support**: Uses `b_1_file_id` format (not multiple bot IDs)
2. **Instant Upload**: Immediate upload to R2 (no 15-second delay)
3. **Complete Metadata**: All available fields are captured and sent
4. **Conditional Fields**: Optional fields only included when available
5. **Type Detection**: Automatic file_type detection based on media type

## Testing

### Test Script
Run the verification test:
```bash
cd /app
python3 test_r2_structure.py
```

This will:
- Test video file with complete metadata
- Test document file without video fields
- Test audio file
- Compare output structure with expected format
- Verify all keys match correctly

### Expected Output
```
✅ SUCCESS: All keys match perfectly!
✅ bot_file_ids structure is correct (uses 'b_1_file_id' format)
```

## API Endpoint

### R2 Upload Endpoint
```
PUT https://{R2_Domain}/tga-r2/{R2_Folder}?id={unique_file_id}
Content-Type: application/json

{
  "unique_id": "...",
  "bot_file_ids": {...},
  "file_name": "...",
  ...
}
```

**Response**: `200 OK` if successful

## Configuration

No configuration changes needed. Uses existing environment variables:
- `R2_Domain` (default: "tga-hd.api.hashhackers.com")
- `R2_Folder` (default: "linkerz")
- `R2_Public` (default: "tg-files-identifier.hashhackers.com")

## Files Modified

1. `/app/WebStreamer/r2_storage.py` - Updated format_file_metadata method
2. `/app/WebStreamer/bot/plugins/media_handler.py` - Extract and pass all metadata
3. `/app/WebStreamer/server/stream_routes.py` - Updated /link endpoint

## Files Added

1. `/app/test_r2_structure.py` - Verification test script
2. `/app/R2_STRUCTURE_UPDATE.md` - This documentation

## Migration Notes

### Breaking Changes
- `format_file_metadata()` signature changed (removed bot_user_id parameter)
- `bot_file_ids` structure changed from `{bot_user_id: file_id}` to `{"b_1_file_id": file_id}`

### Backward Compatibility
The R2 uploader API handles everything automatically, so existing stored files are not affected. Only new uploads use the new format.

## Summary

✅ **Complete**: All fields from user's example are supported  
✅ **Tested**: Test script verifies structure matches exactly  
✅ **Single Bot**: Uses b_1_file_id format for single bot setup  
✅ **Instant Upload**: No delayed upload strategy (immediate upload)  
✅ **Type-Aware**: Correctly handles video, audio, and document files  
✅ **Metadata-Rich**: Captures all available metadata including video dimensions

The system now sends exactly the data structure required by the R2 API, with the uploader handling all backend processing automatically.
