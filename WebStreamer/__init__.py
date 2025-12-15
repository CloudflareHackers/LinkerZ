# This file is a part of TG-
# Coding : Jyothis Jayanth [@EverythingSuckz]
from time import time
import os
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

# Configure limited thread pool executor to prevent thread exhaustion
# This applies to all asyncio operations including Pyrogram clients
# Reduced from default (CPU count * 5) to prevent "can't start new thread" errors on Heroku
# Can be configured via MAX_THREAD_WORKERS env variable (default: 10)
max_workers = int(os.environ.get("MAX_THREAD_WORKERS", "10"))
limited_executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="bot_pool_")

# Create new event loop (fixes deprecation warning for asyncio.get_event_loop())
bot_loop = asyncio.new_event_loop()
asyncio.set_event_loop(bot_loop)
bot_loop.set_default_executor(limited_executor)

logging.info(f"Configured thread pool with {max_workers} max workers")

# Import Var and StreamBot AFTER configuring the executor
from .vars import Var
from WebStreamer.bot import StreamBot

__version__ = 2.2
StartTime = time()
