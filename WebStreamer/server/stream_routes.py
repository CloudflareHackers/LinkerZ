# Taken from megadlbot_oss <https://github.com/eyaadh/megadlbot_oss/blob/master/mega/webserver/routes.py>
# Thanks to Eyaadh <https://github.com/eyaadh>

import re
import time
import math
import logging
import secrets
import mimetypes
import time
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

THREADPOOL = ThreadPoolExecutor(max_workers=1000)

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

@routes.get("/files", allow_head=True)
async def files_list_handler(request: web.Request):
    """Display all files from database with search functionality (requires auth)"""
    try:
        # Check authentication
        user = await get_authenticated_user(request)
        
        if not user:
            # Show login page
            return web.Response(text=get_login_page_html(), content_type="text/html")
        # Get search query parameter
        search_query = request.query.get('search', '').strip()
        
        # Get database instance
        db = get_database()
        
        # Get files from database
        files = db.get_all_files(search_query=search_query if search_query else None, limit=1000)
        total_count = db.get_file_count(search_query=search_query if search_query else None)
        
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
                    <td style="padding: 12px; border-bottom: 1px solid #ecf0f1; word-break: break-all; font-size: 12px; font-family: monospace;">{unique_id}</td>
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
                <td colspan="5" style="padding: 40px; text-align: center; color: #95a5a6; font-size: 18px;">
                    No files found
                </td>
            </tr>
            """
        
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
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>LinkerX CDN</h1>
                <p>File Browser & Download Center</p>
            </div>
            
            <div class="container">
                <div class="search-box">
                    <form method="get" action="/files">
                        <input type="text" name="search" placeholder="Search files by name..." value="{search_query}" autofocus>
                        <button type="submit">Search</button>
                        {f'<a href="/files" class="clear-search">Clear</a>' if search_query else ''}
                    </form>
                </div>
                
                <div class="stats">
                    {f'Found <strong>{total_count}</strong> file(s)' if search_query else f'Total: <strong>{total_count}</strong> file(s)'}
                </div>
                
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Unique ID</th>
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
            </div>
            
            <div class="footer">
                Hash Hackers and LiquidX Projects
            </div>
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

@routes.get("/download/{unique_file_id}", allow_head=True)
async def download_by_unique_id(request: web.Request):
    """Stream media file using unique_file_id from database"""
    try:
        unique_file_id = request.match_info['unique_file_id']
        logging.info(f"Download request for unique_file_id: {unique_file_id}")
        
        # Get file information from database
        db = get_database()
        file_data = db.get_file_ids(unique_file_id)
        
        if not file_data or not file_data['bot_file_ids']:
            raise web.HTTPNotFound(
                text='<html> <head> <title>LinkerX CDN</title> <style> body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato } .container{ text-align:center; display:table-cell; vertical-align:middle } .content{ text-align:center; display:inline-block } .message{ font-size:80px; margin-bottom:40px } .submessage{ font-size:40px; margin-bottom:40px } .copyright{ font-size:20px; } a{ text-decoration:none; color:#3498db } </style> </head> <body> <div class="container"> <div class="content"> <div class="message">LinkerX CDN</div> <div class="submessage">File Not Found in Database</div> <div class="copyright">Hash Hackers and LiquidX Projects</div> </div> </div> </body> </html>', 
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