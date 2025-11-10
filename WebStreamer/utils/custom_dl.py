import math
import asyncio
import logging
from WebStreamer import Var
from typing import Dict, Union
from WebStreamer.bot import work_loads
from pyrogram import Client, utils, raw
from .file_properties import get_file_ids
from pyrogram.session import Session, Auth
import inspect
from pyrogram.errors import AuthBytesInvalid
from WebStreamer.server.exceptions import FIleNotFound
from pyrogram.file_id import FileId, FileType, ThumbnailSource


def get_dc_config(dc_id, test_mode):
    """
    Get the server address and port for a given DC ID.
    Returns (server_address, port) tuple.
    """
    if test_mode:
        dc_configs = {
            1: ("149.154.175.10", 443),
            2: ("149.154.167.40", 443),
            3: ("149.154.175.117", 443),
        }
    else:
        # Production DCs
        dc_configs = {
            1: ("149.154.175.53", 443),
            2: ("149.154.167.51", 443),
            3: ("149.154.175.100", 443),
            4: ("149.154.167.91", 443),
            5: ("91.108.56.128", 443),
        }
    
    return dc_configs.get(dc_id, ("149.154.167.51", 443))


async def create_auth_safe(client, dc_id, test_mode):
    """
    Safely create an Auth object and get auth_key with compatibility for different Pyrogram versions.
    Tries multiple signature patterns to find the one that works.
    """
    # Get the Auth.__init__ signature to understand what parameters it accepts
    sig = inspect.signature(Auth.__init__)
    param_names = [p for p in sig.parameters.keys() if p != 'self']
    
    logging.debug(f"Auth.__init__ parameters: {param_names}")
    
    # Check if we need server_address and port (newer Pyrogram versions)
    if 'server_address' in param_names and 'port' in param_names:
        try:
            # Pattern 4: With server_address and port (newest version)
            logging.debug("Trying Auth pattern 4: with server_address and port")
            
            # Try to get DC configuration from Pyrogram's internal DC map
            try:
                from pyrogram.session.internals import DataCenter
                dc = DataCenter(dc_id, test_mode)
                server_address = dc.address
                port = dc.port
                logging.debug(f"Using DataCenter class: {server_address}:{port}")
            except Exception:
                # Fallback to hardcoded DC addresses
                server_address, port = get_dc_config(dc_id, test_mode)
                logging.info(f"Using hardcoded DC config: {server_address}:{port} for DC {dc_id}")
            
            auth = Auth(
                client,
                dc_id,
                server_address,
                port,
                test_mode
            )
            return await auth.create()
        except Exception as e:
            logging.debug(f"Auth pattern 4 failed: {e}")
    
    # Try Pattern 1: Old style positional arguments (client, dc_id, test_mode)
    try:
        logging.debug("Trying Auth pattern 1: positional arguments")
        auth = Auth(client, dc_id, test_mode)
        return await auth.create()
    except TypeError as e:
        logging.debug(f"Auth pattern 1 failed: {e}")
    
    # Try Pattern 2: Keyword arguments
    try:
        logging.debug("Trying Auth pattern 2: keyword arguments")
        auth = Auth(
            client=client,
            dc_id=dc_id,
            test_mode=test_mode
        )
        return await auth.create()
    except TypeError as e:
        logging.debug(f"Auth pattern 2 failed: {e}")
    
    # Try Pattern 3: With server_address and port using keyword args
    if 'server_address' in param_names and 'port' in param_names:
        try:
            logging.debug("Trying Auth pattern 3: keyword arguments with server_address and port")
            server_address, port = get_dc_config(dc_id, test_mode)
            auth = Auth(
                client=client,
                dc_id=dc_id,
                server_address=server_address,
                port=port,
                test_mode=test_mode
            )
            return await auth.create()
        except TypeError as e:
            logging.debug(f"Auth pattern 3 failed: {e}")
    
    # If all patterns fail, log the signature and raise an error
    logging.error(f"Failed to create Auth. Signature: {sig}")
    logging.error(f"Parameters attempted: client={type(client).__name__}, dc_id={dc_id}, test_mode={test_mode}")
    raise RuntimeError(f"Could not create Auth with any known signature. Auth.__init__ parameters: {param_names}")


def create_session_safe(client, dc_id, auth_key, test_mode, is_media=True):
    """
    Safely create a Session object with compatibility for different Pyrogram versions.
    Tries multiple signature patterns to find the one that works.
    """
    # Get the Session.__init__ signature to understand what parameters it accepts
    sig = inspect.signature(Session.__init__)
    param_names = [p for p in sig.parameters.keys() if p != 'self']
    
    logging.debug(f"Session.__init__ parameters: {param_names}")
    
    # Try different patterns based on parameter names
    
    # Check if we need server_address and port (newer Pyrogram versions)
    if 'server_address' in param_names and 'port' in param_names:
        try:
            # Pattern 4: With server_address and port (newest version)
            logging.debug("Trying pattern 4: with server_address and port")
            
            # Get DC configuration from Pyrogram's internal DC map
            from pyrogram.session.internals import DataCenter
            dc = DataCenter(dc_id, test_mode)
            
            return Session(
                client,
                dc_id,
                dc.address,  # server_address
                dc.port,     # port
                auth_key,
                test_mode,
                is_media=is_media
            )
        except Exception as e:
            logging.debug(f"Pattern 4 failed: {e}")
            
            # Fallback: Try to get DC info from client or use hardcoded values
            try:
                logging.debug("Trying pattern 4b: with hardcoded DC addresses")
                
                # Hardcoded DC addresses as fallback (Telegram's standard DCs)
                dc_configs = {
                    1: ("149.154.175.53", 443),
                    2: ("149.154.167.51", 443),
                    3: ("149.154.175.100", 443),
                    4: ("149.154.167.91", 443),
                    5: ("91.108.56.128", 443),
                }
                
                if test_mode:
                    dc_configs = {
                        1: ("149.154.175.10", 443),
                        2: ("149.154.167.40", 443),
                        3: ("149.154.175.117", 443),
                    }
                
                server_address, port = dc_configs.get(dc_id, ("149.154.167.51", 443))
                logging.info(f"Using DC config: {server_address}:{port} for DC {dc_id}")
                
                return Session(
                    client,
                    dc_id,
                    server_address,
                    port,
                    auth_key,
                    test_mode,
                    is_media=is_media
                )
            except Exception as e2:
                logging.debug(f"Pattern 4b failed: {e2}")
                pass
    
    try:
        # Pattern 1: Positional arguments (old style)
        if len(param_names) >= 4:
            logging.debug("Trying pattern 1: positional arguments")
            return Session(client, dc_id, auth_key, test_mode, is_media=is_media)
    except TypeError as e:
        logging.debug(f"Pattern 1 failed: {e}")
        pass
    
    try:
        # Pattern 2: Keyword arguments
        logging.debug("Trying pattern 2: keyword arguments")
        return Session(
            client=client,
            dc_id=dc_id,
            auth_key=auth_key,
            test_mode=test_mode,
            is_media=is_media
        )
    except TypeError as e:
        logging.debug(f"Pattern 2 failed: {e}")
        pass
    
    try:
        # Pattern 3: Without is_media parameter
        logging.debug("Trying pattern 3: without is_media")
        return Session(client, dc_id, auth_key, test_mode)
    except TypeError as e:
        logging.debug(f"Pattern 3 failed: {e}")
        pass
    
    # If all patterns fail, log the signature and raise an error
    logging.error(f"Failed to create Session. Signature: {sig}")
    logging.error(f"Parameters attempted: client={type(client).__name__}, dc_id={dc_id}, auth_key=<bytes>, test_mode={test_mode}, is_media={is_media}")
    raise RuntimeError(f"Could not create Session with any known signature. Session.__init__ parameters: {param_names}")


class ByteStreamer:
    def __init__(self, client: Client):
        """A custom class that holds the cache of a specific client and class functions.
        attributes:
            client: the client that the cache is for.
            cached_file_ids: a dict of cached file IDs.
            cached_file_properties: a dict of cached file properties.
        
        functions:
            generate_file_properties: returns the properties for a media of a specific message contained in Tuple.
            generate_media_session: returns the media session for the DC that contains the media file.
            yield_file: yield a file from telegram servers for streaming.
            
        This is a modified version of the <https://github.com/eyaadh/megadlbot_oss/blob/master/mega/telegram/utils/custom_download.py>
        Thanks to Eyaadh <https://github.com/eyaadh>
        """
        self.clean_timer = 30 * 60
        self.client: Client = client
        self.cached_file_ids: Dict[int, FileId] = {}
        asyncio.create_task(self.clean_cache())

    async def get_file_properties(self, message_id: int, channel_id) -> FileId:
        """
        Returns the properties of a media of a specific message in a FIleId class.
        if the properties are cached, then it'll return the cached results.
        or it'll generate the properties from the Message ID and cache them.
        """
        if message_id not in self.cached_file_ids:
            await self.generate_file_properties(message_id, channel_id)
            logging.debug(f"Cached file properties for message with ID {message_id}")
        return self.cached_file_ids[message_id]
    
    async def generate_file_properties(self, message_id: int, channel_id) -> FileId:
        """
        Generates the properties of a media file on a specific message.
        returns ths properties in a FIleId class.
        """
        logging.debug(f"Logging Channel ID {channel_id}")
        file_id = await get_file_ids(self.client, int(channel_id), message_id)
        logging.debug(f"Generated file ID and Unique ID for message with ID {message_id}")
        if not file_id:
            logging.debug(f"Message with ID {message_id} not found")
            raise FIleNotFound
        self.cached_file_ids[message_id] = file_id
        logging.debug(f"Cached media message with ID {message_id}")
        return self.cached_file_ids[message_id]

    async def generate_media_session(self, client: Client, file_id: FileId) -> Session:
        """
        Generates the media session for the DC that contains the media file.
        This is required for getting the bytes from Telegram servers.
        """

        media_session = client.media_sessions.get(file_id.dc_id, None)

        if media_session is None:
            if file_id.dc_id != await client.storage.dc_id():
                auth_key = await Auth(
                    client, file_id.dc_id, await client.storage.test_mode()
                ).create()
                test_mode = await client.storage.test_mode()
                
                # Use safe session creation
                media_session = create_session_safe(
                    client, file_id.dc_id, auth_key, test_mode, is_media=True
                )
                await media_session.start()

                for _ in range(6):
                    exported_auth = await client.invoke(
                        raw.functions.auth.ExportAuthorization(dc_id=file_id.dc_id)
                    )

                    try:
                        await media_session.invoke(
                            raw.functions.auth.ImportAuthorization(
                                id=exported_auth.id, bytes=exported_auth.bytes
                            )
                        )
                        break
                    except AuthBytesInvalid:
                        logging.debug(
                            f"Invalid authorization bytes for DC {file_id.dc_id}"
                        )
                        continue
                else:
                    await media_session.stop()
                    raise AuthBytesInvalid
            else:
                # Use safe session creation
                media_session = create_session_safe(
                    client,
                    file_id.dc_id,
                    await client.storage.auth_key(),
                    await client.storage.test_mode(),
                    is_media=True
                )
                await media_session.start()
            logging.debug(f"Created media session for DC {file_id.dc_id}")
            client.media_sessions[file_id.dc_id] = media_session
        else:
            logging.debug(f"Using cached media session for DC {file_id.dc_id}")
        return media_session


    @staticmethod
    async def get_location(file_id: FileId) -> Union[raw.types.InputPhotoFileLocation,
                                                     raw.types.InputDocumentFileLocation,
                                                     raw.types.InputPeerPhotoFileLocation,]:
        """
        Returns the file location for the media file.
        """
        file_type = file_id.file_type

        if file_type == FileType.CHAT_PHOTO:
            if file_id.chat_id > 0:
                peer = raw.types.InputPeerUser(
                    user_id=file_id.chat_id, access_hash=file_id.chat_access_hash
                )
            else:
                if file_id.chat_access_hash == 0:
                    peer = raw.types.InputPeerChat(chat_id=-file_id.chat_id)
                else:
                    peer = raw.types.InputPeerChannel(
                        channel_id=utils.get_channel_id(file_id.chat_id),
                        access_hash=file_id.chat_access_hash,
                    )

            location = raw.types.InputPeerPhotoFileLocation(
                peer=peer,
                volume_id=file_id.volume_id,
                local_id=file_id.local_id,
                big=file_id.thumbnail_source == ThumbnailSource.CHAT_PHOTO_BIG,
            )
        elif file_type == FileType.PHOTO:
            location = raw.types.InputPhotoFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size,
            )
        else:
            location = raw.types.InputDocumentFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size,
            )
        return location

    async def yield_file(
        self,
        file_id: FileId,
        index: int,
        offset: int,
        first_part_cut: int,
        last_part_cut: int,
        part_count: int,
        chunk_size: int,
    ) -> Union[str, None]:
        """
        Custom generator that yields the bytes of the media file.
        Modded from <https://github.com/eyaadh/megadlbot_oss/blob/master/mega/telegram/utils/custom_download.py#L20>
        Thanks to Eyaadh <https://github.com/eyaadh>
        """
        client = self.client
        work_loads[index] += 1
        logging.debug(f"Starting to yielding file with client {index}.")
        media_session = await self.generate_media_session(client, file_id)

        current_part = 1
        location = await self.get_location(file_id)

        try:
            r = await media_session.invoke(
                raw.functions.upload.GetFile(
                    location=location, offset=offset, limit=chunk_size
                ),
            )
            if isinstance(r, raw.types.upload.File):
                while True:
                    chunk = r.bytes
                    if not chunk:
                        break
                    elif part_count == 1:
                        yield chunk[first_part_cut:last_part_cut]
                    elif current_part == 1:
                        yield chunk[first_part_cut:]
                    elif current_part == part_count:
                        yield chunk[:last_part_cut]
                    else:
                        yield chunk

                    current_part += 1
                    offset += chunk_size

                    if current_part > part_count:
                        break

                    r = await media_session.invoke(
                        raw.functions.upload.GetFile(
                            location=location, offset=offset, limit=chunk_size
                        ),
                    )
        except (TimeoutError, AttributeError):
            pass
        finally:
            logging.debug("Finished yielding file with {current_part} parts.")
            work_loads[index] -= 1

    
    async def clean_cache(self) -> None:
        """
        function to clean the cache to reduce memory usage
        """
        while True:
            await asyncio.sleep(self.clean_timer)
            self.cached_file_ids.clear()
            logging.debug("Cleaned the cache")
