# Taken from megadlbot_oss <https://github.com/eyaadh/megadlbot_oss/blob/master/mega/webserver/routes.py>
# Thanks to Eyaadh <https://github.com/eyaadh>

import re
import time
import math
import logging
import secrets
import mimetypes
import time
import json
from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine
from WebStreamer import bot_loop
from functools import partial
from WebStreamer.bot import multi_clients, work_loads
from WebStreamer.server.exceptions import FIleNotFound, InvalidHash
from WebStreamer import Var, utils, StartTime, __version__, StreamBot
from concurrent.futures import ThreadPoolExecutor
import urllib.parse
from WebStreamer.database import get_database
from collections import OrderedDict

# Optimized for Heroku 1GB dyno
# 50 workers can handle 50 concurrent streaming requests
# Previous value of 1000 was consuming 500-800MB of memory!
THREADPOOL = ThreadPoolExecutor(max_workers=50)

# LRU Cache for ByteStreamer objects with size limit
class LRUCache(OrderedDict):
    """Least Recently Used cache with maximum size limit"""
    def __init__(self, max_size=15):
        super().__init__()
        self.max_size = max_size
    
    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.max_size:
            oldest = next(iter(self))
            del self[oldest]
            logging.debug(f"LRU cache evicted oldest entry, cache size: {len(self)}")

async def sync_to_async(func, *args, wait=True, **kwargs):
    pfunc = partial(func, *args, **kwargs)
    future = bot_loop.run_in_executor(THREADPOOL, pfunc)
    return await future if wait else future

routes = web.RouteTableDef()
@routes.get("/", allow_head=True)
async def root_route_handler(_):
    return web.Response(
            text='<html> <head> <title>LinkerX CDN</title> <style> body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato } .container{ text-align:center; display:table-cell; vertical-align:middle } .content{ text-align:center; display:inline-block } .message{ font-size:80px; margin-bottom:40px } .submessage{ font-size:40px; margin-bottom:40px } .copyright{ font-size:20px; } a{ text-decoration:none; color:#3498db } </style> </head> <body> <div class="container"> <div class="content"> <div class="message">LinkerX CDN</div> <div class="submessage">All Systems Operational since '+utils.get_readable_time(time.time() - StartTime)+'</div> <div class="copyright">Hash Hackers and LiquidX Projects</div> </div> </div> </body> </html>', content_type="text/html"
    )

@routes.get("/favicon.ico", allow_head=True)
async def favicon_handler(_):
    """Serve favicon"""
    # Simple SVG favicon as base64 encoded ICO
    favicon_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect fill="#667eea" width="100" height="100" rx="15"/>
        <path fill="#fff" d="M30 25h40v10H30zm0 20h40v10H30zm0 20h30v10H30z"/>
        <circle fill="#764ba2" cx="75" cy="70" r="8"/>
    </svg>'''
    return web.Response(body=favicon_svg, content_type="image/svg+xml")

# route to check file name and size
@routes.get("/info/{path:.*}", allow_head=True)
async def info_route_handler(request: web.Request):
    try:
        # eg. path is /info/channelid/messageid
        parts = request.match_info['path'].split("/")
        if len(parts) != 2:
            raise web.HTTPBadRequest(
            text='<html> <head> <title>LinkerX CDN</title> <style> body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato } .container{ text-align:center; display:table-cell; vertical-align:middle } .content{ text-align:center; display:inline-block } .message{ font-size:80px; margin-bottom:40px } .submessage{ font-size:40px; margin-bottom:40px } .copyright{ font-size:20px; } a{ text-decoration:none; color:#3498db } </style> </head> <body> <div class="container"> <div class="content"> <div class="message">LinkerX CDN</div> <div class="submessage">Invalid Link</div> <div class="copyright">Hash Hackers and LiquidX Projects</div> </div> </div> </body> </html>', content_type="text/html"
        )

        cid, fid = parts
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
        logging.debug("before calling get_file_properties")
        file_id = await tg_connect.get_file_properties(int(fid), int(cid))
        dc_id = file_id.dc_id
        file_name = file_id.file_name
        file_size = file_id.file_size
        #file_details = file_name + " " + str(await formatFileSize(file_size)) + " on DC " + str(dc_id)
        return web.Response(
            text="{\"file_name\":\"" + file_name + "\", \"file_size\":\"" + str(await formatFileSize(file_size)) + "\", \"dc_id\":" + str(dc_id) + "}", content_type="application/json"
        )
    except FileNotFoundError as e:
        raise web.HTTPNotFound(
            text='<html> <head> <title>LinkerX CDN</title> <style> body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato } .container{ text-align:center; display:table-cell; vertical-align:middle } .content{ text-align:center; display:inline-block } .message{ font-size:80px; margin-bottom:40px } .submessage{ font-size:40px; margin-bottom:40px } .copyright{ font-size:20px; } a{ text-decoration:none; color:#3498db } </style> </head> <body> <div class="container"> <div class="content"> <div class="message">LinkerX CDN</div> <div class="submessage">File Not Found - '+e.message+'</div> <div class="copyright">Hash Hackers and LiquidX Projects</div> </div> </div> </body> </html>', content_type="text/html"
        )
    except Exception as e:
        error_message = str(e)
        logging.critical(error_message)
        raise web.HTTPInternalServerError(
            text='<html> <head> <title>LinkerX CDN</title> <style> body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato } .container{ text-align:center; display:table-cell; vertical-align:middle } .content{ text-align:center; display:inline-block } .message{ font-size:80px; margin-bottom:40px } .submessage{ font-size:40px; margin-bottom:40px } .copyright{ font-size:20px; } a{ text-decoration:none; color:#3498db } </style> </head> <body> <div class="container"> <div class="content"> <div class="message">LinkerX CDN</div> <div class="submessage">'+error_message+'</div> <div class="copyright">Hash Hackers and LiquidX Projects</div> </div> </div> </body> </html>', content_type="text/html"
        )


# Public API to generate download link from channel/message
@routes.get("/link/{path:.*}", allow_head=True)
async def link_route_handler(request: web.Request):
    """Generate download link for a file from channel_id/message_id - Public API, no auth required"""
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
        unique_file_id = file_id.unique_id  # Note: it's unique_id, not file_unique_id
        dc_id = file_id.dc_id
        file_name = file_id.file_name
        file_size = file_id.file_size
        mime_type = file_id.mime_type
        telegram_file_id = file_id.file_id
        
        # Store in database
        db = get_database()
        if db:
            try:
                db.store_file(
                    unique_file_id=unique_file_id,
                    bot_index=index,
                    file_id=telegram_file_id,
                    file_name=file_name,
                    file_size=file_size,
                    mime_type=mime_type,
                    dc_id=dc_id,
                    channel_id=int(channel_id)
                )
                logging.info(f"Stored file {unique_file_id} from channel {channel_id}")
            except Exception as store_error:
                logging.warning(f"Failed to store file in database: {store_error}")
        
        # Generate time-limited download link (3 hours)
        from WebStreamer.auth import generate_download_signature
        
        expires_at = int(time.time()) + (3 * 60 * 60)  # 3 hours from now
        signature = generate_download_signature(unique_file_id, expires_at, Var.DOWNLOAD_SECRET_KEY)
        
        # Build download URL
        fqdn = Var.FQDN
        download_url = f"https://{fqdn}/download/{unique_file_id}/{expires_at}/{signature}"
        
        return web.json_response({
            'success': True,
            'download_url': download_url,
            'file_info': {
                'unique_file_id': unique_file_id,
                'file_name': file_name,
                'file_size': file_size,
                'file_size_formatted': str(await formatFileSize(file_size)),
                'mime_type': mime_type,
                'dc_id': dc_id
            },
            'expires_at': expires_at,
            'expires_in_seconds': 3 * 60 * 60
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


async def get_authenticated_user(request: web.Request):
    """Helper to get authenticated user from session"""
    session_token = request.cookies.get('session_token')
    
    if not session_token:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header[7:]
    
    if not session_token:
        return None
    
    db = get_database()
    if not db.auth:
        return None
    
    telegram_user_id = db.auth.validate_session(session_token)
    if not telegram_user_id:
        return None
    
    return db.auth.get_user(telegram_user_id)

@routes.get("/files/{unique_file_id}", allow_head=True)
async def file_detail_page(request: web.Request):
    """Display file details page with download button (requires auth)"""
    try:
        unique_file_id = request.match_info['unique_file_id']
        
        # Check authentication
        user = await get_authenticated_user(request)
        
        if not user:
            # Show login page
            return web.Response(text=get_login_page_html(), content_type="text/html")
        
        # Get file info
        db = get_database()
        file_data = db.get_file_ids(unique_file_id)
        
        if not file_data:
            raise web.HTTPNotFound(text="File not found")
        
        # Get rate limit info
        rate_limits = {}
        if db.rate_limiter:
            rate_limits = db.rate_limiter.get_limits(user['telegram_user_id'])
        
        # Generate file page HTML
        html = get_file_detail_html(unique_file_id, file_data, user, rate_limits)
        return web.Response(text=html, content_type="text/html")
        
    except web.HTTPNotFound:
        raise
    except Exception as e:
        logging.error(f"Error in file_detail_page: {e}", exc_info=True)
        return web.Response(
            text='<html><body><h1>Error</h1><p>Failed to load file details</p></body></html>',
            content_type="text/html"
        )

def generate_pagination_html(current_page, total_pages, search_query=""):
    """Generate pagination HTML with page numbers and last page link"""
    if total_pages <= 1:
        return ""
    
    search_param = f"&search={search_query}" if search_query else ""
    pagination_html = '<div class="pagination">'
    
    # Previous button
    if current_page > 1:
        pagination_html += f'<a href="/files?page={current_page - 1}{search_param}" class="page-btn">← Prev</a>'
    else:
        pagination_html += '<span class="page-btn disabled">← Prev</span>'
    
    # Page numbers logic
    max_visible_pages = 5
    
    if total_pages <= max_visible_pages:
        # Show all pages
        for page_num in range(1, total_pages + 1):
            if page_num == current_page:
                pagination_html += f'<span class="page-btn active">{page_num}</span>'
            else:
                pagination_html += f'<a href="/files?page={page_num}{search_param}" class="page-btn">{page_num}</a>'
    else:
        # Smart pagination
        # Always show first page
        if current_page == 1:
            pagination_html += f'<span class="page-btn active">1</span>'
        else:
            pagination_html += f'<a href="/files?page=1{search_param}" class="page-btn">1</a>'
        
        # Calculate range around current page
        start_page = max(2, current_page - 1)
        end_page = min(total_pages - 1, current_page + 1)
        
        # Show ellipsis if needed
        if start_page > 2:
            pagination_html += '<span class="page-ellipsis">...</span>'
        
        # Show pages around current
        for page_num in range(start_page, end_page + 1):
            if page_num == current_page:
                pagination_html += f'<span class="page-btn active">{page_num}</span>'
            else:
                pagination_html += f'<a href="/files?page={page_num}{search_param}" class="page-btn">{page_num}</a>'
        
        # Show ellipsis if needed
        if end_page < total_pages - 1:
            pagination_html += '<span class="page-ellipsis">...</span>'
        
        # Always show last page
        if current_page == total_pages:
            pagination_html += f'<span class="page-btn active">{total_pages}</span>'
        else:
            pagination_html += f'<a href="/files?page={total_pages}{search_param}" class="page-btn">{total_pages}</a>'
    
    # Next button
    if current_page < total_pages:
        pagination_html += f'<a href="/files?page={current_page + 1}{search_param}" class="page-btn">Next →</a>'
    else:
        pagination_html += '<span class="page-btn disabled">Next →</span>'
    
    pagination_html += '</div>'
    return pagination_html

@routes.get("/files", allow_head=True)
async def files_list_handler(request: web.Request):
    """Display all files from database with search functionality (requires auth)"""
    try:
        # Check authentication
        user = await get_authenticated_user(request)
        
        if not user:
            # Show login page
            return web.Response(text=get_login_page_html(), content_type="text/html")
        
        # Get search query and page parameters
        search_query = request.query.get('search', '').strip()
        try:
            page = int(request.query.get('page', '1'))
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1
        
        # Get database instance
        db = get_database()
        
        # Get rate limit info
        rate_limits = {}
        if db.rate_limiter:
            rate_limits = db.rate_limiter.get_limits(user['telegram_user_id'])
        
        # Pagination settings
        items_per_page = 20
        offset = (page - 1) * items_per_page
        
        # Get files from database with pagination
        files = db.get_all_files(search_query=search_query if search_query else None, limit=items_per_page, offset=offset)
        total_count = db.get_file_count(search_query=search_query if search_query else None)
        
        # Calculate total pages
        import math
        total_pages = math.ceil(total_count / items_per_page) if total_count > 0 else 1
        
        # Build HTML table rows
        rows_html = ""
        if files:
            for file in files:
                file_name = file['file_name'] or 'Unknown'
                file_size = await formatFileSize(file['file_size']) if file['file_size'] else '0B'
                mime_type = file['mime_type'] or 'Unknown'
                unique_id = file['unique_file_id']
                
                rows_html += f"""
                <tr>
                    <td style="padding: 12px; border-bottom: 1px solid #ecf0f1;">{file_name}</td>
                    <td style="padding: 12px; border-bottom: 1px solid #ecf0f1; text-align: right;">{file_size}</td>
                    <td style="padding: 12px; border-bottom: 1px solid #ecf0f1;">{mime_type}</td>
                    <td style="padding: 12px; border-bottom: 1px solid #ecf0f1; text-align: center;">
                        <a href="/download/{unique_id}" style="background-color: #3498db; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; font-size: 14px;">Download</a>
                    </td>
                </tr>
                """
        else:
            rows_html = """
            <tr>
                <td colspan="4" style="padding: 40px; text-align: center; color: #95a5a6; font-size: 18px;">
                    No files found
                </td>
            </tr>
            """
        
        # Prepare user and rate limit info
        first_name = user.get('first_name') or ''
        last_name = user.get('last_name') or ''
        user_id = user.get('telegram_user_id', '')
        
        # Build display name
        if first_name or last_name:
            user_name = f"{first_name} {last_name}".strip()
        else:
            user_name = "User"
        
        # Add user ID in parentheses
        user_name = f"{user_name} ({user_id})"
        
        rate_hour_used = rate_limits.get('hour_used', 0) if rate_limits else 0
        rate_hour_limit = rate_limits.get('hour_limit', 10) if rate_limits else 10
        rate_day_used = rate_limits.get('day_used', 0) if rate_limits else 0
        rate_day_limit = rate_limits.get('day_limit', 50) if rate_limits else 50
        
        # Build complete HTML page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>LinkerX CDN - Files</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    font-family: 'Lato', Arial, sans-serif;
                    background-color: #f5f6fa;
                    color: #2c3e50;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 36px;
                    font-weight: 300;
                }}
                .header p {{
                    margin: 10px 0 0 0;
                    font-size: 16px;
                    opacity: 0.9;
                }}
                .container {{
                    max-width: 1400px;
                    margin: 30px auto;
                    padding: 0 20px;
                }}
                .user-info-box {{
                    background: white;
                    padding: 20px 25px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                    margin-bottom: 25px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    flex-wrap: wrap;
                    gap: 15px;
                }}
                .user-details {{
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}
                .user-name {{
                    font-size: 18px;
                    font-weight: 600;
                    color: #2c3e50;
                }}
                .limits-info {{
                    display: flex;
                    gap: 20px;
                    flex-wrap: wrap;
                }}
                .limit-item {{
                    display: flex;
                    flex-direction: column;
                    gap: 5px;
                }}
                .limit-label {{
                    font-size: 12px;
                    color: #7f8c8d;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                .limit-value {{
                    font-size: 16px;
                    font-weight: 600;
                    color: #667eea;
                }}
                .limit-bar {{
                    width: 150px;
                    height: 6px;
                    background: #ecf0f1;
                    border-radius: 3px;
                    overflow: hidden;
                }}
                .limit-bar-fill {{
                    height: 100%;
                    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                    transition: width 0.3s;
                }}
                .logout-btn {{
                    padding: 10px 20px;
                    background: #e74c3c;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: background 0.3s;
                }}
                .logout-btn:hover {{
                    background: #c0392b;
                }}
                .search-box {{
                    background: white;
                    padding: 25px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                    margin-bottom: 25px;
                }}
                .search-box form {{
                    display: flex;
                    gap: 10px;
                }}
                .search-box input[type="text"] {{
                    flex: 1;
                    padding: 12px 15px;
                    border: 2px solid #e0e0e0;
                    border-radius: 6px;
                    font-size: 16px;
                    transition: border-color 0.3s;
                }}
                .search-box input[type="text"]:focus {{
                    outline: none;
                    border-color: #3498db;
                }}
                .search-box button {{
                    padding: 12px 30px;
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 16px;
                    cursor: pointer;
                    transition: background-color 0.3s;
                }}
                .search-box button:hover {{
                    background-color: #2980b9;
                }}
                .clear-search {{
                    padding: 12px 20px;
                    background-color: #95a5a6;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 16px;
                    cursor: pointer;
                    transition: background-color 0.3s;
                    text-decoration: none;
                    display: inline-block;
                }}
                .clear-search:hover {{
                    background-color: #7f8c8d;
                }}
                .stats {{
                    background: white;
                    padding: 15px 25px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                    margin-bottom: 25px;
                    text-align: center;
                    font-size: 16px;
                    color: #7f8c8d;
                }}
                .table-container {{
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                    overflow: hidden;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                thead {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }}
                th {{
                    padding: 15px 12px;
                    text-align: left;
                    font-weight: 500;
                    font-size: 14px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                th:nth-child(3), th:nth-child(5) {{
                    text-align: center;
                }}
                tbody tr:hover {{
                    background-color: #f8f9fa;
                }}
                a {{
                    transition: opacity 0.3s;
                }}
                a:hover {{
                    opacity: 0.8;
                }}
                .footer {{
                    text-align: center;
                    padding: 30px 20px;
                    color: #95a5a6;
                    font-size: 14px;
                }}
                .pagination {{
                    background: white;
                    padding: 20px 25px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                    margin-top: 25px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    gap: 8px;
                    flex-wrap: wrap;
                }}
                .page-btn {{
                    padding: 8px 14px;
                    background: white;
                    color: #667eea;
                    border: 2px solid #667eea;
                    border-radius: 6px;
                    text-decoration: none;
                    font-size: 14px;
                    font-weight: 600;
                    transition: all 0.3s;
                    min-width: 40px;
                    text-align: center;
                }}
                .page-btn:hover {{
                    background: #667eea;
                    color: white;
                }}
                .page-btn.active {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-color: #667eea;
                }}
                .page-btn.disabled {{
                    opacity: 0.4;
                    cursor: not-allowed;
                    pointer-events: none;
                }}
                .page-ellipsis {{
                    padding: 8px 14px;
                    color: #7f8c8d;
                    font-weight: 600;
                }}
                @media (max-width: 768px) {{
                    .header h1 {{
                        font-size: 28px;
                    }}
                    .search-box form {{
                        flex-direction: column;
                    }}
                    .table-container {{
                        overflow-x: auto;
                    }}
                    table {{
                        min-width: 800px;
                    }}
                    .user-info-box {{
                        flex-direction: column;
                        align-items: flex-start;
                    }}
                    .limits-info {{
                        width: 100%;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>LinkerX CDN</h1>
                <p>File Browser & Download Center</p>
            </div>
            
            <div class="container">
                <!-- User Info & Limits -->
                <div class="user-info-box">
                    <div class="user-details">
                        <span style="font-size: 24px;">👤</span>
                        <span class="user-name">{user_name}</span>
                    </div>
                    <div class="limits-info">
                        <div class="limit-item">
                            <div class="limit-label">Hourly Downloads</div>
                            <div class="limit-value">{rate_hour_used}/{rate_hour_limit}</div>
                            <div class="limit-bar">
                                <div class="limit-bar-fill" style="width: {min(100, (rate_hour_used/rate_hour_limit)*100) if rate_hour_limit > 0 else 0}%;"></div>
                            </div>
                        </div>
                        <div class="limit-item">
                            <div class="limit-label">Daily Downloads</div>
                            <div class="limit-value">{rate_day_used}/{rate_day_limit}</div>
                            <div class="limit-bar">
                                <div class="limit-bar-fill" style="width: {min(100, (rate_day_used/rate_day_limit)*100) if rate_day_limit > 0 else 0}%;"></div>
                            </div>
                        </div>
                    </div>
                    <button class="logout-btn" onclick="handleLogout()">🚪 Logout</button>
                </div>
                
                <div class="search-box">
                    <form method="get" action="/files">
                        <input type="text" name="search" placeholder="Search files by name..." value="{search_query}" autofocus>
                        <button type="submit">Search</button>
                        {f'<a href="/files" class="clear-search">Clear</a>' if search_query else ''}
                    </form>
                </div>
                
                <div class="stats">
                    {f'Found <strong>{total_count}</strong> file(s) - Page {page} of {total_pages}' if search_query else f'Total: <strong>{total_count}</strong> file(s) - Page {page} of {total_pages}'}
                </div>
                
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>File Name</th>
                                <th style="text-align: right;">Size</th>
                                <th>MIME Type</th>
                                <th style="text-align: center;">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                </div>
                
                <!-- Pagination -->
                {generate_pagination_html(page, total_pages, search_query)}
            </div>
            
            <div class="footer">
                Hash Hackers and LiquidX Projects
            </div>
            
            <script>
                async function handleLogout() {{
                    if (!confirm('Are you sure you want to logout?')) {{
                        return;
                    }}
                    
                    try {{
                        const response = await fetch('/api/auth/logout', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json'
                            }}
                        }});
                        
                        const data = await response.json();
                        
                        if (data.success) {{
                            // Redirect to files page (will show login)
                            window.location.href = '/files';
                        }} else {{
                            alert('Logout failed: ' + (data.message || 'Unknown error'));
                        }}
                    }} catch (error) {{
                        console.error('Logout error:', error);
                        alert('Logout failed. Please try again.');
                    }}
                }}
            </script>
        </body>
        </html>
        """
        
        return web.Response(text=html_content, content_type="text/html")
        
    except Exception as e:
        logging.error(f"Error in files_list_handler: {e}", exc_info=True)
        return web.Response(
            text=f'<html> <head> <title>LinkerX CDN</title> <style> body{{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato }} .container{{ text-align:center; display:table-cell; vertical-align:middle }} .content{{ text-align:center; display:inline-block }} .message{{ font-size:80px; margin-bottom:40px }} .submessage{{ font-size:40px; margin-bottom:40px }} .copyright{{ font-size:20px; }} a{{ text-decoration:none; color:#3498db }} </style> </head> <body> <div class="container"> <div class="content"> <div class="message">LinkerX CDN</div> <div class="submessage">Error loading files</div> <div class="copyright">Hash Hackers and LiquidX Projects</div> </div> </div> </body> </html>',
            content_type="text/html"
        )

@routes.post("/api/generate-download-link")
async def generate_download_link(request: web.Request):
    """Generate time-limited download link with integrity check"""
    try:
        data = await request.json()
        unique_file_id = data.get('unique_file_id')
        
        if not unique_file_id:
            return web.json_response({
                'success': False,
                'message': 'unique_file_id is required'
            }, status=400)
        
        # Check authentication
        user = await get_authenticated_user(request)
        if not user:
            return web.json_response({
                'success': False,
                'message': 'Authentication required'
            }, status=401)
        
        telegram_user_id = user['telegram_user_id']
        
        # Check rate limits
        db = get_database()
        if db.rate_limiter:
            allowed, message = db.rate_limiter.check_and_increment(telegram_user_id)
            if not allowed:
                return web.json_response({
                    'success': False,
                    'message': message
                }, status=429)
        
        # Check if file exists
        file_data = db.get_file_ids(unique_file_id)
        if not file_data:
            return web.json_response({
                'success': False,
                'message': 'File not found'
            }, status=404)
        
        # Generate time-limited link (3 hours)
        import time
        from WebStreamer.auth import generate_download_signature
        
        expires_at = int(time.time()) + (3 * 60 * 60)  # 3 hours from now
        signature = generate_download_signature(unique_file_id, expires_at, Var.DOWNLOAD_SECRET_KEY)
        
        # Build download URL
        fqdn = Var.FQDN
        download_url = f"https://{fqdn}/download/{unique_file_id}/{expires_at}/{signature}"
        
        return web.json_response({
            'success': True,
            'download_url': download_url,
            'expires_at': expires_at,
            'valid_for_hours': 3,
            'rate_limit_message': message if db.rate_limiter else None
        })
        
    except json.JSONDecodeError:
        return web.json_response({
            'success': False,
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logging.error(f"Error generating download link: {e}", exc_info=True)
        return web.json_response({
            'success': False,
            'message': 'Internal server error'
        }, status=500)

@routes.get("/download/{unique_file_id}/{expires_at}/{signature}", allow_head=True)
async def download_with_signature(request: web.Request):
    """Stream media file with time-limited signature"""
    try:
        unique_file_id = request.match_info['unique_file_id']
        expires_at = int(request.match_info['expires_at'])
        signature = request.match_info['signature']
        
        logging.info(f"Download request for unique_file_id: {unique_file_id}")
        
        # Check expiration
        import time
        if time.time() > expires_at:
            raise web.HTTPForbidden(
                text='<html><body><h1>Link Expired</h1><p>This download link has expired. Please generate a new one.</p></body></html>',
                content_type="text/html"
            )
        
        # Verify signature
        from WebStreamer.auth import verify_download_signature
        if not verify_download_signature(unique_file_id, expires_at, signature, Var.DOWNLOAD_SECRET_KEY):
            raise web.HTTPForbidden(
                text='<html><body><h1>Invalid Link</h1><p>Link integrity check failed.</p></body></html>',
                content_type="text/html"
            )
        
        # Get file information from database
        db = get_database()
        file_data = db.get_file_ids(unique_file_id)
        
        if not file_data or not file_data['bot_file_ids']:
            raise web.HTTPNotFound(
                text='<html><body><h1>File Not Found</h1><p>The requested file could not be found in the database.</p></body></html>', 
                content_type="text/html"
            )
        
        # Try to stream using available file_ids (same logic as before)
        last_error = None
        available_bots = list(file_data['bot_file_ids'].items())
        
        # Randomize the order
        import random
        random.shuffle(available_bots)
        
        for bot_index, file_id in available_bots:
            try:
                logging.info(f"Attempting to stream using bot {bot_index + 1}, file_id: {file_id}")
                
                # Get the client for this bot
                if bot_index not in multi_clients:
                    logging.warning(f"Bot {bot_index} not available in multi_clients")
                    continue
                
                client = multi_clients[bot_index]
                
                # Get ByteStreamer for this client
                if client in class_cache:
                    tg_connect = class_cache[client]
                else:
                    tg_connect = utils.ByteStreamer(client)
                    class_cache[client] = tg_connect
                
                # Get file properties using file_id
                from pyrogram.file_id import FileId
                file_id_obj = FileId.decode(file_id)
                
                # Set additional properties from database
                setattr(file_id_obj, "file_size", file_data['file_size'] or 0)
                setattr(file_id_obj, "mime_type", file_data['mime_type'] or "application/octet-stream")
                setattr(file_id_obj, "file_name", file_data['file_name'] or "file")
                
                file_size = file_id_obj.file_size
                
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
                    file_id_obj, bot_index, offset, first_part_cut, last_part_cut, part_count, chunk_size
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
                
                logging.info(f"Successfully streaming file using bot {bot_index + 1}")
                
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
                last_error = e
                logging.warning(f"Failed to stream using bot {bot_index + 1}: {e}")
                continue
        
        # If all bots failed, raise the last error
        error_msg = f"All available bots failed to stream the file. Last error: {last_error}"
        logging.error(error_msg)
        raise web.HTTPInternalServerError(
            text='<html><body><h1>Failed to Stream File</h1><p>Unable to stream the file from Telegram servers.</p></body></html>',
            content_type="text/html"
        )
        
    except web.HTTPNotFound:
        raise
    except web.HTTPForbidden:
        raise
    except web.HTTPInternalServerError:
        raise
    except Exception as e:
        logging.error(f"Error in download_with_signature: {e}", exc_info=True)
        raise web.HTTPInternalServerError(
            text='<html><body><h1>Internal Server Error</h1></body></html>',
            content_type="text/html"
        )

@routes.get("/download/{unique_file_id}", allow_head=True)
async def download_by_unique_id_redirect(request: web.Request):
    """Redirect old download links to file detail page"""
    try:
        unique_file_id = request.match_info['unique_file_id']
        logging.info(f"Old download link accessed for unique_file_id: {unique_file_id}, redirecting to file page")
        
        # Redirect to file detail page
        raise web.HTTPFound(f"/files/{unique_file_id}")
        
    except web.HTTPFound:
        raise
    except Exception as e:
        logging.error(f"Error in download redirect: {e}", exc_info=True)
        raise web.HTTPNotFound(
            text='<html><body><h1>File Not Found</h1></body></html>',
            content_type="text/html"
        )

# Keep old download endpoint for backwards compatibility but it will be deprecated
@routes.get("/download_old/{unique_file_id}", allow_head=True)
async def download_by_unique_id_old(request: web.Request):
    """Stream media file using unique_file_id from database (deprecated - for backwards compatibility)"""
    try:
        unique_file_id = request.match_info['unique_file_id']
        logging.info(f"Download request for unique_file_id: {unique_file_id}")
        
        # Get file information from database
        db = get_database()
        file_data = db.get_file_ids(unique_file_id)
        
        if not file_data or not file_data['bot_file_ids']:
            raise web.HTTPNotFound(
                text='<html><body><h1>File Not Found</h1></body></html>', 
                content_type="text/html"
            )
        
        # Try to stream using available file_ids
        last_error = None
        available_bots = list(file_data['bot_file_ids'].items())
        
        # Randomize the order
        import random
        random.shuffle(available_bots)
        
        for bot_index, file_id in available_bots:
            try:
                logging.info(f"Attempting to stream using bot {bot_index + 1}, file_id: {file_id}")
                
                # Get the client for this bot
                if bot_index not in multi_clients:
                    logging.warning(f"Bot {bot_index} not available in multi_clients")
                    continue
                
                client = multi_clients[bot_index]
                
                # Get ByteStreamer for this client
                if client in class_cache:
                    tg_connect = class_cache[client]
                else:
                    tg_connect = utils.ByteStreamer(client)
                    class_cache[client] = tg_connect
                
                # Get file properties using file_id
                from pyrogram.file_id import FileId
                file_id_obj = FileId.decode(file_id)
                
                # Set additional properties from database
                setattr(file_id_obj, "file_size", file_data['file_size'] or 0)
                setattr(file_id_obj, "mime_type", file_data['mime_type'] or "application/octet-stream")
                setattr(file_id_obj, "file_name", file_data['file_name'] or "file")
                
                file_size = file_id_obj.file_size
                
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
                    file_id_obj, bot_index, offset, first_part_cut, last_part_cut, part_count, chunk_size
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
                
                logging.info(f"Successfully streaming file using bot {bot_index + 1}")
                
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
                last_error = e
                logging.warning(f"Failed to stream using bot {bot_index + 1}: {e}")
                continue
        
        # If all bots failed, raise the last error
        error_msg = f"All available bots failed to stream the file. Last error: {last_error}"
        logging.error(error_msg)
        raise web.HTTPInternalServerError(
            text='<html> <head> <title>LinkerX CDN</title> <style> body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato } .container{ text-align:center; display:table-cell; vertical-align:middle } .content{ text-align:center; display:inline-block } .message{ font-size:80px; margin-bottom:40px } .submessage{ font-size:40px; margin-bottom:40px } .copyright{ font-size:20px; } a{ text-decoration:none; color:#3498db } </style> </head> <body> <div class="container"> <div class="content"> <div class="message">LinkerX CDN</div> <div class="submessage">Failed to Stream File</div> <div class="copyright">Hash Hackers and LiquidX Projects</div> </div> </div> </body> </html>',
            content_type="text/html"
        )
        
    except web.HTTPNotFound:
        raise
    except web.HTTPInternalServerError:
        raise
    except Exception as e:
        logging.error(f"Error in download_by_unique_id: {e}", exc_info=True)
        raise web.HTTPInternalServerError(
            text='<html> <head> <title>LinkerX CDN</title> <style> body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato } .container{ text-align:center; display:table-cell; vertical-align:middle } .content{ text-align:center; display:inline-block } .message{ font-size:80px; margin-bottom:40px } .submessage{ font-size:40px; margin-bottom:40px } .copyright{ font-size:20px; } a{ text-decoration:none; color:#3498db } </style> </head> <body> <div class="container"> <div class="content"> <div class="message">LinkerX CDN</div> <div class="submessage">Internal Server Error</div> <div class="copyright">Hash Hackers and LiquidX Projects</div> </div> </div> </body> </html>',
            content_type="text/html"
        )

@routes.get("/{path:.*}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        encrypted_code = urllib.parse.unquote(request.match_info['path'])
        logging.debug(f"Encrypted code Got: {encrypted_code}")

        parts = encrypted_code.split("/")
        if len(parts) != 4:
            raise web.HTTPBadRequest(
            text='<html> <head> <title>LinkerX CDN</title> <style> body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato } .container{ text-align:center; display:table-cell; vertical-align:middle } .content{ text-align:center; display:inline-block } .message{ font-size:80px; margin-bottom:40px } .submessage{ font-size:40px; margin-bottom:40px } .copyright{ font-size:20px; } a{ text-decoration:none; color:#3498db } </style> </head> <body> <div class="container"> <div class="content"> <div class="message">LinkerX CDN</div> <div class="submessage">Invalid Link</div> <div class="copyright">Hash Hackers and LiquidX Projects</div> </div> </div> </body> </html>', content_type="text/html"
        )

        cid, fid, expiration_time, sha256_key = parts
        current_time = int(time.time())
        if int(expiration_time) < current_time:
            raise web.HTTPForbidden(
            text='<html> <head> <title>LinkerX CDN</title> <style> body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato } .container{ text-align:center; display:table-cell; vertical-align:middle } .content{ text-align:center; display:inline-block } .message{ font-size:80px; margin-bottom:40px } .submessage{ font-size:40px; margin-bottom:40px } .copyright{ font-size:20px; } a{ text-decoration:none; color:#3498db } </style> </head> <body> <div class="container"> <div class="content"> <div class="message">LinkerX CDN</div> <div class="submessage">Link Expired</div> <div class="copyright">Hash Hackers and LiquidX Projects</div> </div> </div> </body> </html>', content_type="text/html"
        )

        sha256_verified = await sync_to_async(utils.verify_sha256_key, cid, fid, expiration_time, sha256_key)
        if not sha256_verified:
            raise web.HTTPForbidden(
            text='<html> <head> <title>LinkerX CDN</title> <style> body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato } .container{ text-align:center; display:table-cell; vertical-align:middle } .content{ text-align:center; display:inline-block } .message{ font-size:80px; margin-bottom:40px } .submessage{ font-size:40px; margin-bottom:40px } .copyright{ font-size:20px; } a{ text-decoration:none; color:#3498db } </style> </head> <body> <div class="container"> <div class="content"> <div class="message">LinkerX CDN</div> <div class="submessage">Hash Manipulation Detected</div> <div class="copyright">Hash Hackers and LiquidX Projects</div> </div> </div> </body> </html>', content_type="text/html"
        )

        return await media_streamer(request, int(fid), int(cid))
    except InvalidHash as e:
        raise web.HTTPForbidden(
            text='<html> <head> <title>LinkerX CDN</title> <style> body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato } .container{ text-align:center; display:table-cell; vertical-align:middle } .content{ text-align:center; display:inline-block } .message{ font-size:80px; margin-bottom:40px } .submessage{ font-size:40px; margin-bottom:40px } .copyright{ font-size:20px; } a{ text-decoration:none; color:#3498db } </style> </head> <body> <div class="container"> <div class="content"> <div class="message">LinkerX CDN</div> <div class="submessage">Invalid File Hash - '+e.message+'</div> <div class="copyright">Hash Hackers and LiquidX Projects</div> </div> </div> </body> </html>', content_type="text/html"
        )
    except FileNotFoundError as e:
        raise web.HTTPNotFound(
            text='<html> <head> <title>LinkerX CDN</title> <style> body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato } .container{ text-align:center; display:table-cell; vertical-align:middle } .content{ text-align:center; display:inline-block } .message{ font-size:80px; margin-bottom:40px } .submessage{ font-size:40px; margin-bottom:40px } .copyright{ font-size:20px; } a{ text-decoration:none; color:#3498db } </style> </head> <body> <div class="container"> <div class="content"> <div class="message">LinkerX CDN</div> <div class="submessage">File Not Found - '+e.message+'</div> <div class="copyright">Hash Hackers and LiquidX Projects</div> </div> </div> </body> </html>', content_type="text/html"
        )
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        error_message = str(e)
        logging.critical(error_message)
        raise web.HTTPInternalServerError(
            text='<html> <head> <title>LinkerX CDN</title> <style> body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato } .container{ text-align:center; display:table-cell; vertical-align:middle } .content{ text-align:center; display:inline-block } .message{ font-size:80px; margin-bottom:40px } .submessage{ font-size:40px; margin-bottom:40px } .copyright{ font-size:20px; } a{ text-decoration:none; color:#3498db } </style> </head> <body> <div class="container"> <div class="content"> <div class="message">LinkerX CDN</div> <div class="submessage">'+error_message+'</div> <div class="copyright">Hash Hackers and LiquidX Projects</div> </div> </div> </body> </html>', content_type="text/html"
        )

# if url doesn't match any route, return 404
@routes.get("/{tail:.*}")
async def not_found(_):
    # show special html page for 404
    return web.Response(
        text='<html> <head> <title>LinkerX CDN</title> <style> body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato } .container{ text-align:center; display:table-cell; vertical-align:middle } .content{ text-align:center; display:inline-block } .message{ font-size:80px; margin-bottom:40px } .submessage{ font-size:40px; margin-bottom:40px } .copyright{ font-size:20px; } a{ text-decoration:none; color:#3498db } </style> </head> <body> <div class="container"> <div class="content"> <div class="message">LinkerX CDN</div> <div class="submessage">Page Not Found</div> <div class="copyright">Hash Hackers and LiquidX Projects</div> </div> </div> </body> </html>', content_type="text/html"
    )

class_cache = {}

async def media_streamer(request: web.Request, message_id: int, channel_id):
    try:
        range_header = request.headers.get("Range", 0)
        
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
        logging.debug("before calling get_file_properties")
        file_id = await tg_connect.get_file_properties(message_id, channel_id)
        logging.debug("after calling get_file_properties")

        file_size = file_id.file_size

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
            file_id, index, offset, first_part_cut, last_part_cut, part_count, chunk_size
        )
        mime_type = file_id.mime_type
        file_name = file_id.file_name
        disposition = "attachment"

        if mime_type:
            if not file_name:
                try:
                    file_name = f"{secrets.token_hex(2)}.{mime_type.split('/')[1]}"
                except (IndexError, AttributeError):
                    file_name = f"{secrets.token_hex(2)}.unknown"
        else:
            if file_name:
                mime_type = mimetypes.guess_type(file_id.file_name)
            else:
                mime_type = "application/octet-stream"
                file_name = f"{secrets.token_hex(2)}.unknown"

        if "video/" in mime_type or "audio/" in mime_type or "/html" in mime_type:
            disposition = "inline"

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
        logging.error(f"Error in media streamer: {str(e)}")
        return web.Response(
            text='<html> <head> <title>LinkerX CDN</title> <style> body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato } .container{ text-align:center; display:table-cell; vertical-align:middle } .content{ text-align:center; display:inline-block } .message{ font-size:80px; margin-bottom:40px } .submessage{ font-size:40px; margin-bottom:40px } .copyright{ font-size:20px; } a{ text-decoration:none; color:#3498db } </style> </head> <body> <div class="container"> <div class="content"> <div class="message">LinkerX CDN</div> <div class="submessage">'+str(e)+'</div> <div class="copyright">Hash Hackers and LiquidX Projects</div> </div> </div> </body> </html>', content_type="text/html"
        )
    
async def formatFileSize(bytes):
    if bytes == 0:
        return "0B"
    k = 1024
    sizes = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    i = math.floor(math.log(bytes) / math.log(k))
    return f"{round(bytes / math.pow(k, i), 2)} {sizes[i]}"

def get_login_page_html():
    """Generate HTML for login page"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - LinkerX CDN</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .login-container {
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                max-width: 400px;
                width: 100%;
                padding: 40px 30px;
            }
            .logo {
                text-align: center;
                margin-bottom: 30px;
            }
            .logo h1 {
                color: #667eea;
                font-size: 32px;
                margin-bottom: 10px;
            }
            .logo p {
                color: #666;
                font-size: 14px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                color: #333;
                font-weight: 600;
                margin-bottom: 8px;
                font-size: 14px;
            }
            .form-group input {
                width: 100%;
                padding: 12px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
                transition: border-color 0.3s;
            }
            .form-group input:focus {
                outline: none;
                border-color: #667eea;
            }
            .btn {
                width: 100%;
                padding: 12px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }
            .btn:hover {
                transform: translateY(-2px);
            }
            .btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            .message {
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 20px;
                font-size: 14px;
            }
            .message.success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .message.error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            .message.info {
                background: #d1ecf1;
                color: #0c5460;
                border: 1px solid #bee5eb;
            }
            .step-indicator {
                text-align: center;
                margin-bottom: 25px;
            }
            .step {
                display: inline-block;
                width: 30px;
                height: 30px;
                line-height: 30px;
                border-radius: 50%;
                background: #e0e0e0;
                color: #666;
                font-weight: 600;
                margin: 0 5px;
            }
            .step.active {
                background: #667eea;
                color: white;
            }
            .help-text {
                text-align: center;
                color: #666;
                font-size: 13px;
                margin-top: 20px;
                line-height: 1.6;
            }
            .hidden {
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="logo">
                <h1>🔐 LinkerX CDN</h1>
                <p>Secure File Access</p>
            </div>

            <div class="step-indicator">
                <span class="step active" id="step1">1</span>
                <span class="step" id="step2">2</span>
            </div>

            <div id="message-container"></div>

            <!-- Step 1: Enter Telegram ID -->
            <div id="step-telegram-id">
                <div class="form-group">
                    <label for="telegram_user_id">Telegram User ID</label>
                    <input type="number" id="telegram_user_id" placeholder="Enter your Telegram User ID" required>
                </div>
                <button class="btn" onclick="requestOTP()">Request OTP</button>
                <div class="help-text">
                    Don't know your Telegram ID?<br>
                    Send /start to our bot to get your ID
                </div>
            </div>

            <!-- Step 2: Enter OTP -->
            <div id="step-otp" class="hidden">
                <div class="form-group">
                    <label for="otp">Enter OTP</label>
                    <input type="text" id="otp" placeholder="Enter 6-digit code" maxlength="6" pattern="[0-9]{6}" required>
                </div>
                <button class="btn" onclick="verifyOTP()">Verify & Login</button>
                <div class="help-text">
                    Check your Telegram for the OTP code<br>
                    <a href="#" onclick="backToStep1(); return false;" style="color: #667eea;">Request new code</a>
                </div>
            </div>
        </div>

        <script>
            let currentUserId = null;

            function showMessage(text, type = 'info') {
                const container = document.getElementById('message-container');
                container.innerHTML = `<div class="message ${type}">${text}</div>`;
                setTimeout(() => {
                    if (container.firstChild && container.firstChild.classList.contains(type)) {
                        container.innerHTML = '';
                    }
                }, 5000);
            }

            function requestOTP() {
                const userIdInput = document.getElementById('telegram_user_id');
                const userId = userIdInput.value.trim();

                if (!userId) {
                    showMessage('Please enter your Telegram User ID', 'error');
                    return;
                }

                currentUserId = userId;
                const btn = event.target;
                btn.disabled = true;
                btn.textContent = 'Sending...';

                fetch('/api/auth/request-otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ telegram_user_id: userId })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showMessage('OTP sent to your Telegram! Check your messages.', 'success');
                        document.getElementById('step-telegram-id').classList.add('hidden');
                        document.getElementById('step-otp').classList.remove('hidden');
                        document.getElementById('step1').classList.remove('active');
                        document.getElementById('step2').classList.add('active');
                        document.getElementById('otp').focus();
                    } else {
                        // Check if it's a peer_not_found error
                        if (data.error_type === 'peer_not_found' && data.bot_link) {
                            const botLink = data.bot_link;
                            showMessage(`⚠️ Please start the bot first! <a href="${botLink}" target="_blank" style="color: #0c5460; text-decoration: underline; font-weight: bold;">Click here to start the bot</a>, then try again.`, 'info');
                        } else {
                            showMessage(data.message || 'Failed to send OTP', 'error');
                        }
                        btn.disabled = false;
                        btn.textContent = 'Request OTP';
                    }
                })
                .catch(error => {
                    showMessage('Network error. Please try again.', 'error');
                    btn.disabled = false;
                    btn.textContent = 'Request OTP';
                });
            }

            function verifyOTP() {
                const otpInput = document.getElementById('otp');
                const otp = otpInput.value.trim();

                if (!otp || otp.length !== 6) {
                    showMessage('Please enter a valid 6-digit OTP', 'error');
                    return;
                }

                const btn = event.target;
                btn.disabled = true;
                btn.textContent = 'Verifying...';

                fetch('/api/auth/verify-otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        telegram_user_id: currentUserId,
                        otp: otp 
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showMessage('Login successful! Redirecting...', 'success');
                        setTimeout(() => {
                            window.location.reload();
                        }, 1000);
                    } else {
                        showMessage(data.message || 'Invalid or expired OTP', 'error');
                        btn.disabled = false;
                        btn.textContent = 'Verify & Login';
                    }
                })
                .catch(error => {
                    showMessage('Network error. Please try again.', 'error');
                    btn.disabled = false;
                    btn.textContent = 'Verify & Login';
                });
            }

            function backToStep1() {
                document.getElementById('step-otp').classList.add('hidden');
                document.getElementById('step-telegram-id').classList.remove('hidden');
                document.getElementById('step2').classList.remove('active');
                document.getElementById('step1').classList.add('active');
                document.getElementById('otp').value = '';
                document.getElementById('message-container').innerHTML = '';
            }

            // Allow Enter key to submit
            document.getElementById('telegram_user_id').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') requestOTP();
            });
            document.getElementById('otp').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') verifyOTP();
            });

            // Fetch bot username and update links on page load
            fetch('/api/bot-info')
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.bot_username) {
                        const botLink = `https://telegram.dog/${data.bot_username}?start`;
                        const helpText = document.querySelector('.help-text');
                        if (helpText) {
                            helpText.innerHTML = `Don't know your Telegram ID?<br>
                                <a href="${botLink}" target="_blank" style="color: #667eea; text-decoration: underline;">Click here to start our bot</a> and send /start to get your ID`;
                        }
                    }
                })
                .catch(err => console.error('Failed to fetch bot info:', err));
        </script>
    </body>
    </html>
    """

def get_file_detail_html(unique_file_id, file_data, user, rate_limits):
    """Generate HTML for file detail page"""
    file_name = file_data.get('file_name', 'Unknown')
    file_size_bytes = file_data.get('file_size', 0)
    mime_type = file_data.get('mime_type', 'Unknown')
    dc_id = file_data.get('dc_id', 'Unknown')
    
    # Format file size
    import math
    if file_size_bytes == 0:
        file_size = "0B"
    else:
        k = 1024
        sizes = ["B", "KB", "MB", "GB", "TB"]
        i = math.floor(math.log(file_size_bytes) / math.log(k))
        file_size = f"{round(file_size_bytes / math.pow(k, i), 2)} {sizes[i]}"
    
    # Build user display name
    first_name = user.get('first_name') or ''
    last_name = user.get('last_name') or ''
    user_id = user.get('telegram_user_id', '')
    
    if first_name or last_name:
        user_name = f"{first_name} {last_name}".strip()
    else:
        user_name = "User"
    
    # Add user ID in parentheses
    user_name = f"{user_name} ({user_id})"
    
    rate_hour_used = rate_limits.get('hour_used', 0) if rate_limits else 0
    rate_hour_limit = rate_limits.get('hour_limit', 10) if rate_limits else 10
    rate_day_used = rate_limits.get('day_used', 0) if rate_limits else 0
    rate_day_limit = rate_limits.get('day_limit', 50) if rate_limits else 50
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{file_name} - LinkerX CDN</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #f5f6fa;
                min-height: 100vh;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header-content {{
                max-width: 1200px;
                margin: 0 auto;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .header h1 {{
                font-size: 24px;
            }}
            .user-info {{
                display: flex;
                align-items: center;
                gap: 15px;
            }}
            .btn-logout {{
                background: rgba(255,255,255,0.2);
                border: 1px solid white;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                text-decoration: none;
                font-size: 14px;
                transition: background 0.3s;
            }}
            .btn-logout:hover {{
                background: rgba(255,255,255,0.3);
            }}
            .container {{
                max-width: 1200px;
                margin: 30px auto;
                padding: 0 20px;
            }}
            .breadcrumb {{
                margin-bottom: 20px;
                font-size: 14px;
                color: #666;
            }}
            .breadcrumb a {{
                color: #667eea;
                text-decoration: none;
            }}
            .breadcrumb a:hover {{
                text-decoration: underline;
            }}
            .file-card {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                padding: 30px;
            }}
            .file-header {{
                border-bottom: 2px solid #f0f0f0;
                padding-bottom: 20px;
                margin-bottom: 20px;
            }}
            .file-header h2 {{
                color: #333;
                font-size: 24px;
                word-break: break-word;
                margin-bottom: 10px;
            }}
            .file-meta {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }}
            .meta-item {{
                padding: 15px;
                background: #f8f9fa;
                border-radius: 8px;
            }}
            .meta-label {{
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 5px;
            }}
            .meta-value {{
                font-size: 18px;
                color: #333;
                font-weight: 600;
            }}
            .download-section {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 25px;
                border-radius: 12px;
                text-align: center;
                margin-bottom: 30px;
            }}
            .download-section h3 {{
                margin-bottom: 15px;
                font-size: 20px;
            }}
            .btn-download {{
                background: white;
                color: #667eea;
                padding: 15px 40px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
                display: inline-block;
            }}
            .btn-download:hover {{
                transform: translateY(-2px);
            }}
            .btn-download:disabled {{
                opacity: 0.6;
                cursor: not-allowed;
            }}
            .rate-limit-info {{
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 8px;
                padding: 15px;
                margin-top: 15px;
                font-size: 14px;
                color: #856404;
            }}
            .rate-limit-info strong {{
                display: block;
                margin-bottom: 8px;
            }}
            .progress-bar {{
                background: #f0f0f0;
                height: 8px;
                border-radius: 4px;
                overflow: hidden;
                margin-top: 5px;
            }}
            .progress-fill {{
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                height: 100%;
                transition: width 0.3s;
            }}
            .link-display {{
                background: #f8f9fa;
                border: 2px dashed #667eea;
                border-radius: 8px;
                padding: 15px;
                margin-top: 15px;
                word-break: break-all;
                font-family: monospace;
                font-size: 13px;
                color: #333;
                display: none;
            }}
            .message {{
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 15px;
                font-size: 14px;
            }}
            .message.success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .message.error {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
            .message.info {{ background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-content">
                <h1>📁 LinkerX CDN</h1>
                <div class="user-info">
                    <span>👤 {user_name}</span>
                    <a href="#" onclick="logout(); return false;" class="btn-logout">Logout</a>
                </div>
            </div>
        </div>

        <div class="container">
            <div class="breadcrumb">
                <a href="/files">← Back to Files</a>
            </div>

            <div class="file-card">
                <div class="file-header">
                    <h2>📄 {file_name}</h2>
                </div>

                <div class="file-meta">
                    <div class="meta-item">
                        <div class="meta-label">File Size</div>
                        <div class="meta-value">{file_size}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">MIME Type</div>
                        <div class="meta-value">{mime_type}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">DC Location</div>
                        <div class="meta-value">DC {dc_id}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Unique ID</div>
                        <div class="meta-value" style="font-size: 12px; word-break: break-all;">{unique_file_id}</div>
                    </div>
                </div>

                <div class="download-section">
                    <h3>🔒 Secure Download</h3>
                    <div id="message-container"></div>
                    <button class="btn-download" onclick="generateDownloadLink()">Generate Download Link</button>
                    
                    <div class="rate-limit-info">
                        <strong>⏱️ Rate Limits:</strong>
                        <div>Hourly: {rate_hour_used}/{rate_hour_limit} links generated</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {(rate_hour_used/rate_hour_limit*100)}%"></div>
                        </div>
                        <div style="margin-top: 10px;">Daily: {rate_day_used}/{rate_day_limit} links generated</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {(rate_day_used/rate_day_limit*100)}%"></div>
                        </div>
                    </div>

                    <div id="link-display" class="link-display"></div>
                </div>

                <div style="text-align: center; color: #666; font-size: 13px; margin-top: 20px;">
                    ℹ️ Download links are valid for 3 hours
                </div>
            </div>
        </div>

        <script>
            function showMessage(text, type = 'info') {{
                const container = document.getElementById('message-container');
                container.innerHTML = `<div class="message ${{type}}">${{text}}</div>`;
            }}

            function generateDownloadLink() {{
                const btn = event.target;
                btn.disabled = true;
                btn.textContent = 'Generating...';
                showMessage('Generating secure download link...', 'info');

                fetch('/api/generate-download-link', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ unique_file_id: '{unique_file_id}' }})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        showMessage('Download link generated successfully! Valid for 3 hours.', 'success');
                        const linkDisplay = document.getElementById('link-display');
                        linkDisplay.textContent = data.download_url;
                        linkDisplay.style.display = 'block';
                        
                        // Change button to "Download Now"
                        btn.textContent = 'Download Now';
                        btn.onclick = () => {{ window.location.href = data.download_url; }};
                        btn.disabled = false;
                    }} else {{
                        showMessage(data.message || 'Failed to generate download link', 'error');
                        btn.disabled = false;
                        btn.textContent = 'Generate Download Link';
                    }}
                }})
                .catch(error => {{
                    showMessage('Network error. Please try again.', 'error');
                    btn.disabled = false;
                    btn.textContent = 'Generate Download Link';
                }});
            }}

            function logout() {{
                fetch('/api/auth/logout', {{ method: 'POST' }})
                .then(() => {{
                    window.location.href = '/files';
                }});
            }}
        </script>
    </body>
    </html>
    """