# Simplified server - no auth routes
from aiohttp import web
from .stream_routes import routes as stream_routes


@web.middleware
async def error_middleware(request, handler):
    try:
        response = await handler(request)
        if response.status == 404:
            # Return custom 404 page with same styling as home page
            html_content = '''<html>
<head>
    <title>Link Expired - LinkerX CDN</title>
    <style>
        body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato }
        .container{ text-align:center; display:table-cell; vertical-align:middle }
        .content{ text-align:center; display:inline-block }
        .message{ font-size:80px; margin-bottom:40px }
        .submessage{ font-size:40px; margin-bottom:40px; color:#e74c3c }
        .copyright{ font-size:20px; }
        a{ text-decoration:none; color:#3498db }
    </style>
</head>
<body>
    <div class="container">
        <div class="content">
            <div class="message">LinkerX CDN</div>
            <div class="submessage">Link Expired</div>
            <div class="copyright">Hash Hackers and LiquidX Projects</div>
        </div>
    </div>
</body>
</html>'''
            return web.Response(text=html_content, content_type="text/html", status=404)
        return response
    except web.HTTPException as ex:
        if ex.status == 404:
            # Return custom 404 page with same styling as home page
            html_content = '''<html>
<head>
    <title>Link Expired - LinkerX CDN</title>
    <style>
        body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato }
        .container{ text-align:center; display:table-cell; vertical-align:middle }
        .content{ text-align:center; display:inline-block }
        .message{ font-size:80px; margin-bottom:40px }
        .submessage{ font-size:40px; margin-bottom:40px; color:#e74c3c }
        .copyright{ font-size:20px; }
        a{ text-decoration:none; color:#3498db }
    </style>
</head>
<body>
    <div class="container">
        <div class="content">
            <div class="message">LinkerX CDN</div>
            <div class="submessage">Link Expired</div>
            <div class="copyright">Hash Hackers and LiquidX Projects</div>
        </div>
    </div>
</body>
</html>'''
            return web.Response(text=html_content, content_type="text/html", status=404)
        raise


def web_server():
    web_app = web.Application(client_max_size=30000000, middlewares=[error_middleware])
    web_app.add_routes(stream_routes)
    return web_app


def make_runner():
    return web.AppRunner(web_server(), keepalive_timeout=65)
