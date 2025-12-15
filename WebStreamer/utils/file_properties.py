from pyrogram import Client, raw, utils
from typing import Any, Optional
from pyrogram.types import Message
from pyrogram.file_id import FileId
from pyrogram.raw.types.messages import Messages
from WebStreamer.server.exceptions import FileNotFound
import logging


async def parse_file_id(message: "Message") -> Optional[FileId]:
    media = get_media_from_message(message)
    if media:
        return FileId.decode(media.file_id)

async def parse_file_unique_id(message: "Messages") -> Optional[str]:
    media = get_media_from_message(message)
    if media:
        return media.file_unique_id

async def resolve_peer_with_raw_api(client: Client, chat_id: int) -> bool:
    """
    Force resolve peer using raw Telegram API.
    This fetches the channel information and caches it in the session.
    """
    try:
        # Convert the chat_id to the proper channel_id format
        channel_id = utils.get_channel_id(chat_id)
        
        logging.info(f"Attempting to resolve peer using raw API for chat_id={chat_id}, channel_id={channel_id}")
        
        # Try to get the channel using raw API with access_hash=0
        # This forces Telegram to resolve the peer
        try:
            result = await client.invoke(
                raw.functions.channels.GetChannels(
                    id=[raw.types.InputChannel(
                        channel_id=channel_id,
                        access_hash=0
                    )]
                )
            )
            logging.info(f"Successfully resolved peer using GetChannels for {chat_id}")
            return True
        except Exception as e1:
            logging.warning(f"GetChannels with access_hash=0 failed: {e1}")
            
            # Alternative: Try getting recent messages/history to cache the peer
            try:
                result = await client.invoke(
                    raw.functions.messages.GetHistory(
                        peer=raw.types.InputPeerChannel(
                            channel_id=channel_id,
                            access_hash=0
                        ),
                        offset_id=0,
                        offset_date=0,
                        add_offset=0,
                        limit=1,
                        max_id=0,
                        min_id=0,
                        hash=0
                    )
                )
                logging.info(f"Successfully resolved peer using GetHistory for {chat_id}")
                return True
            except Exception as e2:
                logging.error(f"GetHistory also failed: {e2}")
                return False
                
    except Exception as e:
        logging.error(f"Failed to resolve peer with raw API: {e}")
        return False

async def get_file_ids(client: Client, chat_id: int, message_id: int) -> Optional[FileId]:
    try:
        message = await client.get_messages(chat_id, message_id)
    except Exception as e:
        error_str = str(e).lower()
        # If we get a "Peer id invalid" error, try to resolve the peer first
        if "peer id invalid" in error_str or "peer_id_invalid" in error_str:
            logging.warning(f"Peer id invalid for chat {chat_id}, attempting to resolve peer...")
            
            # Try raw API resolution first
            if await resolve_peer_with_raw_api(client, chat_id):
                try:
                    message = await client.get_messages(chat_id, message_id)
                    logging.info(f"Successfully fetched message {message_id} after raw API peer resolution")
                except Exception as retry_error:
                    logging.error(f"Still failed after raw API resolution: {retry_error}")
                    # Continue to other methods
                    pass
            
            # If still failing, try other methods
            if not hasattr(locals(), 'message') or locals().get('message') is None:
                try:
                    # Try to resolve peer by getting chat info
                    await client.get_chat(chat_id)
                    logging.info(f"Successfully resolved peer by getting chat info for {chat_id}")
                    # Retry getting the message after resolving peer
                    message = await client.get_messages(chat_id, message_id)
                    logging.info(f"Successfully fetched message {message_id} from chat {chat_id} after peer resolution")
                except Exception as chat_error:
                    logging.warning(f"Failed to get chat info for {chat_id}: {chat_error}")
                    # For bots, GetDialogs is not available. If raw API and get_chat both failed,
                    # we cannot resolve the peer. Log and raise the error.
                    logging.error(f"Unable to resolve peer for chat {chat_id}. All methods exhausted.")
                    raise
        else:
            # Re-raise if it's a different error
            raise
    
    if message.empty:
        raise FileNotFound
    media = get_media_from_message(message)
    file_unique_id = await parse_file_unique_id(message)
    file_id = await parse_file_id(message)
    setattr(file_id, "file_size", getattr(media, "file_size", 0))
    setattr(file_id, "mime_type", getattr(media, "mime_type", ""))
    setattr(file_id, "file_name", getattr(media, "file_name", ""))
    setattr(file_id, "unique_id", file_unique_id)
    setattr(file_id, "file_id", getattr(media, "file_id", ""))  # Store the actual file_id string
    return file_id

def get_media_from_message(message: "Message") -> Any:
    media_types = (
        "audio",
        "document",
        "photo",
        "sticker",
        "animation",
        "video",
        "voice",
        "video_note",
    )
    for attr in media_types:
        media = getattr(message, attr, None)
        if media:
            return media


def get_hash(media_msg: Message) -> str:
    media = get_media_from_message(media_msg)
    return getattr(media, "file_unique_id", "")[:6]

def get_name(media_msg: Message) -> str:
    media = get_media_from_message(media_msg)
    return getattr(media, 'file_name', "")
