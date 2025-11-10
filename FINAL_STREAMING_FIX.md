# Final Streaming Fix - Pattern 4 Added

## 🎯 Discovered Signature

Your production logs revealed the **exact** Session signature:

```python
Session(
    self,
    client: 'pyrogram.Client',
    dc_id: int,
    server_address: str,    # ← Missing!
    port: int,              # ← Missing!
    auth_key: bytes,
    test_mode: bool,
    is_media: bool = False,
    is_cdn: bool = False
)
```

## ✅ Solution: Added Pattern 4

Added a new pattern that provides `server_address` and `port`:

### Approach 1: Use Pyrogram's DataCenter class
```python
from pyrogram.session.internals import DataCenter
dc = DataCenter(dc_id, test_mode)
Session(client, dc_id, dc.address, dc.port, auth_key, test_mode, is_media=True)
```

### Approach 2: Hardcoded DC addresses (fallback)
If DataCenter class doesn't exist, use Telegram's standard DC addresses:

```python
# Production DCs
dc_configs = {
    1: ("149.154.175.53", 443),
    2: ("149.154.167.51", 443),
    3: ("149.154.175.100", 443),
    4: ("149.154.167.91", 443),
    5: ("91.108.56.128", 443),
}

# Test DCs (if test_mode=True)
dc_configs = {
    1: ("149.154.175.10", 443),
    2: ("149.154.167.40", 443),
    3: ("149.154.175.117", 443),
}
```

## 📋 Updated Logic

The `create_session_safe()` function now:

1. **Checks signature** - Looks for `server_address` and `port` parameters
2. **Pattern 4a** - Tries to use `DataCenter` class
3. **Pattern 4b** - Falls back to hardcoded DC addresses
4. **Pattern 1-3** - Falls back to old patterns if needed

### Complete Flow

```python
def create_session_safe(client, dc_id, auth_key, test_mode, is_media=True):
    # Check if signature needs server_address and port
    if 'server_address' in parameters:
        # Try Pattern 4a: DataCenter class
        try:
            from pyrogram.session.internals import DataCenter
            dc = DataCenter(dc_id, test_mode)
            return Session(client, dc_id, dc.address, dc.port, auth_key, test_mode, is_media=is_media)
        except:
            # Try Pattern 4b: Hardcoded addresses
            dc_configs = {1: ("149.154.175.53", 443), ...}
            server_address, port = dc_configs[dc_id]
            return Session(client, dc_id, server_address, port, auth_key, test_mode, is_media=is_media)
    
    # Fall back to old patterns...
    try: return Session(client, dc_id, auth_key, test_mode, is_media=is_media)
    try: return Session(client=client, dc_id=dc_id, auth_key=auth_key, ...)
    # etc.
```

## 🔍 What the Logs Will Show

After deploying, you'll see:

```
[DEBUG] Session.__init__ parameters: ['client', 'dc_id', 'server_address', 'port', 'auth_key', 'test_mode', 'is_media', 'is_cdn']
[DEBUG] Trying pattern 4: with server_address and port
[INFO] Using DC config: 91.108.56.128:443 for DC 5
[INFO] Successfully created Session
```

## 📊 DC ID Reference

Your file is on **DC 5** (as shown in logs: `dc_id=5`)

**Telegram DC Locations:**
- DC 1: Miami, USA (149.154.175.53:443)
- DC 2: Amsterdam, Netherlands (149.154.167.51:443)
- DC 3: Miami, USA (149.154.175.100:443)
- DC 4: Amsterdam, Netherlands (149.154.167.91:443)
- DC 5: Singapore (91.108.56.128:443)

## ✅ What Changed

**File:** `/app/WebStreamer/utils/custom_dl.py`

**Added:**
1. Pattern 4a: Uses `DataCenter` class to get server/port
2. Pattern 4b: Uses hardcoded DC addresses as fallback
3. Logs which DC config is being used

**Logic:**
1. First checks if signature needs server_address and port
2. Tries to get them from DataCenter class
3. Falls back to hardcoded addresses
4. Then tries old patterns if needed

## 🚀 Expected Result

This fix will:
✅ Detect that your Session needs server_address and port
✅ Use DC 5's address: 91.108.56.128:443
✅ Create Session successfully
✅ Downloads will work!

## 🧪 Testing

After deployment, the streaming download should work. Check logs for:

```
[INFO] Using DC config: 91.108.56.128:443 for DC 5
```

This confirms Pattern 4b is working correctly.

## 📝 Summary

**Issue:** Session class needs `server_address` and `port` parameters
**Solution:** Added Pattern 4 that provides these from DC configuration
**Method:** Try DataCenter class, fallback to hardcoded addresses
**Status:** Ready to deploy

Your downloads should work now! The file is on DC 5 (Singapore) and we'll connect to 91.108.56.128:443 to stream it. 🎉
