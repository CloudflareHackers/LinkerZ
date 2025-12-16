# Simplified streaming routes - no database, no auth, no R2
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
from WebStreamer.server.exceptions import FileNotFound, InvalidHash
from WebStreamer import Var, utils, StartTime, __version__, StreamBot
from concurrent.futures import ThreadPoolExecutor
import urllib.parse

THREADPOOL = ThreadPoolExecutor(max_workers=1000)


def sanitize_header_value(value: str) -> str:
    """
    Sanitize a string for use in HTTP headers.
    Removes or replaces newline and carriage return characters
    to prevent HTTP header injection attacks.
    """
    if not value:
        return value
    # Remove carriage return and newline characters
    sanitized = value.replace('\r', '').replace('\n', ' ')
    # Also remove any null bytes using chr(0)
    sanitized = sanitized.replace(chr(0), '')
    # Strip leading/trailing whitespace
    return sanitized.strip()

async def sync_to_async(func, *args, wait=True, **kwargs):
    pfunc = partial(func, *args, **kwargs)
    future = bot_loop.run_in_executor(THREADPOOL, pfunc)
    return await future if wait else future

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(_):
    # Pass the start timestamp to JavaScript for real-time updates
    start_timestamp = int(StartTime * 1000)  # Convert to milliseconds for JS
    
    html_content = f'''<html>
<head>
    <title>LinkerX CDN</title>
    <style>
        body{{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato }}
        .container{{ text-align:center; display:table-cell; vertical-align:middle }}
        .content{{ text-align:center; display:inline-block }}
        .message{{ font-size:80px; margin-bottom:40px }}
        .submessage{{ font-size:40px; margin-bottom:40px }}
        .copyright{{ font-size:20px; }}
        a{{ text-decoration:none; color:#3498db }}
    </style>
</head>
<body>
    <div class="container">
        <div class="content">
            <div class="message">LinkerX CDN</div>
            <div class="submessage">All Systems Operational since <span id="uptime">0s</span></div>
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
            if (hours > 0 || days > 0) timeStr += hours + 'h ';
            if (minutes > 0 || hours > 0 || days > 0) timeStr += minutes + 'm ';
            timeStr += seconds + 's';
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
    """Generate download link for a file from channel_id/message_id - No auth, no expiry"""
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
        
        # Build permanent download URL with new format
        fqdn = Var.FQDN
        safe_filename = urllib.parse.quote(file_name or 'file', safe='')
        download_url = f"https://{fqdn}/dl/{unique_file_id}/{telegram_file_id}/{file_size}/{safe_filename}"
        
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

@routes.get("/dl/{unique_file_id}/{file_id}/{size}/{filename}", allow_head=True)
async def direct_download(request: web.Request):
    """Stream file directly using file_id - metadata from URL path"""
    try:
        unique_file_id = request.match_info['unique_file_id']
        file_id = request.match_info['file_id']
        size_str = request.match_info['size']
        filename_encoded = request.match_info['filename']
        
        # Decode filename from URL encoding
        file_name = urllib.parse.unquote(filename_encoded)
        file_size = int(size_str) if size_str.isdigit() else 0
        
        logging.debug(f"Download request: {unique_file_id} - {file_name}")
        
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
        
        # Use metadata from URL path
        setattr(file_id_obj, "file_size", file_size)
        setattr(file_id_obj, "file_name", file_name)
        
        # Guess mime type from filename
        mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        setattr(file_id_obj, "mime_type", mime_type)
        
        logging.debug(f"Using URL metadata: {file_name} ({file_size} bytes)")
        
        # If file_size is 0, we need to get it from Telegram
        if file_size == 0:
            try:
                message = await faster_client.get_messages(file_id_obj.chat_id, file_id_obj.message_id)
                media = message.video or message.audio or message.document
                if media:
                    file_size = media.file_size
                    setattr(file_id_obj, "file_size", file_size)
                    if hasattr(media, 'file_name') and media.file_name:
                        setattr(file_id_obj, "file_name", media.file_name)
                        file_name = media.file_name
                    if hasattr(media, 'mime_type') and media.mime_type:
                        setattr(file_id_obj, "mime_type", media.mime_type)
                        mime_type = media.mime_type
            except Exception as tg_error:
                logging.warning(f"Failed to get file info from Telegram: {tg_error}")
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
        
        disposition = "attachment"
        
        # Sanitize header values to prevent HTTP header injection
        mime_type = sanitize_header_value(mime_type) if mime_type else "application/octet-stream"
        file_name = sanitize_header_value(file_name) if file_name else "file"
        
        if "video/" in mime_type or "audio/" in mime_type or "/html" in mime_type:
            disposition = "inline"
        
        logging.debug(f"Streaming: {file_name}")
        
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
