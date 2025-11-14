# 3-Hour Temporary Download Link Feature

## Overview
Added a convenient 3-hour temporary direct download link for newly uploaded files, making it simple for users to quickly share and download files without needing to generate links through the web interface.

---

## How It Works

### For NEW Files (First Time Upload)
When a file is posted to the channel for the first time:

**Bot Reply:**
```
📁 File Stored Successfully

Name: example_video.mp4
Size: 125.5 MB
Type: video/mp4
Location: DC 4

⏱️ Collecting all bot IDs... R2 upload in 15s

📥 Use the buttons below to access your file
```

**Buttons:**
1. **📥 View File** → Links to `/files/{unique_id}` (permanent web viewer)
2. **⏱️ 3 Hour Link** → Direct download link (expires in 3 hours)

### For DUPLICATE Files (Already Exists)
When the same file is posted again (already in R2 storage):

**Bot Reply:**
```
✅ File Already Exists

Name: example_video.mp4
Size: 125.5 MB
Type: video/mp4
Location: DC 4

📥 Use the button below to view and download
```

**Buttons:**
1. **📥 View File** → Links to `/files/{unique_id}` (permanent web viewer)
2. ~~No 3 Hour Link~~ (since file already exists, users can generate on demand)

---

## Technical Implementation

### Changes Made

**File:** `/app/WebStreamer/bot/plugins/media_handler.py`

#### 1. For Duplicate Files (Lines 172-199)
```python
# Only show View File button
reply_text = f"✅ **File Already Exists**\n\n"
reply_text += f"**Name:** {file_name}\n"
reply_text += f"**Size:** {size_str}\n"
reply_text += f"**Type:** {mime_str}\n"
reply_text += f"**Location:** {dc_str}\n\n"
reply_text += f"📥 **Use the button below to view and download**"

keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("📥 View File", url=file_link)]
])
```

#### 2. For New Files (Lines 241-281)
```python
# Generate 3-hour temporary download link
from WebStreamer.auth import generate_download_signature
import time

expires_at = int(time.time()) + (3 * 60 * 60)  # 3 hours from now
signature = generate_download_signature(unique_file_id, expires_at, Var.DOWNLOAD_SECRET_KEY)
temp_download_link = f"https://{fqdn}/download/{unique_file_id}/{expires_at}/{signature}"

reply_text = f"📁 **File Stored Successfully**\n\n"
reply_text += f"**Name:** {file_name}\n"
reply_text += f"**Size:** {size_str}\n"
reply_text += f"**Type:** {mime_str}\n"
reply_text += f"**Location:** {dc_str}\n\n"
reply_text += f"📥 **Use the buttons below to access your file**"

# Two buttons for new files
keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("📥 View File", url=file_link)],
    [InlineKeyboardButton("⏱️ 3 Hour Link", url=temp_download_link)]
])
```

---

## Security Features

### Link Integrity
- Uses HMAC-SHA256 signature
- Signature includes: unique_file_id + expiration timestamp + secret key
- Prevents link tampering or manipulation

### Expiration Enforcement
The existing download endpoint (`/download/{unique_file_id}/{expires_at}/{signature}`) already handles:
1. **Time validation:** Rejects expired links
2. **Signature verification:** Ensures link authenticity
3. **Graceful error:** Shows "Link Expired" message

**Implementation (already exists in `/app/WebStreamer/server/stream_routes.py`):**
```python
@routes.get("/download/{unique_file_id}/{expires_at}/{signature}")
async def download_route_handler(request: web.Request):
    expires_at = int(request.match_info['expires_at'])
    
    # Check expiration
    if time.time() > expires_at:
        raise web.HTTPGone(
            text='Link Expired. Please generate a new one.'
        )
    
    # Verify signature
    if not verify_download_signature(unique_file_id, expires_at, signature, secret_key):
        raise web.HTTPForbidden(text='Invalid link signature')
    
    # Serve file...
```

---

## User Benefits

### 1. Quick Sharing
- No need to visit the web interface
- Copy link directly from Telegram
- Share immediately after upload

### 2. Temporary Access
- 3-hour window is perfect for immediate downloads
- Link automatically expires (no manual cleanup needed)
- Reduces risk of permanent link sharing

### 3. Dual Options
- **View File button:** Permanent access via web viewer
  - Can generate new temporary links anytime
  - Stream files online
  - Preview before downloading
  
- **3 Hour Link button:** Direct download
  - Bypass web interface
  - Download managers compatible
  - Perfect for mobile users

---

## Example Use Cases

### Use Case 1: Quick File Sharing
```
User posts video → Gets 3-hour link → Shares with friend → Friend downloads within 3 hours
```

### Use Case 2: Mobile Download
```
User posts file → Clicks "3 Hour Link" → Mobile browser starts download → No web interface needed
```

### Use Case 3: Download Manager
```
User posts file → Copies 3-hour link → Pastes into IDM/wget → Scheduled download
```

### Use Case 4: Re-upload Detection
```
User posts duplicate file → Gets only View File button → Goes to web viewer → Generates new temp link if needed
```

---

## Link Format

### View File Link (Permanent)
```
https://your-domain.com/files/{unique_file_id}
```
- Never expires
- Opens web viewer
- Can generate temporary links on demand

### 3 Hour Download Link (Temporary)
```
https://your-domain.com/download/{unique_file_id}/{expires_at}/{signature}
```
- Expires after 3 hours
- Direct download (no web viewer)
- Cryptographically signed

**Example:**
```
https://your-domain.com/download/AgAD-YwAAinisEg/1736824800/a3f2e1d9c8b7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1
                                    └─────┬─────┘ └──────┬──────┘ └─────────────────┬─────────────────┘
                                   unique_file_id   expires_at              HMAC signature
```

---

## Comparison: Before vs After

### Before This Feature
**New File:**
```
📁 File Stored Successfully

Name: video.mp4
Size: 100 MB
Type: video/mp4
Location: DC 4

🔗 View and download at: https://domain.com/files/AbCdEf123

[Button: 📥 View File]
```
- User had to click View File
- Then click "Generate 3 Hour Link" on web page
- Extra steps for quick downloads

### After This Feature
**New File:**
```
📁 File Stored Successfully

Name: video.mp4
Size: 100 MB
Type: video/mp4
Location: DC 4

📥 Use the buttons below to access your file

[Button: 📥 View File]
[Button: ⏱️ 3 Hour Link]
```
- Direct access to temporary link
- One click to download
- No web interface needed for quick downloads

**Duplicate File:**
```
✅ File Already Exists

Name: video.mp4
Size: 100 MB
Type: video/mp4
Location: DC 4

📥 Use the button below to view and download

[Button: 📥 View File]
```
- Clear indication file already exists
- No redundant temporary link (user can generate on web if needed)

---

## Configuration

### Expiration Time
Currently set to **3 hours** (10,800 seconds)

**To change:**
Edit `/app/WebStreamer/bot/plugins/media_handler.py` line 253:
```python
# Change 3 to any number of hours
expires_at = int(time.time()) + (3 * 60 * 60)

# Examples:
# 1 hour:  expires_at = int(time.time()) + (1 * 60 * 60)
# 6 hours: expires_at = int(time.time()) + (6 * 60 * 60)
# 24 hours: expires_at = int(time.time()) + (24 * 60 * 60)
```

### Secret Key
Make sure `DOWNLOAD_SECRET_KEY` is set in your environment:
```bash
heroku config:set DOWNLOAD_SECRET_KEY="your-secure-random-key-here"
```

**Generate a secure key:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Testing

### Test Case 1: New File Upload
1. Post a new file to your channel
2. Bot should reply with 2 buttons
3. Click "⏱️ 3 Hour Link"
4. File should download immediately

### Test Case 2: Duplicate File
1. Post the same file again
2. Bot should reply with "File Already Exists"
3. Should have only 1 button (📥 View File)
4. No 3 Hour Link button

### Test Case 3: Link Expiration
1. Get a 3-hour link
2. Wait 3+ hours (or modify expires_at to test)
3. Click the link
4. Should see "Link Expired" error

### Test Case 4: Link Tampering
1. Get a 3-hour link
2. Modify the signature in URL
3. Click the modified link
4. Should see "Invalid link signature" error

---

## Monitoring

### Success Indicators
- Users receive bot replies with proper buttons
- 3-hour links download successfully
- Expired links show proper error messages
- Duplicate files don't get redundant temp links

### Logs to Watch
```bash
# Check bot responses
heroku logs --tail | grep "File Stored Successfully\|File Already Exists"

# Check download attempts
heroku logs --tail | grep "download/"

# Check for expired link access attempts
heroku logs --tail | grep "Link Expired"
```

---

## FAQ

**Q: Why only 3 hours?**
A: Balance between convenience and security. Long enough for immediate use, short enough to prevent abuse.

**Q: Can users extend the 3-hour window?**
A: No, but they can generate a new link from the View File page anytime.

**Q: Why no 3-hour link for duplicate files?**
A: Duplicate files are already stored and accessible. Users can generate temporary links on demand from the web viewer.

**Q: What happens after 3 hours?**
A: Link expires and shows "Link Expired" error. Users need to get a new link from the View File page.

**Q: Can download managers use these links?**
A: Yes! The direct download links work with IDM, wget, curl, aria2, etc.

**Q: Is the signature secure?**
A: Yes, uses HMAC-SHA256 with a secret key. Cannot be forged without the secret.

---

## Future Enhancements (Optional)

### Possible Improvements:
1. **Custom expiration:** Let users choose 1h/3h/6h/24h
2. **QR code:** Generate QR code for mobile sharing
3. **Password protection:** Add optional password to temp links
4. **Usage tracking:** Track how many times link was accessed
5. **Auto-regenerate:** Button to regenerate expired link

---

## Summary

✅ **Implemented Features:**
- 3-hour temporary download links for NEW files
- Direct download without web interface
- Cryptographically signed links
- Automatic expiration after 3 hours
- No redundant links for duplicate files
- Clean, intuitive button layout

✅ **User Experience:**
- One-click download access
- Clear distinction between new and duplicate files
- Mobile-friendly
- Download manager compatible

✅ **Security:**
- HMAC-SHA256 signatures
- Time-based expiration
- Tamper-proof links
- Graceful error handling

**Status:** ✅ Ready to use
**Testing:** Recommended before production
**Impact:** Improved user convenience without compromising security
