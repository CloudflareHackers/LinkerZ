# Simplified media handler - single "DL Link" button - No R2, local tracking only
import logging
import time
import asyncio
import urllib.parse
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
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
# Cleanup interval (run every 2 minutes)
CLEANUP_INTERVAL = 120

# Cache for bot user IDs to avoid repeated get_me() calls
# Format: {client_id: bot_user_id}
_bot_user_id_cache = {}

# Flag to track if cleanup task is running
_cleanup_task_started = False


async def scheduled_cleanup():
    """Background task to periodically clean up expired entries from _processed_messages"""
    global _processed_messages
    while True:
        try:
            await asyncio.sleep(CLEANUP_INTERVAL)
            current_time = time.time()
            async with _processed_lock:
                # Find and remove expired entries
                expired_keys = [
                    k for k, ts in _processed_messages.items()
                    if current_time - ts > PROCESSED_TTL
                ]
                for k in expired_keys:
                    del _processed_messages[k]
                
                if expired_keys:
                    logging.debug(f"Cleaned up {len(expired_keys)} expired message entries")
        except Exception as e:
            logging.error(f"Error in scheduled cleanup: {e}")


def start_cleanup_task():
    """Start the cleanup background task if not already running"""
    global _cleanup_task_started
    if not _cleanup_task_started:
        asyncio.create_task(scheduled_cleanup())
        _cleanup_task_started = True
        logging.info("Started scheduled cleanup task for processed messages")

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

async def get_bot_user_id(client) -> int:
    """Get bot user ID - uses ENV variable first, then falls back to API with caching"""
    # Use BOT_ID from environment if set
    if Var.BOT_ID:
        return Var.BOT_ID
    
    client_id = id(client)
    
    # Check cache first
    if client_id in _bot_user_id_cache:
        return _bot_user_id_cache[client_id]
    
    # Fetch from API and cache (fallback)
    try:
        bot_me = await client.get_me()
        bot_user_id = bot_me.id
        _bot_user_id_cache[client_id] = bot_user_id
        logging.info(f"Cached bot user ID from API: {bot_user_id}")
        return bot_user_id
    except Exception as e:
        logging.error(f"Failed to get bot user ID: {e}")
        # Return a fallback based on client id (not ideal but prevents crash)
        return client_id

async def store_and_reply_to_media(client, message: Message):
    """
    Store media file and reply with DL Link button
    
    Args:
        client: Pyrogram client
        message: Message containing media
    """
    try:
        # Check if sending links to channels is enabled
        if not Var.SEND_LINKS_TO_CHANNELS:
            logging.debug(f"Skipping link reply - SEND_LINKS_TO_CHANNELS is disabled")
            return
        
        # Get media information
        media = message.video or message.audio or message.document
        if not media:
            return
        
        unique_file_id = media.file_unique_id
        file_id = media.file_id
        file_name = getattr(media, 'file_name', None) or f"file_{unique_file_id}"
        file_size = getattr(media, 'file_size', 0)
        
        # Get channel ID and message ID
        channel_id = message.chat.id if message.chat else None
        message_id = message.id
        
        # Get bot's Telegram user ID (cached to avoid repeated API calls)
        bot_user_id = await get_bot_user_id(client)
        
        # Check if this message was already processed by any bot (prevent duplicate processing)
        if await is_message_processed(channel_id, message_id, bot_user_id):
            logging.debug(f"Skipping already processed message {message_id} in {channel_id} for bot {bot_user_id}")
            return
        
        # Mark message as being processed immediately to prevent race conditions
        await mark_message_processed(channel_id, message_id, bot_user_id)
        
        # Determine file type
        file_type = None
        if message.video:
            file_type = "video"
        elif message.audio:
            file_type = "audio"
        elif message.document:
            file_type = "document"
        
        logging.info(f"Processing {file_type}: {unique_file_id} - Bot {bot_user_id}")
        
        # Generate download link with new format: /dl/unique_file_id/file_id/size/filename
        fqdn = Var.FQDN
        if not fqdn:
            fqdn = "your-domain.com"
        
        # URL encode the filename for safe URL usage
        safe_filename = urllib.parse.quote(file_name, safe='')
        download_url = f"https://{fqdn}/dl/{unique_file_id}/{file_id}/{file_size}/{safe_filename}"
        
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
    # Ensure cleanup task is running
    start_cleanup_task()
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
