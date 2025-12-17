# Enhanced Logging Guide

## Overview
Comprehensive logging has been added to track every step of session handling and GitHub operations.

---

## Log Prefixes

All logs are now prefixed for easy filtering:

- **`[GitHub Upload]`** - GitHub upload operations
- **`[GitHub Download]`** - GitHub download operations  
- **`STEP X:`** - Main startup steps
- **`✓`** - Success indicators
- **`✗`** - Error indicators
- **`!`** - Warning/Info indicators

---

## Startup Flow Logging

### STEP 1: Downloading Session File

```
======================================================================
STEP 1: DOWNLOADING SESSION FILE FROM GITHUB
======================================================================
Session file to download: 123456789.session
[GitHub Download] Starting download process...
[GitHub Download] GitHub repo path: 123456789.session
[GitHub Download] Current directory: /app
[GitHub Download] ✓ GitHub credentials configured
[GitHub Download] Target repo: username/repo
[GitHub Download] API URL: https://api.github.com/repos/username/repo/contents/123456789.session
[GitHub Download] Sending GET request to GitHub...
[GitHub Download] Response status: 200
[GitHub Download] ✓ File found on GitHub
[GitHub Download] Decoding base64 content...
[GitHub Download] Decoded content size: 8192 bytes
[GitHub Download] Writing to file: /app/123456789.session
[GitHub Download] ✓✓✓ SUCCESS! File saved: /app/123456789.session
[GitHub Download] File size: 8192 bytes
✓ Session file downloaded successfully from GitHub
```

**If file not found:**
```
[GitHub Download] Response status: 404
[GitHub Download] ! File not found on GitHub: 123456789.session
[GitHub Download] This is normal for first-time setup
! Session file not found in GitHub (will create new one)
```

---

### STEP 2: Initializing Telegram Bot

**Normal startup (valid session):**
```
======================================================================
STEP 2: INITIALIZING TELEGRAM BOT
======================================================================
Session file path: /app/123456789.session
Session file exists: True
Current working directory: /app
Attempting to start bot with existing session...
✓ Bot started successfully with existing session
✓ Bot name: MyBot
✓ Bot username: @mybot
✓ Bot ID: 123456789
----------------------------------------------------------------------
```

**Session error detected:**
```
======================================================================
STEP 2: INITIALIZING TELEGRAM BOT
======================================================================
Session file path: /app/123456789.session
Session file exists: True
Current working directory: /app
Attempting to start bot with existing session...
======================================================================
SESSION ERROR DETECTED!
======================================================================
Error type: OperationalError
Error message: no such table: version
----------------------------------------------------------------------
✓ Identified as session-related error, will re-authenticate

======================================================================
STEP 2B: RE-AUTHENTICATING WITH BOT TOKEN
======================================================================
Deleting corrupted session file: /app/123456789.session
✓ Deleted corrupted session file successfully
Starting fresh bot authentication with BOT_TOKEN...
✓ Bot.start() completed
✓ Bot.get_me() completed

✓✓✓ RE-AUTHENTICATION SUCCESSFUL ✓✓✓
✓ Bot name: MyBot
✓ Bot username: @mybot
✓ Bot ID: 123456789
✓ New session file created: /app/123456789.session (8192 bytes)
----------------------------------------------------------------------
```

---

### STEP 3: Uploading Session File to GitHub

**Normal upload (existing session):**
```
======================================================================
STEP 3: UPLOADING SESSION FILE TO GITHUB
======================================================================
! This is an EXISTING session, updating GitHub backup...
Session file to upload: 123456789.session
Session file path: /app/123456789.session
Session file exists: True
Session file size: 8192 bytes
Starting GitHub upload...
[GitHub Upload] Starting upload process...
[GitHub Upload] Local file path: 123456789.session
[GitHub Upload] GitHub repo path: 123456789.session
[GitHub Upload] File size: 8192 bytes
[GitHub Upload] ✓ GitHub credentials configured
[GitHub Upload] Target repo: username/repo
[GitHub Upload] API URL: https://api.github.com/repos/username/repo/contents/123456789.session
[GitHub Upload] Checking if file exists on GitHub...
[GitHub Upload] ✓ File exists on GitHub: 123456789.session
[GitHub Upload] Current SHA: abc123def4...
[GitHub Upload] Reading file content...
[GitHub Upload] Encoded content length: 10923 chars
[GitHub Upload] Mode: UPDATE (with SHA)
[GitHub Upload] Sending PUT request to GitHub...
[GitHub Upload] ✓✓✓ SUCCESS! File uploaded to GitHub
[GitHub Upload] Status code: 200
✓✓✓ SESSION FILE UPLOADED TO GITHUB SUCCESSFULLY ✓✓✓
----------------------------------------------------------------------
```

**New session upload (after re-auth):**
```
======================================================================
STEP 3: UPLOADING SESSION FILE TO GITHUB
======================================================================
! This is a NEW session (re-authenticated), uploading to GitHub...
Session file to upload: 123456789.session
Session file path: /app/123456789.session
Session file exists: True
Session file size: 8192 bytes
Starting GitHub upload...
[GitHub Upload] Starting upload process...
[GitHub Upload] Local file path: 123456789.session
[GitHub Upload] GitHub repo path: 123456789.session
[GitHub Upload] File size: 8192 bytes
[GitHub Upload] ✓ GitHub credentials configured
[GitHub Upload] Target repo: username/repo
[GitHub Upload] API URL: https://api.github.com/repos/username/repo/contents/123456789.session
[GitHub Upload] Checking if file exists on GitHub...
[GitHub Upload] ✓ File exists on GitHub: 123456789.session
[GitHub Upload] Current SHA: old123sha4...
[GitHub Upload] Reading file content...
[GitHub Upload] Encoded content length: 10923 chars
[GitHub Upload] Mode: UPDATE (with SHA)
[GitHub Upload] Sending PUT request to GitHub...
[GitHub Upload] ✓✓✓ SUCCESS! File uploaded to GitHub
[GitHub Upload] Status code: 200
✓✓✓ SESSION FILE UPLOADED TO GITHUB SUCCESSFULLY ✓✓✓
✓ NEW session is now backed up to GitHub
----------------------------------------------------------------------
```

---

## Error Scenarios

### GitHub Credentials Not Set

```
[GitHub Upload] ✗ GitHub credentials not configured:
[GitHub Upload]   - GITHUB_TOKEN: NOT SET
[GitHub Upload]   - GITHUB_USERNAME: NOT SET
[GitHub Upload]   - GITHUB_REPO: NOT SET
[GitHub Upload] Skipping upload
✗✗✗ GITHUB UPLOAD FAILED ✗✗✗
✗ NEW session was NOT backed up - manual backup recommended!
```

### GitHub API Error

```
[GitHub Upload] ✗✗✗ FAILED to upload to GitHub
[GitHub Upload] Status code: 401
[GitHub Upload] Response: {"message":"Bad credentials","documentation_url":"https://docs.github.com/..."}
✗✗✗ GITHUB UPLOAD FAILED ✗✗✗
```

### Session File Not Created

```
✗ Session file was NOT created at: /app/123456789.session
```

### Re-authentication Failed

```
======================================================================
RE-AUTHENTICATION FAILED!
======================================================================
Error type: UnauthorizedError
Error message: The bot token is invalid
----------------------------------------------------------------------
```

---

## Filtering Logs

### View only GitHub operations:
```bash
grep "\[GitHub" logs.txt
```

### View only success indicators:
```bash
grep "✓" logs.txt
```

### View only errors:
```bash
grep "✗" logs.txt
```

### View session-related events:
```bash
grep -E "SESSION|session" logs.txt
```

### View full startup flow:
```bash
grep -E "STEP|====" logs.txt
```

---

## What to Look For

### Successful Session Re-auth:
1. ✓ "SESSION ERROR DETECTED!"
2. ✓ "Deleted corrupted session file successfully"
3. ✓ "RE-AUTHENTICATION SUCCESSFUL"
4. ✓ "New session file created: ... (8192 bytes)"
5. ✓ "SESSION FILE UPLOADED TO GITHUB SUCCESSFULLY"
6. ✓ "NEW session is now backed up to GitHub"

### Failed GitHub Upload:
1. ✓ "RE-AUTHENTICATION SUCCESSFUL"
2. ✗ "GITHUB UPLOAD FAILED"
3. ✗ Look for error details in `[GitHub Upload]` logs
4. Check GitHub credentials configuration

### GitHub Credentials Missing:
1. Look for: "GitHub credentials not configured"
2. Check which credentials are missing (TOKEN, USERNAME, REPO)
3. Set the missing environment variables

---

## Debugging Tips

1. **Session file not uploading?**
   - Check if session file exists: `ls -la *.session`
   - Check file size (should be ~8KB): `du -h *.session`
   - Look for `[GitHub Upload]` logs to see exact failure point

2. **Re-authentication not working?**
   - Verify BOT_TOKEN is valid
   - Check `RE-AUTHENTICATION SUCCESSFUL` message appears
   - Verify new session file was created

3. **GitHub operations failing?**
   - Check GitHub credentials are set
   - Verify GITHUB_TOKEN has write permissions
   - Check repository exists and is accessible
   - Look for HTTP status codes in logs

4. **Still seeing "no such table" errors?**
   - Check if re-authentication is triggering
   - Verify session file is being deleted
   - Check if new session is being created
   - Ensure new session is uploaded to GitHub

---

## Example Full Successful Re-auth Log

```
======================================================================
STEP 1: DOWNLOADING SESSION FILE FROM GITHUB
======================================================================
Session file to download: 123456789.session
[GitHub Download] Starting download process...
[GitHub Download] ✓✓✓ SUCCESS! File saved: /app/123456789.session
✓ Session file downloaded successfully from GitHub

======================================================================
STEP 2: INITIALIZING TELEGRAM BOT
======================================================================
Attempting to start bot with existing session...
======================================================================
SESSION ERROR DETECTED!
======================================================================
Error message: no such table: version
✓ Identified as session-related error, will re-authenticate

======================================================================
STEP 2B: RE-AUTHENTICATING WITH BOT TOKEN
======================================================================
✓ Deleted corrupted session file successfully
✓✓✓ RE-AUTHENTICATION SUCCESSFUL ✓✓✓
✓ New session file created: /app/123456789.session (8192 bytes)

======================================================================
STEP 3: UPLOADING SESSION FILE TO GITHUB
======================================================================
! This is a NEW session (re-authenticated), uploading to GitHub...
[GitHub Upload] ✓✓✓ SUCCESS! File uploaded to GitHub
✓✓✓ SESSION FILE UPLOADED TO GITHUB SUCCESSFULLY ✓✓✓
✓ NEW session is now backed up to GitHub
```

---

**Last Updated:** December 2024
**Version:** 2.1 (Enhanced Logging)
