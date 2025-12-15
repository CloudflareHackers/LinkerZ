# Simplified server - no auth routes
from aiohttp import web
from .stream_routes import routes as stream_routes


def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(stream_routes)
    return web_app
