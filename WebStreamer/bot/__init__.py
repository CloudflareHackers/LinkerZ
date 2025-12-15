# This file is a part of TG-
# Coding : Jyothis Jayanth [@EverythingSuckz]

from ..vars import Var
from pyrogram import Client, utils
from os import getcwd
from concurrent.futures import ThreadPoolExecutor

# Updated MIN_CHANNEL_ID to support newer/larger channel IDs
# Old value: -1002947483647
# New value supports channel IDs like -1003260273478
utils.MIN_CHANNEL_ID = -1007852516352
utils.MIN_CHAT_ID = -999999999999

# Create a limited thread pool executor to prevent thread exhaustion
# Reducing max_workers helps avoid "can't start new thread" errors on Heroku
main_executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="main_bot_")

StreamBot = Client(
    name="WebStreamer",  # This will create a session file named "WebStreamer.session"
    api_id=Var.API_ID,
    api_hash=Var.API_HASH,
    workdir=getcwd(),  # Ensure the working directory is set correctly
    plugins={"root": "WebStreamer/bot/plugins"},
    bot_token=Var.BOT_TOKEN,
    sleep_threshold=Var.SLEEP_THRESHOLD,
    workers=Var.WORKERS,
    in_memory=False,  # Set this to False to create a session file
    executor=main_executor  # Use limited thread pool to prevent exhaustion
)

multi_clients = {}
work_loads = {}
