# Admin Permissions Auto-Leave Feature

## Overview
This feature automatically handles situations where the bot lacks admin permissions in a chat. When permission errors occur, the bot will notify users and gracefully leave the chat, allowing them to re-add it with proper permissions.

## Problem Solved
When the bot is added to channels/groups without admin permissions, it cannot:
- Edit message captions to add download links
- Delete messages
- Perform admin-only operations

Previously, these errors would just be logged, and the bot would remain in the chat unable to function properly.

## Solution Implemented

### Automatic Detection & Response
When the bot encounters permission-related errors, it will:

1. **Detect Permission Errors**
   - `CHAT_ADMIN_REQUIRED` - Bot needs admin permissions
   - `CHAT_WRITE_FORBIDDEN` - Bot cannot write to chat
   - `MESSAGE_AUTHOR_REQUIRED` - Bot cannot edit messages it didn't create

2. **Send Notification Message**
   ```
   ⚠️ Admin Permissions Required
   
   I need admin permissions to edit messages in this chat.
   
   Please make me an Admin with the following permissions:
   • ✏️ Edit messages
   • 📝 Post messages
   • 🗑️ Delete messages
   
   I'm leaving this chat now. Please add me back with proper admin permissions!
   ```

3. **Leave the Chat**
   - Wait 2 seconds for notification to be delivered
   - Exit the chat using `client.leave_chat()`
   - Log the action with chat details

4. **Log the Event**
   ```
   [ADMIN_ERROR] Leaving chat 'Channel Name' (-1001234567890) - missing permissions
   [ADMIN_ERROR] Successfully left chat 'Channel Name' (-1001234567890)
   ```

## Required Bot Permissions

For the bot to work properly in channels/groups, it needs these admin permissions:

| Permission | Purpose |
|------------|---------|
| ✏️ Edit messages | Add download buttons to media posts |
| 📝 Post messages | Send notifications and replies |
| 🗑️ Delete messages | (Optional) Clean up old messages |

## User Experience

### Before Fix
1. Bot is added without admin permissions
2. Error logged: `WARNING:root:Bot needs admin permissions: [400 CHAT_ADMIN_REQUIRED]`
3. Bot stays in chat but cannot function
4. User confused why bot isn't working

### After Fix
1. Bot is added without admin permissions
2. Bot detects it cannot edit messages
3. Bot sends clear notification explaining what's needed
4. Bot leaves the chat automatically
5. User sees the message, understands the issue
6. User adds bot back with proper permissions
7. ✅ Bot works correctly

## Technical Implementation

### File Modified
`/app/WebStreamer/bot/plugins/media_handler.py`

### Key Code Changes

**Detection Logic (Lines 240-246):**
```python
permission_errors = [
    "CHAT_ADMIN_REQUIRED",
    "CHAT_WRITE_FORBIDDEN", 
    "MESSAGE_AUTHOR_REQUIRED"
]

if any(err in error_str for err in permission_errors):
```

**Leave Chat Logic (Lines 254-267):**
```python
await message.reply_text(notification_message)
await asyncio.sleep(2)  # Wait for message delivery
chat_id = message.chat.id
await client.leave_chat(chat_id)
```

### Error Handling
- Wrapped in try-except to handle cases where:
  - Bot cannot send messages (already restricted)
  - Bot cannot leave chat (already kicked)
  - Network issues during leave operation
- Logs all failures for debugging

## Testing

### Test Scenario 1: Channel Without Admin Permissions
1. Create a test channel
2. Add bot as a regular member (not admin)
3. Post a media file (video/audio/document)
4. Expected Result:
   - Bot detects permission error
   - Sends notification message
   - Leaves channel within 2 seconds
   - Logs show `[ADMIN_ERROR]` entries

### Test Scenario 2: Re-adding with Permissions
1. After bot leaves (from Test 1)
2. Add bot back as admin with required permissions
3. Post a media file
4. Expected Result:
   - Bot successfully edits message caption
   - Adds "DL Link" button
   - No errors, stays in channel

### Test Scenario 3: Multi-Client Setup
1. Multiple bot instances in same channel
2. Remove admin permissions from one bot
3. Expected Result:
   - Only the affected bot leaves
   - Other bots continue working
   - Each bot handles permissions independently

## Monitoring

### Log Messages to Watch For

**Success (Normal Operation):**
```
INFO: Edited caption for file: ABCD1234 (total buttons: 1)
```

**Permission Error Detected:**
```
WARNING: Bot needs admin permissions: [400 CHAT_ADMIN_REQUIRED]
[ADMIN_ERROR] Leaving chat 'My Channel' (-1001234567890) - missing permissions
[ADMIN_ERROR] Successfully left chat 'My Channel' (-1001234567890)
```

**Failure to Leave:**
```
ERROR: Failed to send admin notification or leave chat: [error details]
[ADMIN_ERROR] Failed to leave chat: [error details]
```

## Benefits

1. **User-Friendly**: Clear explanation of what's needed
2. **Automatic**: No manual intervention required
3. **Clean**: Bot doesn't stay in chats where it can't function
4. **Visible**: Both logging and print statements for monitoring
5. **Graceful**: 2-second delay ensures notification is delivered
6. **Multi-Error**: Handles multiple permission error types

## Notes

- The 2-second delay before leaving ensures the notification message is sent
- Bot only leaves for permission-related errors, not other edit failures
- For other edit errors (e.g., message too old), bot replies instead of editing
- Feature works for both single bot and multi-client setups
- Logs include both chat title and chat ID for easy identification
