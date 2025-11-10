# Media handler plugin to store file information in database
import logging
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from WebStreamer.database import get_database
from WebStreamer.bot import StreamBot, multi_clients
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

async def store_channel_media(client, message: Message, bot_index: int, should_reply: bool = False):
    """
    Store media file in database. Only replies if should_reply=True.
    
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
        
        # Get channel ID
        channel_id = message.chat.id if message.chat else None
        
        # Store in database
        db = get_database()
        success = db.store_file(
            unique_file_id=unique_file_id,
            bot_index=bot_index,
            file_id=file_id,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            dc_id=dc_id,
            channel_id=channel_id
        )
        
        if success:
            logging.info(f"[Bot {bot_index + 1}] Stored media: {file_name} (unique_id: {unique_file_id}, file_id: {file_id[:20]}...)")
            
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
                
                reply_text = f"📁 **File Stored Successfully**\n\n"
                reply_text += f"**Name:** {file_name}\n"
                reply_text += f"**Size:** {size_str}\n"
                reply_text += f"**Type:** {mime_str}\n"
                reply_text += f"**Location:** {dc_str}\n\n"
                reply_text += f"🔗 View and download at: {file_link}"
                
                # Create button
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 View File", url=file_link)]
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
        
        await message.reply_text(reply_text, reply_markup=keyboard)
        
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
                    
                    await message.reply_text(reply_text, reply_markup=keyboard)
                    
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
