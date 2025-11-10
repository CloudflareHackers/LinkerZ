# This file is a part of TG-
# Coding : Jyothis Jayanth [@EverythingSuckz]

import logging
from pyrogram import filters
from WebStreamer.vars import Var
from urllib.parse import quote_plus
from WebStreamer.bot import StreamBot
from WebStreamer.utils import get_hash, get_name
from pyrogram.enums.parse_mode import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from WebStreamer.database import get_database

# OTP storage (telegram_user_id -> otp)
pending_otps = {}

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
        
        # Create or update user in database
        db = get_database()
        if db.auth:
            db.auth.create_user(
                telegram_user_id=telegram_user_id,
                first_name=first_name,
                last_name=last_name,
                username=user.username
            )
        
        # Build response
        reply_text = f"👋 **Welcome, {full_name}!**\n\n"
        reply_text += "📋 **Your Details:**\n"
        reply_text += f"🆔 Telegram ID: `{telegram_user_id}`\n"
        reply_text += f"👤 Username: {username}\n"
        reply_text += f"📝 Name: {full_name}\n\n"
        reply_text += "ℹ️ **How to use:**\n"
        reply_text += "1️⃣ Add me to your channel (where you're owner/admin)\n"
        reply_text += "2️⃣ Post files in the channel\n"
        reply_text += "3️⃣ I'll reply with a secure download link\n"
        reply_text += "4️⃣ Access files through the web interface\n\n"
        reply_text += "🔐 When you receive an OTP code, reply with:\n"
        reply_text += "`/verify <6-digit-code>`"
        
        bot_username = (await StreamBot.get_me()).username
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Bot to Channel", 
                                url=f"https://t.me/{bot_username}?startchannel=true")],
            [InlineKeyboardButton("🌐 Browse Files", url=f"https://{Var.FQDN}/files" if Var.FQDN else "https://your-domain.com/files")]
        ])
        
        await m.reply(reply_text, reply_markup=keyboard)
        
    except Exception as e:
        logging.error(f"Error in start command: {e}", exc_info=True)
        await m.reply("An error occurred. Please try again.")

@StreamBot.on_message(filters.command(["verify"]) & filters.private)
async def verify_otp(_, m: Message):
    """Handle OTP verification"""
    try:
        user = m.from_user
        if not user:
            await m.reply("Unable to identify user.")
            return
        
        # Extract OTP from command
        command_parts = m.text.split()
        if len(command_parts) != 2:
            await m.reply("❌ **Invalid format**\n\nUsage: `/verify <6-digit-code>`\n\nExample: `/verify 123456`")
            return
        
        otp = command_parts[1].strip()
        
        if not otp.isdigit() or len(otp) != 6:
            await m.reply("❌ **Invalid OTP**\n\nOTP must be a 6-digit number.")
            return
        
        telegram_user_id = user.id
        
        # Verify OTP
        db = get_database()
        if not db.auth:
            await m.reply("❌ Authentication system not available.")
            return
        
        verified = db.auth.verify_otp(telegram_user_id, otp)
        
        if verified:
            # Create session
            session_token = db.auth.create_session(telegram_user_id)
            
            if session_token:
                await m.reply(
                    f"✅ **OTP Verified Successfully!**\n\n"
                    f"Your session token:\n`{session_token}`\n\n"
                    f"⚠️ Keep this token secure! It will be used automatically when you log in through the website.\n\n"
                    f"🔗 Access files at: https://{Var.FQDN}/files"
                )
                logging.info(f"OTP verified and session created for user {telegram_user_id}")
            else:
                await m.reply("✅ OTP verified but failed to create session. Please try again.")
        else:
            await m.reply(
                "❌ **Invalid or Expired OTP**\n\n"
                "The OTP you entered is incorrect or has expired (valid for 10 minutes).\n"
                "Please request a new OTP from the website and try again."
            )
            logging.warning(f"Failed OTP verification attempt for user {telegram_user_id}")
        
    except Exception as e:
        logging.error(f"Error verifying OTP: {e}", exc_info=True)
        await m.reply("An error occurred during verification. Please try again.")

@StreamBot.on_message(filters.private & filters.text & ~filters.command(["start", "verify"]))
async def handle_text_messages(_, m: Message):
    """Handle other text messages in private chat"""
    bot_username = (await StreamBot.get_me()).username
    
    reply_text = "👋 Hello! I'm a file storage bot.\n\n"
    reply_text += "To get started, use /start to see your details and instructions.\n\n"
    reply_text += "📂 **Main Features:**\n"
    reply_text += "• Store files from channels\n"
    reply_text += "• Generate secure download links\n"
    reply_text += "• Web-based file browser\n"
    reply_text += "• Rate-limited access (10/hour, 50/day)\n\n"
    reply_text += "Use /start for more information!"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Bot to Channel", 
                            url=f"https://t.me/{bot_username}?startchannel=true")]
    ])
    
    await m.reply(reply_text, reply_markup=keyboard)
