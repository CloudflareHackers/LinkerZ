#!/usr/bin/env python3
"""
Simple test server to verify the 404 page styling matches the home page
and displays "Link Expired" message.
"""

from aiohttp import web
import asyncio

# Home page HTML (similar to stream_routes.py)
HOME_PAGE = '''<html>
<head>
    <title>LinkerX CDN</title>
    <style>
        body{ margin:0; padding:0; width:100%; height:100%; color:#b0bec5; display:table; font-weight:100; font-family:Lato }
        .container{ text-align:center; display:table-cell; vertical-align:middle }
        .content{ text-align:center; display:inline-block }
        .message{ font-size:80px; margin-bottom:40px }
        .submessage{ font-size:40px; margin-bottom:40px }
        .copyright{ font-size:20px; }
        a{ text-decoration:none; color:#3498db }
    </style>
</head>
<body>
    <div class="container">
        <div class="content">
            <div class="message">LinkerX CDN</div>
            <div class="submessage">All Systems Operational</div>
            <div class="copyright">Hash Hackers and LiquidX Projects</div>
        </div>
    </div>
</body>
</html>'''

# 404 page HTML (from our updated __init__.py)
ERROR_404_PAGE = '''<html>
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

@web.middleware
async def error_middleware(request, handler):
    """Custom 404 handler middleware"""
    try:
        response = await handler(request)
        if response.status == 404:
            return web.Response(text=ERROR_404_PAGE, content_type="text/html", status=404)
        return response
    except web.HTTPException as ex:
        if ex.status == 404:
            return web.Response(text=ERROR_404_PAGE, content_type="text/html", status=404)
        raise

async def home(request):
    """Home page handler"""
    return web.Response(text=HOME_PAGE, content_type="text/html")

async def test_404(request):
    """Endpoint to test 404 page by raising HTTPNotFound"""
    raise web.HTTPNotFound()

def create_app():
    """Create and configure the web application"""
    app = web.Application(middlewares=[error_middleware])
    app.router.add_get('/', home)
    app.router.add_get('/test-404', test_404)
    return app

if __name__ == '__main__':
    print("=" * 70)
    print("Testing 404 Page Implementation")
    print("=" * 70)
    print()
    print("Starting test server on http://0.0.0.0:8080")
    print()
    print("Test URLs:")
    print("  - Home page:        http://0.0.0.0:8080/")
    print("  - 404 test:         http://0.0.0.0:8080/test-404")
    print("  - Any invalid path: http://0.0.0.0:8080/any-invalid-path")
    print()
    print("The 404 page should:")
    print("  ✓ Use the same CSS/HTML structure as the home page")
    print("  ✓ Display 'Link Expired' instead of 'All Systems Operational'")
    print("  ✓ Show the message in red color (#e74c3c)")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 70)
    print()
    
    app = create_app()
    web.run_app(app, host='0.0.0.0', port=8080)
