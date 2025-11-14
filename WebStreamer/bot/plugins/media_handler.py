# Media handler plugin to store file information in database
import logging
import asyncio
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from WebStreamer.database import get_database
from WebStreamer.r2_storage import get_r2_storage
from WebStreamer.bot import StreamBot, multi_clients
from WebStreamer.vars import Var
from pyrogram.file_id import FileId

# Track files pending R2 upload (to avoid duplicate scheduled tasks)
pending_r2_uploads = set()

# R2 upload delay in seconds (wait for all bots to see the file)
R2_UPLOAD_DELAY = 15

# Media types we want to track
MEDIA_FILTER = (
    filters.video 
    | filters.audio 
    | filters.document
)

def format_file_size(bytes_size: int) -> str:
    """Format file size in human readable format"""
    if bytes_size == 0:
        return "0B"
    k = 1024
    sizes = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = bytes_size
    while size >= k and i < len(sizes) - 1:
        size /= k
        i += 1
    return f"{size:.2f} {sizes[i]}"

async def delayed_r2_upload(unique_file_id: str, file_name: str, file_size: int, 
                           file_type: str, mime_type: str, caption: str,
                           message_id: int, channel_id: int):
    """
    Wait for all bots to see the file, then upload to R2 with all collected file_ids
    
    Args:
        unique_file_id: Unique file identifier
        file_name: Name of the file
        file_size: File size in bytes
        file_type: Type of file (video/audio/document)
        mime_type: MIME type
        caption: File caption
        message_id: Original message ID
        channel_id: Source channel ID
    """
    try:
        # Wait for all bots to see and store the file
        logging.info(f"[R2 Upload] Waiting {R2_UPLOAD_DELAY}s for all bots to report: {unique_file_id}")
        await asyncio.sleep(R2_UPLOAD_DELAY)
        
        # Fetch all bot file_ids from database
        db = get_database()
        file_data = db.get_file_ids(unique_file_id)
        
        if not file_data or not file_data.get('bot_file_ids'):
            logging.error(f"[R2 Upload] No file data found after delay: {unique_file_id}")
            return
        
        # Build bot_file_ids dict in R2 format
        bot_file_ids = {}
        for bot_idx, bot_file_id in file_data['bot_file_ids'].items():
            bot_file_ids[f"b_{bot_idx + 1}_file_id"] = bot_file_id
        
        logging.info(f"[R2 Upload] Collected {len(bot_file_ids)} bot file_ids for {unique_file_id}")
        
        # Format data for R2
        r2 = get_r2_storage()
        r2_data = r2.format_file_data(
            unique_file_id=unique_file_id,
            bot_file_ids=bot_file_ids,
            caption=caption,
            file_size=file_size,
            file_type=file_type,
            message_id=message_id,
            channel_id=channel_id,
            file_name=file_name,
            mime_type=mime_type
        )
        
        # Upload to R2
        upload_success = r2.upload_file_data(unique_file_id, r2_data)
        
        if upload_success:
            logging.info(f"[R2 Upload] Successfully uploaded to R2 with {len(bot_file_ids)} bot file_ids: {unique_file_id}")
        else:
            logging.warning(f"[R2 Upload] Failed to upload to R2: {unique_file_id}")
        
    except Exception as e:
        logging.error(f"[R2 Upload] Error during delayed upload for {unique_file_id}: {e}", exc_info=True)
    finally:
        # Remove from pending set
        if unique_file_id in pending_r2_uploads:
            pending_r2_uploads.remove(unique_file_id)
            logging.info(f"[R2 Upload] Removed from pending: {unique_file_id}")

async def store_channel_media(client, message: Message, bot_index: int, should_reply: bool = False):
    """
    Store media file in database. Schedule R2 upload after delay to collect all bot file_ids.
    Only replies if should_reply=True.
    
    Args:
        client: Pyrogram client
        message: Message containing media
        bot_index: Index of the bot (0-10, maps to b_1 to b_11)
        should_reply: If True, send reply message (only for base bot)
    """
    try:
        # Get media information
        media = message.video or message.audio or message.document
        if not media:
            return
        
        unique_file_id = media.file_unique_id
        file_id = media.file_id
        file_name = getattr(media, 'file_name', None) or f"file_{unique_file_id}"
        file_size = getattr(media, 'file_size', 0)
        mime_type = getattr(media, 'mime_type', None)
        
        # Get DC ID from file_id
        try:
            file_id_obj = FileId.decode(file_id)
            dc_id = file_id_obj.dc_id
        except:
            dc_id = None
        
        # Get channel ID and message ID
        channel_id = message.chat.id if message.chat else None
        message_id = message.id
        
        # Get caption
        caption = message.caption or file_name
        
        # Determine file type
        if message.video:
            file_type = "video"
        elif message.audio:
            file_type = "audio"
        else:
            file_type = "document"
        
        # Initialize R2 storage
        r2 = get_r2_storage()
        
        # Check if file already exists in R2
        existing_r2_data = r2.check_file_exists(unique_file_id)
        
        if existing_r2_data:
            # File already exists in R2 - just update database
            logging.info(f"[Bot {bot_index + 1}] File already exists in R2: {unique_file_id}")
            
            # Update bot file ID in database
            db = get_database()
            db.store_file(
                unique_file_id=unique_file_id,
                bot_index=bot_index,
                file_id=file_id,
                file_name=file_name,
                file_size=file_size,
                mime_type=mime_type,
                dc_id=dc_id,
                channel_id=channel_id
            )
            
            # Only reply if this is the base bot
            if should_reply:
                # Generate file link
                fqdn = Var.FQDN
                if not fqdn:
                    fqdn = "your-domain.com"
                
                file_link = f"https://{fqdn}/files/{unique_file_id}"
                
                # Format file details
                size_str = format_file_size(file_size)
                dc_str = f"DC {dc_id}" if dc_id else "Unknown DC"
                mime_str = mime_type or "Unknown"
                
                reply_text = f"✅ **File Already Exists**\n\n"
                reply_text += f"**Name:** {file_name}\n"
                reply_text += f"**Size:** {size_str}\n"
                reply_text += f"**Type:** {mime_str}\n"
                reply_text += f"**Location:** {dc_str}\n\n"
                reply_text += f"📥 **Use the button below to view and download**"
                
                # Create button - only View File button for duplicate files
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 View File", url=file_link)]
                ])
                
                # Reply to the message
                await message.reply_text(reply_text, reply_markup=keyboard)
        
        else:
            # File doesn't exist in R2 - new file detected
            logging.info(f"[Bot {bot_index + 1}] New file detected: {unique_file_id}")
            
            # Store this bot's file_id in database immediately
            db = get_database()
            db.store_file(
                unique_file_id=unique_file_id,
                bot_index=bot_index,
                file_id=file_id,
                file_name=file_name,
                file_size=file_size,
                mime_type=mime_type,
                dc_id=dc_id,
                channel_id=channel_id
            )
            
            # Check if this is the FIRST bot to see this file
            is_first_bot = unique_file_id not in pending_r2_uploads
            
            if is_first_bot:
                # Mark as pending and schedule delayed R2 upload
                pending_r2_uploads.add(unique_file_id)
                logging.info(f"[Bot {bot_index + 1}] Scheduling R2 upload in {R2_UPLOAD_DELAY}s: {unique_file_id}")
                
                # Schedule delayed upload task
                asyncio.create_task(delayed_r2_upload(
                    unique_file_id=unique_file_id,
                    file_name=file_name,
                    file_size=file_size,
                    file_type=file_type,
                    mime_type=mime_type,
                    caption=caption,
                    message_id=message_id,
                    channel_id=channel_id
                ))
            else:
                # Another bot already scheduled the upload
                logging.info(f"[Bot {bot_index + 1}] R2 upload already scheduled by another bot: {unique_file_id}")
            
            # Only reply if this is the base bot
            if should_reply:
                # Generate file link
                fqdn = Var.FQDN
                if not fqdn:
                    fqdn = "your-domain.com"
                
                file_link = f"https://{fqdn}/files/{unique_file_id}"
                
                # Generate 3-hour temporary download link
                from WebStreamer.auth import generate_download_signature
                import time
                expires_at = int(time.time()) + (3 * 60 * 60)  # 3 hours from now
                signature = generate_download_signature(unique_file_id, expires_at, Var.DOWNLOAD_SECRET_KEY)
                temp_download_link = f"https://{fqdn}/download/{unique_file_id}/{expires_at}/{signature}"
                
                # Format file details
                size_str = format_file_size(file_size)
                dc_str = f"DC {dc_id}" if dc_id else "Unknown DC"
                mime_str = mime_type or "Unknown"
                
                reply_text = f"📁 **File Stored Successfully**\n\n"
                reply_text += f"**Name:** {file_name}\n"
                reply_text += f"**Size:** {size_str}\n"
                reply_text += f"**Type:** {mime_str}\n"
                reply_text += f"**Location:** {dc_str}\n\n"
                
                # Add note about R2 upload
                if is_first_bot:
                    reply_text += f"⏱️ Collecting all bot IDs... R2 upload in {R2_UPLOAD_DELAY}s\n\n"
                
                reply_text += f"📥 **Use the buttons below to access your file**"
                
                # Create buttons - View File + 3 Hour Direct Link for new files
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 View File", url=file_link)],
                    [InlineKeyboardButton("⏱️ 3 Hour Link", url=temp_download_link)]
                ])
                
                # Reply to the message
                await message.reply_text(reply_text, reply_markup=keyboard)
        
    except Exception as e:
        logging.error(f"[Bot {bot_index + 1}] Error storing media info: {e}", exc_info=True)

# Handler for private messages - guide user to add bot to channel
@StreamBot.on_message(filters.private & MEDIA_FILTER, group=1)
async def handle_private_media(client, message: Message):
    """Guide user to add bot to channel instead of sending files directly"""
    try:
        # Don't store files from private messages
        bot_username = (await client.get_me()).username
        
        reply_text = "🤖 **Please add me to a channel to store files**\n\n"
        reply_text += "I don't store files from private messages. Instead:\n"
        reply_text += "1️⃣ Add me to a channel where you are an owner/admin\n"
        reply_text += "2️⃣ Post your files in that channel\n"
        reply_text += "3️⃣ I'll reply with a download link\n\n"
        reply_text += "👇 Click the button below to add me to your channel"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Bot to Channel", 
                                url=f"https://t.me/{bot_username}?startchannel=true")]
        ])
        
        await message.reply_text(reply_text, reply_markup=keyboard, quote=True)
        
    except Exception as e:
        logging.error(f"Error handling private media: {e}", exc_info=True)

# Handler for channel/group messages on base bot (StreamBot)
@StreamBot.on_message((filters.channel | filters.group) & MEDIA_FILTER, group=1)
async def handle_channel_media_base_bot(client, message: Message):
    """Handle media files on base bot - stores and replies"""
    await store_channel_media(client, message, bot_index=0, should_reply=True)

def register_multi_client_handlers():
    """
    Register handlers on all multi_clients.
    This should be called after multi_clients are initialized.
    """
    from pyrogram.handlers import MessageHandler
    
    for bot_index, bot_client in multi_clients.items():
        if bot_index == 0:
            # Skip base bot, already has handler registered
            continue
        
        # ===== Channel/Group Media Handler =====
        # Create handler function with proper closure for channel messages
        def make_channel_handler(bot_idx):
            async def handler(client, message: Message):
                """Handle media files on multi-client - stores silently without reply"""
                await store_channel_media(client, message, bot_index=bot_idx, should_reply=False)
            return handler
        
        # Create the handler with captured bot_index
        channel_handler_func = make_channel_handler(bot_index)
        
        # Register channel/group handler on this client
        bot_client.add_handler(
            MessageHandler(
                channel_handler_func,
                filters=(filters.channel | filters.group) & MEDIA_FILTER
            ),
            group=1
        )
        
        logging.info(f"Registered channel media handler on bot {bot_index + 1} (b_{bot_index + 1})")
        
        # ===== Private Message Handler =====
        # Create handler for private messages
        def make_private_handler(bot_idx):
            async def handler(client, message: Message):
                """Guide user to add bot to channel instead of sending files directly"""
                try:
                    # Don't store files from private messages
                    bot_username = (await client.get_me()).username
                    
                    reply_text = "🤖 **Please add me to a channel to store files**\n\n"
                    reply_text += "I don't store files from private messages. Instead:\n"
                    reply_text += "1️⃣ Add me to a channel where you are an owner/admin\n"
                    reply_text += "2️⃣ Post your files in that channel\n"
                    reply_text += "3️⃣ I'll reply with a download link\n\n"
                    reply_text += "👇 Click the button below to add me to your channel"
                    
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("➕ Add Bot to Channel", 
                                            url=f"https://t.me/{bot_username}?startchannel=true")]
                    ])
                    
                    await message.reply_text(reply_text, reply_markup=keyboard, quote=True)
                    
                except Exception as e:
                    logging.error(f"[Bot {bot_idx + 1}] Error handling private media: {e}", exc_info=True)
            return handler
        
        # Create private handler
        private_handler_func = make_private_handler(bot_index)
        
        # Register private message handler
        bot_client.add_handler(
            MessageHandler(
                private_handler_func,
                filters=filters.private & MEDIA_FILTER
            ),
            group=1
        )
        
        logging.info(f"Registered private media handler on bot {bot_index + 1} (b_{bot_index + 1})")
        
        # ===== Start Command Handler =====
        # Create handler for /start command
        def make_start_handler(bot_idx):
            async def handler(client, message: Message):
                """Handle /start command on multi-client"""
                try:
                    from WebStreamer.database import get_database
                    from WebStreamer.vars import Var
                    
                    user = message.from_user
                    if not user:
                        await message.reply_text("Unable to identify user.")
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
                    reply_text += "4️⃣ Access files through the web interface"
                    
                    bot_username = (await client.get_me()).username
                    
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("➕ Add Bot to Channel", 
                                            url=f"https://t.me/{bot_username}?startchannel=true")],
                        [InlineKeyboardButton("🌐 Browse Files", url=f"https://{Var.FQDN}/files" if Var.FQDN else "https://your-domain.com/files")]
                    ])
                    
                    await message.reply_text(reply_text, reply_markup=keyboard)
                    
                except Exception as e:
                    logging.error(f"[Bot {bot_idx + 1}] Error in start command: {e}", exc_info=True)
                    await message.reply_text("An error occurred. Please try again.")
            return handler
        
        # Create start handler
        start_handler_func = make_start_handler(bot_index)
        
        # Register start command handler
        bot_client.add_handler(
            MessageHandler(
                start_handler_func,
                filters=filters.command(["start"]) & filters.private
            ),
            group=0
        )
        
        logging.info(f"Registered start command handler on bot {bot_index + 1} (b_{bot_index + 1})")
