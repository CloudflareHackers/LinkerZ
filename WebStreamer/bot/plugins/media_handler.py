# Simplified media handler - single "DL Link" button - No database, R2 only
import logging
import time
import asyncio
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from WebStreamer.r2_storage import get_r2_storage
from WebStreamer.bot import StreamBot
from WebStreamer.vars import Var
from pyrogram.file_id import FileId

# Media types we want to track
MEDIA_FILTER = (
    filters.video 
    | filters.audio 
    | filters.document
)

# In-memory tracking for processed messages to avoid duplicates
# Format: {(chat_id, message_id, bot_id): timestamp}
_processed_messages = {}
_processed_lock = asyncio.Lock()
# TTL for processed message tracking (5 minutes)
PROCESSED_TTL = 300
# Lock timeout to prevent multiple bots processing same message
PROCESS_LOCK_TTL = 30

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

async def is_message_processed(chat_id: int, message_id: int, bot_id: int) -> bool:
    """Check if message was already processed by any bot"""
    async with _processed_lock:
        current_time = time.time()
        
        # Cleanup old entries
        expired_keys = [
            k for k, ts in _processed_messages.items()
            if current_time - ts > PROCESSED_TTL
        ]
        for k in expired_keys:
            del _processed_messages[k]
        
        # Check if this specific message was processed by THIS bot
        key = (chat_id, message_id, bot_id)
        if key in _processed_messages:
            return True
        
        # Check if any bot has processed this message recently (within lock TTL)
        # This prevents duplicate processing by multiple bots
        for (c_id, m_id, b_id), ts in _processed_messages.items():
            if c_id == chat_id and m_id == message_id:
                # Another bot processed it recently
                if current_time - ts < PROCESS_LOCK_TTL:
                    logging.debug(f"Message {message_id} in {chat_id} already being processed by bot {b_id}")
                    return True
        
        return False

async def mark_message_processed(chat_id: int, message_id: int, bot_id: int):
    """Mark message as processed"""
    async with _processed_lock:
        key = (chat_id, message_id, bot_id)
        _processed_messages[key] = time.time()

async def store_and_reply_to_media(client, message: Message):
    """
    Store media file and reply with DL Link button
    
    Args:
        client: Pyrogram client
        message: Message containing media
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
        
        # Get channel ID and message ID
        channel_id = message.chat.id if message.chat else None
        message_id = message.id
        
        # Get caption from message
        caption = message.caption or None
        
        # Determine file type
        file_type = None
        if message.video:
            file_type = "video"
        elif message.audio:
            file_type = "audio"
        elif message.document:
            file_type = "document"
        
        # Extract video-specific metadata if it's a video
        video_duration = None
        video_width = None
        video_height = None
        if message.video:
            video_duration = getattr(media, 'duration', None)
            video_width = getattr(media, 'width', None)
            video_height = getattr(media, 'height', None)
        
        # Store metadata in R2 with merge logic
        r2 = get_r2_storage()
        try:
            # Get bot's Telegram user ID
            bot_me = await client.get_me()
            bot_user_id = bot_me.id
            
            # Fetch existing data from R2 first
            existing_data = r2.get_file_metadata(unique_file_id)
            
            if existing_data:
                logging.info(f"Found existing R2 data for {unique_file_id}, merging bot_file_ids")
            
            # Format with merge (keeps existing bot_file_ids and adds new one)
            r2_data = r2.format_file_metadata(
                unique_file_id=unique_file_id,
                bot_user_id=bot_user_id,
                file_id=file_id,
                file_name=file_name,
                file_size=file_size,
                mime_type=mime_type,
                message_id=message_id,
                channel_id=channel_id,
                caption=caption,
                file_type=file_type,
                video_duration=video_duration,
                video_width=video_width,
                video_height=video_height,
                existing_data=existing_data
            )
            
            # Upload merged data
            r2.upload_file_metadata(unique_file_id, r2_data)
            
            bot_count = len(r2_data.get("bot_file_ids", {}))
            logging.info(f"Uploaded to R2: {unique_file_id} - {file_type} - Bot {bot_user_id} (Total bots: {bot_count})")
        except Exception as r2_error:
            logging.warning(f"Failed to upload to R2: {r2_error}")
        
        # Generate download link
        fqdn = Var.FQDN
        if not fqdn:
            fqdn = "your-domain.com"
        
        download_url = f"https://{fqdn}/dl/{unique_file_id}/{file_id}"
        
        # Check if message already has buttons (from other bot instances)
        existing_buttons = []
        if message.reply_markup and hasattr(message.reply_markup, 'inline_keyboard'):
            # Preserve all existing buttons
            for row in message.reply_markup.inline_keyboard:
                existing_buttons.append(row)
        
        # Add new DL Link button as a new row
        new_button_row = [InlineKeyboardButton("DL Link", url=download_url)]
        existing_buttons.append(new_button_row)
        
        # Create keyboard with all buttons (existing + new)
        keyboard = InlineKeyboardMarkup(existing_buttons)
        
        # Format file details (only add if no existing buttons, meaning first bot)
        size_str = format_file_size(file_size)
        file_info = f"📁 **{file_name}**\n"
        file_info += f"📊 Size: `{size_str}`"
        
        # Check if message is forwarded
        is_forwarded = message.forward_date is not None or message.forward_from is not None or message.forward_from_chat is not None
        
        # If forwarded, reply to message. Otherwise, try to edit caption
        if is_forwarded:
            await message.reply_text(file_info, reply_markup=keyboard)
            logging.info(f"Replied to forwarded file: {unique_file_id}")
        else:
            try:
                # Preserve original caption - don't add file_info again if buttons already exist
                caption = message.caption or ""
                if len(existing_buttons) == 1:
                    # First bot - add file info to caption
                    new_caption = f"{caption}\n\n{file_info}" if caption else file_info
                else:
                    # Other bots - keep caption as is, just add button
                    new_caption = caption
                await message.edit_caption(caption=new_caption, reply_markup=keyboard)
                logging.info(f"Edited caption for file: {unique_file_id} (total buttons: {len(existing_buttons)})")
            except Exception as edit_error:
                error_str = str(edit_error)
                # Check if it's an admin required error
                if "CHAT_ADMIN_REQUIRED" in error_str:
                    logging.warning(f"Bot needs admin permissions: {edit_error}")
                    try:
                        await message.reply_text(
                            "⚠️ **Admin Permissions Required**\n\n"
                            "I need admin permissions to edit messages in this chat.\n\n"
                            "Please make me an **Admin** with the following permissions:\n"
                            "• ✏️ Edit messages\n"
                            "• 📝 Post messages\n"
                            "• 🗑️ Delete messages\n\n"
                            "Once done, I'll be able to add download links directly to posts!"
                        )
                    except Exception as notify_error:
                        logging.error(f"Failed to send admin notification: {notify_error}")
                else:
                    # If edit fails for other reasons, reply with file info instead
                    logging.warning(f"Failed to edit caption, replying instead: {edit_error}")
                    await message.reply_text(file_info, reply_markup=keyboard)
        
    except Exception as e:
        logging.error(f"Error storing media info: {e}", exc_info=True)

# Handler for channel/group messages
@StreamBot.on_message((filters.channel | filters.group) & MEDIA_FILTER, group=1)
async def handle_channel_media(client, message: Message):
    """Handle media files in channels/groups"""
    await store_and_reply_to_media(client, message)

def register_multi_client_handlers():
    """
    Register handlers on all multi_clients.
    This should be called after multi_clients are initialized.
    """
    from pyrogram.handlers import MessageHandler
    from WebStreamer.bot import multi_clients
    
    for bot_index, bot_client in multi_clients.items():
        if bot_index == 0:
            # Skip base bot, already has handler registered
            continue
        
        # Create handler function with proper closure for channel messages
        def make_channel_handler(bot_idx):
            async def handler(client, message: Message):
                """Handle media files on multi-client"""
                await store_and_reply_to_media(client, message)
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
        
        logging.info(f"Registered channel media handler on bot {bot_index + 1}")
