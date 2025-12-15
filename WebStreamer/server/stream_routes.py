# Simplified streaming routes - no database, no auth
import re
import time
import math
import logging
import secrets
import mimetypes
from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine
from WebStreamer import bot_loop
from functools import partial
from WebStreamer.bot import multi_clients, work_loads
from WebStreamer.server.exceptions import FIleNotFound, InvalidHash
from WebStreamer import Var, utils, StartTime, __version__, StreamBot
from concurrent.futures import ThreadPoolExecutor
import urllib.parse
from WebStreamer.r2_storage import get_r2_storage

THREADPOOL = ThreadPoolExecutor(max_workers=1000)

# In-memory cache for file metadata to reduce R2 lookups
# Especially useful for download managers that send multiple parallel requests
class MetadataCache:
    def __init__(self, ttl_seconds=300):  # 5 minute TTL
        self._cache = {}
        self._ttl = ttl_seconds
    
    def get(self, key):
        """Get cached metadata if not expired"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                return data
            else:
                # Expired, remove it
                del self._cache[key]
        return None
    
    def set(self, key, value):
        """Cache metadata with current timestamp"""
        self._cache[key] = (value, time.time())
    
    def cleanup(self):
        """Remove expired entries (call periodically if needed)"""
        current_time = time.time()
        expired_keys = [k for k, (_, ts) in self._cache.items() if current_time - ts >= self._ttl]
        for k in expired_keys:
            del self._cache[k]

# Global metadata cache instance
metadata_cache = MetadataCache(ttl_seconds=300)  # Cache for 5 minutes

async def sync_to_async(func, *args, wait=True, **kwargs):
    pfunc = partial(func, *args, **kwargs)
    future = bot_loop.run_in_executor(THREADPOOL, pfunc)
    return await future if wait else future

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(_):
    # Pass the start timestamp to JavaScript for real-time updates
    start_timestamp = int(StartTime * 1000)  # Convert to milliseconds for JS
    
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>LinkerX CDN</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            color: #b0bec5;
            display: table;
            font-weight: 100;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        }}
        .container {{
            text-align: center;
            display: table-cell;
            vertical-align: middle;
        }}
        .content {{
            text-align: center;
            display: inline-block;
        }}
        .message {{
            font-size: 72px;
            margin-bottom: 30px;
            background: linear-gradient(90deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-weight: 600;
        }}
        .status {{
            display: inline-flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 20px;
        }}
        .status-dot {{
            width: 12px;
            height: 12px;
            background: #4ade80;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        .submessage {{
            font-size: 32px;
            margin-bottom: 40px;
            color: #94a3b8;
        }}
        .timer {{
            font-family: 'Courier New', monospace;
            color: #e2e8f0;
            font-size: 36px;
        }}
        .copyright {{
            font-size: 18px;
            color: #64748b;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="content">
            <div class="message">LinkerX CDN</div>
            <div class="status">
                <span class="status-dot"></span>
                <span style="color: #4ade80; font-size: 24px;">All Systems Operational</span>
            </div>
            <div class="submessage">Uptime: <span id="uptime" class="timer">0d 0h 0m 0s</span></div>
            <div class="copyright">Hash Hackers and LiquidX Projects</div>
        </div>
    </div>
    
    <script>
        const startTime = {start_timestamp};
        
        function updateUptime() {{
            const now = Date.now();
            const diff = Math.floor((now - startTime) / 1000);
            
            const days = Math.floor(diff / 86400);
            const hours = Math.floor((diff % 86400) / 3600);
            const minutes = Math.floor((diff % 3600) / 60);
            const seconds = diff % 60;
            
            let timeStr = '';
            if (days > 0) timeStr += days + 'd ';
            timeStr += hours + 'h ' + minutes + 'm ' + seconds + 's';
            
            document.getElementById('uptime').textContent = timeStr;
        }}
        
        updateUptime();
        setInterval(updateUptime, 1000);
    </script>
</body>
</html>'''
    
    return web.Response(text=html_content, content_type="text/html")

@routes.get("/favicon.ico", allow_head=True)
async def favicon_handler(_):
    """Serve favicon"""
    favicon_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect fill="#667eea" width="100" height="100" rx="15"/>
        <path fill="#fff" d="M30 25h40v10H30zm0 20h40v10H30zm0 20h30v10H30z"/>
        <circle fill="#764ba2" cx="75" cy="70" r="8"/>
    </svg>'''
    return web.Response(body=favicon_svg, content_type="image/svg+xml")

# Public API to generate download link from channel/message
@routes.get("/link/{path:.*}", allow_head=True)
async def link_route_handler(request: web.Request):
    """Generate download link for a file from channel_id/message_id - No auth, no expiry, no database"""
    try:
        # eg. path is /link/channelid/messageid
        parts = request.match_info['path'].split("/")
        if len(parts) != 2:
            return web.json_response({
                'success': False,
                'error': 'Invalid path. Use format: /link/{channel_id}/{message_id}'
            }, status=400)

        channel_id, message_id = parts
        
        # Get file properties from Telegram
        index = min(work_loads, key=work_loads.get)
        faster_client = multi_clients[index]
        
        if Var.MULTI_CLIENT:
            logging.info(f"Client {index} is now serving {request.remote}")

        if faster_client in class_cache:
            tg_connect = class_cache[faster_client]
            logging.debug(f"Using cached ByteStreamer object for client {index}")
        else:
            logging.debug(f"Creating new ByteStreamer object for client {index}")
            tg_connect = utils.ByteStreamer(faster_client)
            class_cache[faster_client] = tg_connect
        
        logging.debug(f"Getting file properties for message {message_id} in channel {channel_id}")
        file_id = await tg_connect.get_file_properties(int(message_id), int(channel_id))
        
        # Extract file information
        unique_file_id = file_id.unique_id
        telegram_file_id = file_id.file_id
        file_name = file_id.file_name
        file_size = file_id.file_size
        mime_type = file_id.mime_type
        
        # Store metadata in R2 with merge logic
        r2 = get_r2_storage()
        try:
            # Get bot's Telegram user ID
            bot_me = await faster_client.get_me()
            bot_user_id = bot_me.id
            
            # Determine file type based on mime_type
            file_type = None
            if mime_type:
                if mime_type.startswith('video/'):
                    file_type = "video"
                elif mime_type.startswith('audio/'):
                    file_type = "audio"
                else:
                    file_type = "document"
            
            # Fetch existing data from R2 first
            existing_data = r2.get_file_metadata(unique_file_id)
            
            if existing_data:
                logging.info(f"Found existing R2 data for {unique_file_id}, merging bot_file_ids")
            
            # Format with merge
            r2_data = r2.format_file_metadata(
                unique_file_id=unique_file_id,
                bot_user_id=bot_user_id,
                file_id=telegram_file_id,
                file_name=file_name,
                file_size=file_size,
                mime_type=mime_type,
                message_id=int(message_id),
                channel_id=int(channel_id),
                file_type=file_type,
                existing_data=existing_data
            )
            
            # Upload merged data
            r2.upload_file_metadata(unique_file_id, r2_data)
            
            bot_count = len(r2_data.get("bot_file_ids", {}))
            logging.info(f"Uploaded metadata to R2: {unique_file_id} - Bot {bot_user_id} (Total bots: {bot_count})")
        except Exception as r2_error:
            logging.warning(f"Failed to upload to R2: {r2_error}")
        
        # Build permanent download URL
        fqdn = Var.FQDN
        download_url = f"https://{fqdn}/dl/{unique_file_id}/{telegram_file_id}"
        
        return web.json_response({
            'success': True,
            'download_url': download_url,
            'file_info': {
                'unique_file_id': unique_file_id,
                'file_name': file_name,
                'file_size': file_size,
                'file_size_formatted': str(await formatFileSize(file_size)),
                'mime_type': mime_type
            }
        })
        
    except FileNotFoundError as e:
        return web.json_response({
            'success': False,
            'error': 'File not found',
            'message': str(e)
        }, status=404)
    except Exception as e:
        error_message = str(e)
        logging.error(f"Error generating link: {error_message}", exc_info=True)
        return web.json_response({
            'success': False,
            'error': 'Internal server error',
            'message': error_message
        }, status=500)

@routes.get("/dl/{unique_file_id}/{file_id}", allow_head=True)
async def direct_download(request: web.Request):
    """Stream file directly using file_id - no database, metadata from R2 with caching"""
    try:
        unique_file_id = request.match_info['unique_file_id']
        file_id = request.match_info['file_id']
        
        logging.info(f"Direct download request for unique_file_id: {unique_file_id}, file_id: {file_id}")
        
        # Get a client to stream with
        index = min(work_loads, key=work_loads.get)
        faster_client = multi_clients[index]
        
        if faster_client in class_cache:
            tg_connect = class_cache[faster_client]
        else:
            tg_connect = utils.ByteStreamer(faster_client)
            class_cache[faster_client] = tg_connect
        
        # Decode file_id to get file properties
        from pyrogram.file_id import FileId
        file_id_obj = FileId.decode(file_id)
        
        # Try to get metadata from cache first, then R2
        r2_metadata = metadata_cache.get(unique_file_id)
        
        if r2_metadata:
            logging.debug(f"Using cached metadata for {unique_file_id}")
        else:
            # Cache miss - fetch from R2
            r2 = get_r2_storage()
            r2_metadata = r2.get_file_metadata(unique_file_id)
            
            if r2_metadata:
                # Store in cache for future requests
                metadata_cache.set(unique_file_id, r2_metadata)
                logging.info(f"File metadata found in R2 and cached: {unique_file_id}")
        
        if r2_metadata:
            # Use metadata from cache/R2
            file_size = r2_metadata.get('file_size_bytes', 0)
            mime_type = r2_metadata.get('mime_type', 'application/octet-stream')
            file_name = r2_metadata.get('file_name', 'file')
            
            setattr(file_id_obj, "file_size", file_size)
            setattr(file_id_obj, "mime_type", mime_type)
            setattr(file_id_obj, "file_name", file_name)
            
            logging.info(f"Using R2 metadata: {file_name} ({file_size} bytes)")
        else:
            # No R2 metadata, try to get from Telegram or use defaults
            logging.warning(f"No R2 metadata found for {unique_file_id}, will try Telegram")
            setattr(file_id_obj, "file_size", 0)
            setattr(file_id_obj, "mime_type", "application/octet-stream")
            setattr(file_id_obj, "file_name", "file")
        
        file_size = file_id_obj.file_size
        
        # If file_size is 0, we need to get it from Telegram
        if file_size == 0:
            try:
                # This might fail if the file_id is not accessible by this client
                message = await faster_client.get_messages(file_id_obj.chat_id, file_id_obj.message_id)
                media = message.video or message.audio or message.document
                if media:
                    file_size = media.file_size
                    setattr(file_id_obj, "file_size", file_size)
                    # Also get filename if available
                    if hasattr(media, 'file_name') and media.file_name:
                        setattr(file_id_obj, "file_name", media.file_name)
                    if hasattr(media, 'mime_type') and media.mime_type:
                        setattr(file_id_obj, "mime_type", media.mime_type)
            except Exception as tg_error:
                logging.warning(f"Failed to get file info from Telegram: {tg_error}")
                # If we can't get size, set a large default
                file_size = 1024 * 1024 * 1024  # 1GB default
                setattr(file_id_obj, "file_size", file_size)
        
        # Handle range requests
        range_header = request.headers.get("Range", 0)
        if range_header:
            from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
            from_bytes = int(from_bytes)
            until_bytes = int(until_bytes) if until_bytes else file_size - 1
        else:
            from_bytes = request.http_range.start or 0
            until_bytes = (request.http_range.stop or file_size) - 1
        
        if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
            return web.Response(
                status=416,
                body="416: Range not satisfiable",
                headers={"Content-Range": f"bytes */{file_size}"},
            )
        
        chunk_size = 1024 * 1024
        until_bytes = min(until_bytes, file_size - 1)
        
        offset = from_bytes - (from_bytes % chunk_size)
        first_part_cut = from_bytes - offset
        last_part_cut = until_bytes % chunk_size + 1
        
        req_length = until_bytes - from_bytes + 1
        part_count = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)
        
        body = tg_connect.yield_file(
            file_id_obj, index, offset, first_part_cut, last_part_cut, part_count, chunk_size
        )
        
        mime_type = file_id_obj.mime_type
        file_name = file_id_obj.file_name
        disposition = "attachment"
        
        if mime_type:
            if not file_name:
                try:
                    file_name = f"{secrets.token_hex(2)}.{mime_type.split('/')[1]}"
                except (IndexError, AttributeError):
                    file_name = f"{secrets.token_hex(2)}.unknown"
        else:
            if file_name:
                mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
            else:
                mime_type = "application/octet-stream"
                file_name = f"{secrets.token_hex(2)}.unknown"
        
        if "video/" in mime_type or "audio/" in mime_type or "/html" in mime_type:
            disposition = "inline"
        
        logging.info(f"Successfully streaming file: {file_name}")
        
        return web.Response(
            status=206 if range_header else 200,
            body=body,
            headers={
                "Content-Type": f"{mime_type}",
                "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
                "Content-Length": str(req_length),
                "Content-Disposition": f'{disposition}; filename="{file_name}"',
                "Accept-Ranges": "bytes",
            },
        )
        
    except Exception as e:
        logging.error(f"Error in direct_download: {e}", exc_info=True)
        raise web.HTTPInternalServerError(
            text='<html><body><h1>Failed to Stream File</h1></body></html>',
            content_type="text/html"
        )

class_cache = {}

async def formatFileSize(bytes_size: int) -> str:
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
