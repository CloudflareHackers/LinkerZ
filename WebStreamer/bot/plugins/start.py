# Simplified start command - no auth
import logging
from pyrogram import filters
from WebStreamer.vars import Var
from WebStreamer.bot import StreamBot, cached_bot_info
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

@StreamBot.on_message(filters.command(["start"]))
async def start(_, m: Message):
    """Handle /start command - show user details"""
    try:
        user = m.from_user
        if not user:
            await m.reply("Unable to identify user.")
            return
        
        # Get user details
        telegram_user_id = user.id
        first_name = user.first_name or "N/A"
        last_name = user.last_name or ""
        username = f"@{user.username}" if user.username else "No username"
        full_name = f"{first_name} {last_name}".strip()
        
        # Build response
        reply_text = f"👋 **Welcome, {full_name}!**\n\n"
        reply_text += "📋 **Your Details:**\n"
        reply_text += f"🆔 Telegram ID: `{telegram_user_id}`\n"
        reply_text += f"👤 Username: {username}\n"
        reply_text += f"📝 Name: {full_name}\n\n"
        reply_text += "ℹ️ **How to use:**\n"
        reply_text += "1️⃣ Add me to your channel (where you're owner/admin)\n"
        reply_text += "2️⃣ Post files in the channel\n"
        reply_text += "3️⃣ I'll reply with a download link"
        
        # Use cached bot username (populated at startup)
        bot_username = cached_bot_info.get("username") or StreamBot.username
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Bot to Channel", 
                                url=f"https://t.me/{bot_username}?startchannel=true")]
        ])
        
        await m.reply(reply_text, reply_markup=keyboard)
        
    except Exception as e:
        logging.error(f"Error in start command: {e}", exc_info=True)
        await m.reply("An error occurred. Please try again.")

@StreamBot.on_message(filters.private & filters.text & ~filters.command(["start"]))
async def handle_text_messages(_, m: Message):
    """Handle other text messages in private chat"""
    # Use cached bot username (populated at startup)
    bot_username = cached_bot_info.get("username") or StreamBot.username
    
    reply_text = "👋 Hello! I'm a file storage bot.\n\n"
    reply_text += "To get started, use /start to see your details and instructions.\n\n"
    reply_text += "📂 **Main Features:**\n"
    reply_text += "• Store files from channels\n"
    reply_text += "• Generate download links\n"
    reply_text += "• Direct streaming\n\n"
    reply_text += "Use /start for more information!"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Bot to Channel", 
                            url=f"https://t.me/{bot_username}?startchannel=true")]
    ])
    
    await m.reply(reply_text, reply_markup=keyboard)
