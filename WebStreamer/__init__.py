# This file is a part of TG-
# Coding : Jyothis Jayanth [@EverythingSuckz]
from time import time
from .vars import Var
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Configure limited thread pool executor to prevent thread exhaustion
# This applies to all asyncio operations including Pyrogram clients
# Reduced from default (CPU count * 5) to prevent "can't start new thread" errors on Heroku
limited_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="bot_pool_")

# Get or create event loop and set the custom executor
bot_loop = asyncio.get_event_loop()
bot_loop.set_default_executor(limited_executor)

# Import StreamBot AFTER configuring the executor
from WebStreamer.bot import StreamBot

__version__ = 2.2
StartTime = time()
