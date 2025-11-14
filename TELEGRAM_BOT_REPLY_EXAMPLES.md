# Telegram Bot Reply Examples

## Visual Guide: Before and After

This document shows exactly what users will see when they upload files to your channel.

---

## Scenario 1: New File Upload

### What Happens:
User posts a video file to the channel for the **first time**.

### Bot Reply:

```
┌─────────────────────────────────────────────┐
│  📁 File Stored Successfully                │
│                                             │
│  Name: episode_05_4k.mkv                    │
│  Size: 2.35 GB                              │
│  Type: video/x-matroska                     │
│  Location: DC 4                             │
│                                             │
│  ⏱️ Collecting all bot IDs... R2 upload in │
│     15s                                     │
│                                             │
│  📥 Use the buttons below to access your    │
│     file                                    │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │     📥 View File                      │ │
│  └───────────────────────────────────────┘ │
│  ┌───────────────────────────────────────┐ │
│  │     ⏱️ 3 Hour Link                    │ │
│  └───────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### Button Actions:

**Button 1: 📥 View File**
- Opens: `https://your-domain.com/files/AgAD-YwAAinisEg`
- Type: Permanent web viewer
- Features:
  - Preview file (if supported)
  - Stream online
  - Generate new temporary links
  - See file metadata
  - Share options

**Button 2: ⏱️ 3 Hour Link**
- Opens: `https://your-domain.com/download/AgAD-YwAAinisEg/1736824800/a3f2e1d9...`
- Type: Direct download (expires in 3 hours)
- Features:
  - Immediate download starts
  - No web interface
  - Works with download managers
  - Mobile-friendly

---

## Scenario 2: Duplicate File Upload

### What Happens:
User posts the **same file** again (file already exists in R2 storage).

### Bot Reply:

```
┌─────────────────────────────────────────────┐
│  ✅ File Already Exists                     │
│                                             │
│  Name: episode_05_4k.mkv                    │
│  Size: 2.35 GB                              │
│  Type: video/x-matroska                     │
│  Location: DC 4                             │
│                                             │
│  📥 Use the button below to view and        │
│     download                                │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │     📥 View File                      │ │
│  └───────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### Button Actions:

**Button 1: 📥 View File**
- Opens: `https://your-domain.com/files/AgAD-YwAAinisEg`
- Type: Permanent web viewer
- Features: Same as Scenario 1
- Note: User can generate a new 3-hour link from the web page if needed

**Why no 3 Hour Link button?**
- File already exists in storage
- No need for automatic temporary link
- Users can generate on-demand from web viewer
- Reduces button clutter for existing files

---

## Scenario 3: Different File Types

### Video File (New)
```
┌─────────────────────────────────────────────┐
│  📁 File Stored Successfully                │
│                                             │
│  Name: tutorial_video.mp4                   │
│  Size: 450.2 MB                             │
│  Type: video/mp4                            │
│  Location: DC 5                             │
│                                             │
│  📥 Use the buttons below to access your    │
│     file                                    │
│                                             │
│  [📥 View File]  [⏱️ 3 Hour Link]          │
└─────────────────────────────────────────────┘
```

### Audio File (New)
```
┌─────────────────────────────────────────────┐
│  📁 File Stored Successfully                │
│                                             │
│  Name: podcast_episode_42.mp3               │
│  Size: 85.7 MB                              │
│  Type: audio/mpeg                           │
│  Location: DC 2                             │
│                                             │
│  📥 Use the buttons below to access your    │
│     file                                    │
│                                             │
│  [📥 View File]  [⏱️ 3 Hour Link]          │
└─────────────────────────────────────────────┘
```

### Document File (New)
```
┌─────────────────────────────────────────────┐
│  📁 File Stored Successfully                │
│                                             │
│  Name: presentation_slides.pdf              │
│  Size: 12.3 MB                              │
│  Type: application/pdf                      │
│  Location: DC 1                             │
│                                             │
│  📥 Use the buttons below to access your    │
│     file                                    │
│                                             │
│  [📥 View File]  [⏱️ 3 Hour Link]          │
└─────────────────────────────────────────────┘
```

---

## Click Flow Diagrams

### New File → 3 Hour Link
```
User posts file
     ↓
Bot detects new file
     ↓
Bot stores in database
     ↓
Bot generates 3-hour link
     ↓
Bot replies with 2 buttons
     ↓
User clicks "⏱️ 3 Hour Link"
     ↓
Browser/App downloads file directly
     ↓
✅ File downloaded!
```

### New File → View File
```
User posts file
     ↓
Bot replies with 2 buttons
     ↓
User clicks "📥 View File"
     ↓
Opens web viewer
     ↓
User can:
  • Stream online
  • Generate new links
  • See metadata
  • Download
```

### Duplicate File → View File
```
User posts same file
     ↓
Bot detects duplicate (R2 check)
     ↓
Bot replies with "File Already Exists"
     ↓
Shows 1 button only
     ↓
User clicks "📥 View File"
     ↓
Opens web viewer
     ↓
User generates new 3-hour link if needed
```

---

## Mobile Experience

### On Telegram Mobile App

**New File:**
```
╔═══════════════════════════════════════╗
║  📁 File Stored Successfully          ║
║                                       ║
║  Name: movie.mkv                      ║
║  Size: 1.5 GB                         ║
║  Type: video/x-matroska               ║
║  Location: DC 4                       ║
║                                       ║
║  📥 Use the buttons below to access   ║
║     your file                         ║
║                                       ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓   ║
║  ┃  📥 View File                 ┃   ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛   ║
║  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓   ║
║  ┃  ⏱️ 3 Hour Link               ┃   ║
║  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛   ║
╚═══════════════════════════════════════╝
```

**Tap Behavior:**
- **View File button** → Opens in-app browser or external browser
- **3 Hour Link button** → Prompts to download or opens download manager

---

## Desktop Experience

### On Telegram Desktop

**New File:**
```
╔══════════════════════════════════════════════════╗
║  LinkerX Bot • Today at 14:35                    ║
╠══════════════════════════════════════════════════╣
║                                                  ║
║  📁 File Stored Successfully                     ║
║                                                  ║
║  Name: backup_archive.zip                        ║
║  Size: 3.2 GB                                    ║
║  Type: application/zip                           ║
║  Location: DC 4                                  ║
║                                                  ║
║  📥 Use the buttons below to access your file    ║
║                                                  ║
║  ┌────────────────────┐  ┌────────────────────┐ ║
║  │  📥 View File      │  │  ⏱️ 3 Hour Link    │ ║
║  └────────────────────┘  └────────────────────┘ ║
║                                                  ║
╚══════════════════════════════════════════════════╝
```

**Click Behavior:**
- **View File button** → Opens default browser with web viewer
- **3 Hour Link button** → Starts download in default browser

---

## Text Changes Summary

### ❌ Removed Text
```
"🔗 View and download at: https://domain.com/files/..."
```
This URL was removed from the text body.

### ✅ New Text
**For new files:**
```
"📥 Use the buttons below to access your file"
```

**For duplicate files:**
```
"📥 Use the button below to view and download"
```

---

## Button Layout

### Two Buttons (New Files)
```
┌─────────────────────────────────┐
│  First Button:  📥 View File    │  ← Permanent link
└─────────────────────────────────┘
┌─────────────────────────────────┐
│  Second Button: ⏱️ 3 Hour Link  │  ← Temporary link (expires)
└─────────────────────────────────┘
```

### One Button (Duplicate Files)
```
┌─────────────────────────────────┐
│  Only Button:   📥 View File    │  ← Permanent link
└─────────────────────────────────┘
```

---

## User Perspective

### "What should I click?"

**For immediate download:**
→ Click **⏱️ 3 Hour Link**
- Downloads right away
- No extra steps
- Works with download managers

**For viewing first:**
→ Click **📥 View File**
- Opens web page
- Can preview file
- Can stream online
- Can generate new links later

**For duplicate files:**
→ Click **📥 View File**
- Only option shown
- File already stored
- Can generate temporary link from web page

---

## Comparison with Old System

### OLD (Before This Update)

**New File:**
```
📁 File Stored Successfully

Name: video.mp4
Size: 100 MB
Type: video/mp4
Location: DC 4

🔗 View and download at: https://domain.com/files/AbCdEf

[📥 View File]
```
Issues:
- ❌ URL in text looks cluttered
- ❌ No quick download option
- ❌ Must visit web page to get temp link
- ❌ Extra steps for mobile users

### NEW (After This Update)

**New File:**
```
📁 File Stored Successfully

Name: video.mp4
Size: 100 MB
Type: video/mp4
Location: DC 4

📥 Use the buttons below to access your file

[📥 View File]
[⏱️ 3 Hour Link]
```
Benefits:
- ✅ Clean, button-focused UI
- ✅ Direct download option available
- ✅ Mobile-friendly
- ✅ Fewer steps to download

**Duplicate File:**
```
✅ File Already Exists

Name: video.mp4
Size: 100 MB
Type: video/mp4
Location: DC 4

📥 Use the button below to view and download

[📥 View File]
```
Benefits:
- ✅ Clear "already exists" message
- ✅ No redundant temp link
- ✅ Clean single-button UI
- ✅ User can still get temp links via web

---

## Edge Cases

### Case 1: Multiple Bots Receiving Same File
**Result:** Only the base bot (bot 0) replies
**Display:** Same as "New File" (2 buttons)

### Case 2: File in R2 but Not in Database
**Result:** Treated as existing file
**Display:** "File Already Exists" (1 button)

### Case 3: Very Long File Name
```
📁 File Stored Successfully

Name: this_is_a_very_long_filename_that_might...
Size: 500 MB
Type: video/mp4
Location: DC 4

📥 Use the buttons below to access your file

[📥 View File] [⏱️ 3 Hour Link]
```
**Note:** Telegram automatically truncates long text

---

## Testing Checklist

- [ ] Post new video file → Check 2 buttons appear
- [ ] Click "View File" → Opens web viewer
- [ ] Click "3 Hour Link" → Download starts
- [ ] Post same file again → Check "Already Exists" message
- [ ] Check only 1 button appears for duplicate
- [ ] Test on mobile app
- [ ] Test on desktop app
- [ ] Wait 3+ hours → Verify link expires
- [ ] Try tampering with link → Verify security

---

**Status:** ✅ Implemented and ready for testing
**User Impact:** Positive - simpler, faster file access
**Breaking Changes:** None - existing links still work
