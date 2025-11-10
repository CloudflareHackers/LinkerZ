# Media handler plugin to store file information in database
import logging
from pyrogram import filters
from pyrogram.types import Message
from WebStreamer.database import get_database
from WebStreamer.bot import StreamBot, multi_clients

# Media types we want to track
MEDIA_FILTER = (
    filters.video 
    | filters.audio 
    | filters.document
)

async def store_media_info(client, message: Message):
    """Store media file information in database"""
    try:
        # Determine which bot received this message
        bot_index = None
        client_id = client.me.id if hasattr(client, 'me') else None
        
        if client_id:
            for index, bot_client in multi_clients.items():
                if bot_client.me.id == client_id:
                    bot_index = index
                    break
        
        if bot_index is None:
            # Default to 0 if we can't identify (main bot)
            bot_index = 0
            logging.warning(f"Could not identify bot index, using default (0)")
        
        # Get media information
        media = message.video or message.audio or message.document
        if not media:
            return
        
        unique_file_id = media.file_unique_id
        file_id = media.file_id
        file_name = getattr(media, 'file_name', None) or f"file_{unique_file_id}"
        file_size = getattr(media, 'file_size', 0)
        mime_type = getattr(media, 'mime_type', None)
        
        # Store in database
        db = get_database()
        success = db.store_file(
            unique_file_id=unique_file_id,
            bot_index=bot_index,
            file_id=file_id,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type
        )
        
        if success:
            logging.info(f"Stored media: {file_name} (unique_id: {unique_file_id}, bot: b_{bot_index + 1})")
        
    except Exception as e:
        logging.error(f"Error storing media info: {e}", exc_info=True)

# Handler for private messages (direct to bot)
@StreamBot.on_message(filters.private & MEDIA_FILTER, group=1)
async def handle_private_media(client, message: Message):
    """Handle media files sent directly to bot"""
    await store_media_info(client, message)

# Handler for channel/group messages
@StreamBot.on_message((filters.channel | filters.group) & MEDIA_FILTER, group=1)
async def handle_channel_media(client, message: Message):
    """Handle media files posted in channels/groups where bot is member"""
    await store_media_info(client, message)
