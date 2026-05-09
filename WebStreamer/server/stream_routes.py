# Simplified streaming routes - no database, no auth, no R2
import re
import time
import math
import hmac
import hashlib
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
LINK_TTL = 3600  # seconds


def make_link_sig(unique_file_id: str, timestamp: int) -> str:
    """HMAC-SHA256 over '{unique_file_id}:{timestamp}' — truncated to 16 hex chars."""
    from WebStreamer.vars import Var
    msg = f"{unique_file_id}:{timestamp}".encode()
    return hmac.new(Var.DOWNLOAD_SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()[:16]


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
        
        fqdn = Var.FQDN
        safe_filename = urllib.parse.quote(file_name or 'file', safe='')
        link_ts = int(time.time())
        sig = make_link_sig(unique_file_id, link_ts)
        download_url = f"https://{fqdn}/dl/{unique_file_id}/{telegram_file_id}/{file_size}/{safe_filename}?t={link_ts}&s={sig}"
        
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

def get_error_page(error_title, error_message, extra_detail=None):
    """Generate styled error page matching the home page design"""
    extra_html = f'<div class="extra-detail">{extra_detail}</div>' if extra_detail else ''
    html_content = f'''<html>
<head>
    <title>{error_title} - LinkerX CDN</title>
    <style>
        body{{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato }}
        .container{{ text-align:center; display:table-cell; vertical-align:middle }}
        .content{{ text-align:center; display:inline-block }}
        .message{{ font-size:80px; margin-bottom:40px }}
        .submessage{{ font-size:40px; margin-bottom:40px; color:#e74c3c }}
        .error-detail{{ font-size:20px; margin-bottom:15px; color:#95a5a6 }}
        .extra-detail{{ font-size:16px; margin-bottom:30px; color:#7f8c8d }}
        .copyright{{ font-size:20px; }}
        a{{ text-decoration:none; color:#3498db }}
    </style>
</head>
<body>
    <div class="container">
        <div class="content">
            <div class="message">LinkerX CDN</div>
            <div class="submessage">{error_message}</div>
            <div class="error-detail">{error_title}</div>
            {extra_html}
            <div class="copyright">Hash Hackers and LiquidX Projects</div>
        </div>
    </div>
</body>
</html>'''
    return html_content

async def safe_yield_file(generator):
    """
    Wrapper for yield_file that catches exceptions during streaming.
    If an error occurs during streaming, we can't send an HTML error page
    because headers were already sent, but we can at least log it and stop gracefully.
    """
    try:
        async for chunk in generator:
            yield chunk
    except Exception as e:
        error_str = str(e)
        logging.error(f"Error during file streaming: {error_str}", exc_info=True)
        
        # Log the specific error type for monitoring
        if "FILE_REFERENCE" in error_str and "EXPIRED" in error_str:
            logging.error("FILE_REFERENCE_EXPIRED during streaming - connection already established")
        elif "FLOOD_WAIT" in error_str:
            logging.error("FLOOD_WAIT during streaming - rate limited")
        
        # Can't send error page here as headers already sent
        # Connection will be closed and client will see incomplete download
        raise

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

        # Enforce 1-hour expiry with HMAC signature to prevent timestamp tampering.
        _expired_page = get_error_page(
            "Link Expired",
            "This link has expired",
            extra_detail="Download links are valid for 1 hour. Please request a new link."
        )
        t_param = request.rel_url.query.get('t')
        s_param = request.rel_url.query.get('s')
        if not t_param or not s_param:
            return web.Response(text=_expired_page, content_type="text/html", status=410)
        try:
            link_time = int(t_param)
            if time.time() - link_time > LINK_TTL:
                return web.Response(text=_expired_page, content_type="text/html", status=410)
            expected_sig = make_link_sig(unique_file_id, link_time)
            if not hmac.compare_digest(s_param, expected_sig):
                return web.Response(text=_expired_page, content_type="text/html", status=410)
        except (ValueError, TypeError):
            return web.Response(text=_expired_page, content_type="text/html", status=410)

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
                error_str = str(tg_error)
                logging.warning(f"Failed to get file info from Telegram: {error_str}")
                
                # Check for specific Telegram errors
                if "FILE_REFERENCE" in error_str and "EXPIRED" in error_str:
                    error_page = get_error_page("File Reference Expired", "Link Expired")
                    return web.Response(text=error_page, content_type="text/html", status=410)
                elif "FLOOD_WAIT" in error_str:
                    error_page = get_error_page("Rate Limit Exceeded", "Too Many Requests")
                    return web.Response(text=error_page, content_type="text/html", status=429)
                elif "FILE_ID_INVALID" in error_str or "FILE_REFERENCE_INVALID" in error_str:
                    error_page = get_error_page("Invalid File Reference", "Link Expired")
                    return web.Response(text=error_page, content_type="text/html", status=410)
                
                # For other errors, use default size
                file_size = 1024 * 1024 * 1024  # 1GB default
                setattr(file_id_obj, "file_size", file_size)
        
        # Handle range requests
        range_header = request.headers.get("Range")
        if range_header:
            try:
                parts = range_header.replace("bytes=", "").split("-", 1)
                from_bytes = int(parts[0]) if parts[0] else 0
                until_bytes = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
            except (ValueError, IndexError):
                error_page = get_error_page("Range Not Satisfiable", "Invalid Request Range")
                return web.Response(
                    text=error_page, content_type="text/html", status=416,
                    headers={"Content-Range": f"bytes */{file_size}"},
                )
        else:
            from_bytes = 0
            until_bytes = file_size - 1
        
        if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
            error_page = get_error_page("Range Not Satisfiable", "Invalid Request Range")
            return web.Response(
                text=error_page,
                content_type="text/html",
                status=416,
                headers={"Content-Range": f"bytes */{file_size}"},
            )
        
        chunk_size = 1024 * 1024
        until_bytes = min(until_bytes, file_size - 1)
        
        offset = from_bytes - (from_bytes % chunk_size)
        first_part_cut = from_bytes - offset
        last_part_cut = until_bytes % chunk_size + 1
        
        req_length = until_bytes - from_bytes + 1
        part_count = math.ceil((until_bytes + 1) / chunk_size) - math.floor(offset / chunk_size)
        
        # Skip pre-validation - file info (fileId, name, size) is already in URL path
        # Validation will happen during actual streaming, errors are handled in safe_yield_file
        logging.debug(f"Starting stream for file: {file_name} (size: {file_size})")
        
        # Get the file generator
        file_generator = tg_connect.yield_file(
            file_id_obj, index, offset, first_part_cut, last_part_cut, part_count, chunk_size
        )
        
        # Wrap it with error handling
        body = safe_yield_file(file_generator)
        
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
        error_str = str(e)
        logging.error(f"Error in direct_download: {error_str}", exc_info=True)
        
        # Handle specific Telegram errors with styled pages
        try:
            # Check for pyrogram errors
            if hasattr(e, '__class__') and hasattr(e.__class__, '__name__'):
                error_class = e.__class__.__name__
                
                if "FileReferenceExpired" in error_class or "FILE_REFERENCE" in error_str:
                    error_page = get_error_page("File Reference Expired", "Link Expired")
                    return web.Response(text=error_page, content_type="text/html", status=410)
                elif "FloodWait" in error_class or "FLOOD_WAIT" in error_str:
                    error_page = get_error_page("Rate Limit Exceeded", "Too Many Requests")
                    return web.Response(text=error_page, content_type="text/html", status=429)
                elif "FileIdInvalid" in error_class or "FILE_ID_INVALID" in error_str:
                    error_page = get_error_page("Invalid File ID", "Link Expired")
                    return web.Response(text=error_page, content_type="text/html", status=410)
                elif "ChannelPrivate" in error_class or "CHANNEL_PRIVATE" in error_str:
                    error_page = get_error_page("Access Denied", "File Not Available")
                    return web.Response(text=error_page, content_type="text/html", status=403)
                elif "MessageIdInvalid" in error_class or "MESSAGE_ID_INVALID" in error_str:
                    error_page = get_error_page("Message Not Found", "Link Expired")
                    return web.Response(text=error_page, content_type="text/html", status=410)
        except Exception:
            pass
        
        # Generic error page for other exceptions
        error_page = get_error_page("Service Error", "Failed to Stream File")
        return web.Response(text=error_page, content_type="text/html", status=500)

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
