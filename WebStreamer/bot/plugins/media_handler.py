# Simplified media handler - single "DL Link" button
import logging
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from WebStreamer.database import get_database
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
        
        # Store in database
        db = get_database()
        db.store_file(
            unique_file_id=unique_file_id,
            file_id=file_id,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            channel_id=channel_id
        )
        
        # Store in R2
        r2 = get_r2_storage()
        try:
            # Get bot's Telegram user ID
            bot_me = await client.get_me()
            bot_user_id = bot_me.id
            
            r2_data = r2.format_file_data(
                unique_file_id=unique_file_id,
                bot_user_id=bot_user_id,
                file_id=file_id,
                file_name=file_name,
                file_size=file_size,
                mime_type=mime_type,
                message_id=message_id,
                channel_id=channel_id
            )
            
            r2.upload_file_data(unique_file_id, r2_data)
            logging.info(f"Uploaded to R2: {unique_file_id} with bot_id {bot_user_id}")
        except Exception as r2_error:
            logging.warning(f"Failed to upload to R2: {r2_error}")
        
        # Generate download link
        fqdn = Var.FQDN
        if not fqdn:
            fqdn = "your-domain.com"
        
        download_url = f"https://{fqdn}/dl/{unique_file_id}/{file_id}"
        
        # Create single button with "DL Link"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("DL Link", url=download_url)]
        ])
        
        # Format file details
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
                # Preserve original caption if exists
                caption = message.caption or ""
                new_caption = f"{caption}\n\n{file_info}" if caption else file_info
                await message.edit_caption(caption=new_caption, reply_markup=keyboard)
                logging.info(f"Edited caption for file: {unique_file_id}")
            except Exception as edit_error:
                # If edit fails, reply instead
                logging.warning(f"Failed to edit caption, replying instead: {edit_error}")
                await message.reply_text(file_info, reply_markup=keyboard)
        
    except Exception as e:
        logging.error(f"Error storing media info: {e}", exc_info=True)

# Handler for channel/group messages
@StreamBot.on_message((filters.channel | filters.group) & MEDIA_FILTER, group=1)
async def handle_channel_media(client, message: Message):
    """Handle media files in channels/groups"""
    await store_and_reply_to_media(client, message)
