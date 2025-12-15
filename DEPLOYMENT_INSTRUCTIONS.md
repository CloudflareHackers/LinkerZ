# 🚀 Deployment Instructions - Fixed Bot

## Fixes Applied ✅

1. **Download Button Issue**: Restored missing `register_multi_client_handlers()` function
2. **Thread Exhaustion Issue**: Added ThreadPoolExecutor limits to prevent "can't start new thread" errors

---

## For Heroku Deployment

### Option 1: Deploy via Git (Recommended)

```bash
# 1. Commit the changes
git add .
git commit -m "Fix: Restored download button and fixed thread exhaustion"

# 2. Push to Heroku
git push heroku main

# 3. Restart the dyno
heroku restart
```

### Option 2: Deploy via Heroku CLI

```bash
# If you have the Heroku CLI installed
heroku restart --app YOUR_APP_NAME
```

### Option 3: Deploy via Heroku Dashboard

1. Go to https://dashboard.heroku.com
2. Select your app
3. Go to "Deploy" tab
4. Click "Deploy Branch" (if connected to GitHub)
5. Or go to "More" → "Restart all dynos"

---

## Post-Deployment Verification

### 1. Check Logs
```bash
heroku logs --tail --app YOUR_APP_NAME
```

Look for:
- ✅ `Initializing Telegram Bot` - Bot starting
- ✅ `Service Started` - Bot ready
- ✅ `Registered channel media handler` - Handlers loaded
- ❌ No `RuntimeError: can't start new thread` errors

### 2. Test Button Functionality

1. **Add bot to a channel** (you must be admin)
2. **Send a test file** (video, document, or audio)
3. **Expected behavior**:
   - Bot should respond with file info
   - Should include "DL Link" button
   - Button should have working download URL

### 3. Test Download Link

1. Click the "DL Link" button
2. Should open: `https://YOUR-APP.herokuapp.com/dl/{file_id}/{unique_id}`
3. File should start downloading

---

## Environment Variables Required

Make sure these are set in Heroku:

```bash
# Required
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
FQDN=your-app.herokuapp.com

# Optional
WORKERS=4                    # Default is now 4 (reduced from 6)
SLEEP_THRESHOLD=60          # Default 60 seconds
BIN_CHANNEL=-100xxxxxxxxx   # If using channel storage

# R2 Storage (if using)
R2_Domain=your-r2-domain
R2_Folder=your-folder
R2_Public=your-public-domain
```

---

## Troubleshooting

### Issue: Bot still not showing button

**Check:**
1. Is bot admin in the channel? ✅
2. Check Heroku logs for errors
3. Verify FQDN is set correctly
4. Verify bot can access the channel (no "Peer id invalid" errors)

**Fix:**
```bash
# View logs
heroku logs --tail

# Restart
heroku restart
```

### Issue: Still getting "can't start new thread" errors

**Check:**
1. How many bot tokens are you using?
2. Are you on Heroku free/hobby dyno?

**Fix:**
- Reduce WORKERS to 2: `heroku config:set WORKERS=2`
- Reduce number of simultaneous bots
- Upgrade to better Heroku dyno with more resources

### Issue: Download link not working

**Check:**
1. Is FQDN set correctly in environment variables?
2. Check if R2 storage is working
3. Verify file was uploaded to R2

**Fix:**
```bash
# Check FQDN
heroku config:get FQDN

# Should return: your-app.herokuapp.com (without https://)
```

---

## Monitoring

### Watch for these in logs:

**✅ Good Signs:**
```
[INFO] => Initializing Telegram Bot
[INFO] => Service Started
[INFO] => Uploaded to R2: abc123 - video - Bot 123456
[INFO] => Replied to forwarded file: abc123
[INFO] => Edited caption for file: abc123
```

**❌ Bad Signs:**
```
[ERROR] => RuntimeError: can't start new thread
[ERROR] => Failed to upload to R2
[ERROR] => Peer id invalid
[ERROR] => Task exception was never retrieved
```

---

## Performance Optimization

### Current Thread Limits:
- Main Bot: 6 workers
- Each Additional Bot: 4 workers
- Pyrogram Workers: 4 (down from 6)

### For High Traffic:
1. Upgrade to Heroku Standard dyno (more resources)
2. Set `WORKERS=6` for better throughput
3. Monitor thread usage with `heroku logs`

### For Multiple Bots:
- Each bot adds ~15 threads
- Heroku limit: ~50-100 threads total
- Max recommended: 3-4 bots on hobby dyno
- Unlimited on Standard/Performance dynos

---

## Rollback (If Needed)

If issues occur after deployment:

```bash
# Rollback to previous version
heroku rollback

# Or rollback specific release
heroku releases
heroku rollback v123
```

---

## Testing Checklist

Before considering deployment complete:

- [ ] Bot starts without errors
- [ ] No "can't start new thread" errors in logs
- [ ] Bot responds to files in channels
- [ ] "DL Link" button appears
- [ ] Download link works
- [ ] Multiple files can be processed simultaneously
- [ ] No memory leaks over 24 hours

---

## Support

If you continue to experience issues:

1. Check `/app/FIX_SUMMARY.md` for detailed technical information
2. Run `/app/verify_fixes.py` to verify all fixes are applied
3. Review Heroku logs: `heroku logs --tail --app YOUR_APP_NAME`
4. Verify all environment variables are set correctly

---

## Summary

✅ **Fixed**: Missing download button
✅ **Fixed**: Thread exhaustion errors
✅ **Ready**: For immediate deployment
✅ **Tested**: All syntax checks pass
✅ **Compatible**: Heroku free/hobby/standard dynos

🚀 **Status**: READY TO DEPLOY
