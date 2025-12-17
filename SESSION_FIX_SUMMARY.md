# Session Error Handling & File Validation Fix

## Summary
Fixed session expiry errors and removed problematic file validation in the Telegram bot WebStreamer application.

---

## Issues Fixed

### 1. Session Expiry/Corruption Errors
**Problem:**
```
ERROR:root:no such table: version
ERROR:root:Client is already terminated
```

**Root Cause:**
- Session file downloaded from GitHub was expired or corrupted
- Bot failed to start with invalid session
- Cleanup function attempted to stop already-terminated client

**Solution Implemented:**
- Added automatic session re-authentication in `WebStreamer/__main__.py`
- When session errors are detected (e.g., "no such table", "database is locked"), the bot now:
  1. Detects the session error during startup
  2. Deletes the corrupted session file
  3. Re-authenticates using BOT_TOKEN (creates fresh session)
  4. Uploads the new session file to GitHub
  5. Continues normal operation

**Error Detection:**
Catches these error patterns:
- "no such table"
- "session"
- "auth"
- "database is locked"
- "database disk image is malformed"

---

### 2. Cleanup Error - "Client is already terminated"
**Problem:**
```
ConnectionError: Client is already terminated
```

**Root Cause:**
- Cleanup function tried to stop bot without checking if it was already stopped

**Solution Implemented:**
- Enhanced `cleanup()` function with proper error handling
- Checks `StreamBot.is_connected` before attempting to stop
- Gracefully handles ConnectionError with "already terminated" message
- Prevents crash during cleanup phase

---

### 3. File Validation Warning
**Problem:**
```
WARNING:root:File validation failed: 'FileId' object has no attribute 'message_id'
```

**Root Cause:**
- Pre-validation code in `stream_routes.py` (lines 332-353) tried to access `message_id` attribute
- This validation was unnecessary since file info (fileId, name, size) is already embedded in URL path

**Solution Implemented:**
- Removed the pre-validation check entirely from `/app/WebStreamer/server/stream_routes.py`
- File errors are now handled during actual streaming in `safe_yield_file()`
- Reduces unnecessary Telegram API calls
- Validation still occurs during streaming with proper error pages

---

## Files Modified

### 1. `/app/WebStreamer/__main__.py`
**Changes:**
- Added session error detection and auto re-authentication logic in `start_services()`
- Enhanced `cleanup()` function with proper error handling
- Added logging for session re-authentication process
- Tracks whether a new session was created and uploaded to GitHub

**Key Code Sections:**
```python
# Session retry logic (lines 45-93)
try:
    await StreamBot.start()
    # ... normal startup
except Exception as session_error:
    if any(err in error_str for err in ["no such table", "session", ...]):
        # Delete corrupted session
        # Re-authenticate with bot token
        # Upload new session to GitHub
```

```python
# Enhanced cleanup (lines 142-162)
try:
    if StreamBot.is_connected:
        await StreamBot.stop()
except ConnectionError as e:
    if "already terminated" in str(e).lower():
        logging.info("Client already terminated, cleanup complete")
```

### 2. `/app/WebStreamer/server/stream_routes.py`
**Changes:**
- Removed pre-validation code (lines 329-353)
- Replaced with simple logging statement
- File validation now happens only during actual streaming

**Before:**
```python
# Pre-validate file reference by attempting to get file info
try:
    test_message = await faster_client.get_messages(...)
    # ... validation logic
except Exception as validation_error:
    # ... error handling
```

**After:**
```python
# Skip pre-validation - file info is already in URL path
logging.debug(f"Starting stream for file: {file_name} (size: {file_size})")
```

---

## Benefits

1. **Automatic Recovery**: Bot automatically recovers from session expiry without manual intervention
2. **Reduced API Calls**: Removed unnecessary Telegram API calls for file validation
3. **Better Error Handling**: Graceful cleanup prevents crashes during shutdown
4. **GitHub Sync**: New sessions are automatically uploaded to GitHub for persistence
5. **Improved Logging**: Clear logging for debugging session issues

---

## Testing Recommendations

1. **Test Session Expiry:**
   - Delete or corrupt the session file
   - Start the bot
   - Verify it re-authenticates and uploads new session

2. **Test Cleanup:**
   - Stop the bot normally
   - Force-kill the bot process
   - Verify no "already terminated" errors in logs

3. **Test File Streaming:**
   - Stream files using /dl/ endpoint
   - Verify no "message_id" attribute warnings
   - Check error pages for invalid/expired files

---

## Notes

- Session re-authentication is automatic and requires no user intervention
- BOT_TOKEN must be valid for re-authentication to work
- GitHub credentials must be configured for session backup
- All original error handling for streaming (FILE_REFERENCE_EXPIRED, etc.) remains intact

---

## Deployment

No additional dependencies or configuration required. The changes are backward compatible and enhance existing error handling.
