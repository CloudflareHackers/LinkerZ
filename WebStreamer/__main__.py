# This file is a part of TG-
# Coding : Jyothis Jayanth [@EverythingSuckz]

import sys
import logging
import asyncio
import os
from .vars import Var
from aiohttp import web
from pyrogram import idle
from WebStreamer import bot_loop, utils
from WebStreamer import StreamBot
from WebStreamer.server import web_server
from WebStreamer.bot.clients import initialize_clients
from WebStreamer.bot import cached_bot_info
from WebStreamer.utils import upload_to_github, download_from_github

logging.basicConfig(
    level=logging.INFO,
    datefmt="%d/%m/%Y %H:%M:%S",
    format="[%(asctime)s][%(levelname)s] => %(message)s",
    handlers=[logging.StreamHandler(stream=sys.stdout),
              logging.FileHandler("streambot.log", mode="a", encoding="utf-8")],)

logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
#logging.getLogger("pyrogram").setLevel(logging.DEBUG)
#logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

server = web.AppRunner(web_server())

session_name = "WebStreamer"
session_file = f"{session_name}.session"

async def start_services():
    try:
        # Download session file from GitHub before starting the bot
        logging.info("-------------------- Downloading Session File --------------------")
        await download_from_github(session_file)

        logging.info("")
        logging.info("-------------------- Initializing Telegram Bot --------------------")
        await StreamBot.start()
        bot_info = await StreamBot.get_me()
        StreamBot.username = bot_info.username
        
        # Cache bot info for later use (avoids repeated API calls)
        cached_bot_info["username"] = bot_info.username
        cached_bot_info["first_name"] = bot_info.first_name
        cached_bot_info["id"] = bot_info.id
        
        logging.info("------------------------------ DONE ------------------------------")
        logging.info("")

        # Upload session file to GitHub after starting the bot
        logging.info("-------------------- Uploading Session File --------------------")
        await upload_to_github(session_file, session_file)

        logging.info("---------------------- Initializing Clients ----------------------")
        await initialize_clients()
        logging.info("------------------------------ DONE ------------------------------")
        
        # Pre-cache BIN_CHANNEL peer to avoid "Peer id invalid" errors
        if Var.BIN_CHANNEL:
            logging.info("------------------ Pre-caching BIN_CHANNEL Peer ------------------")
            try:
                # Get the BIN_CHANNEL chat to cache it (bot-compatible method)
                chat = await StreamBot.get_chat(Var.BIN_CHANNEL)
                logging.info(f"Successfully cached BIN_CHANNEL: {chat.title if hasattr(chat, 'title') else Var.BIN_CHANNEL}")
                logging.info("------------------------------ DONE ------------------------------")
            except Exception as e:
                logging.error(f"Failed to pre-cache BIN_CHANNEL: {e}")
                logging.info("--------------------------- FAILED ------------------------------")
        if Var.ON_HEROKU:
            logging.info("------------------ Starting Keep Alive Service ------------------")
            logging.info("")
            asyncio.create_task(utils.ping_server())
        logging.info("--------------------- Initializing Web Server ---------------------")
        await server.setup()
        bind_address = "0.0.0.0" if Var.ON_HEROKU else Var.BIND_ADDRESS
        await web.TCPSite(server, bind_address, Var.PORT).start()
        logging.info("------------------------------ DONE ------------------------------")
        logging.info("")
        logging.info("------------------------- Service Started -------------------------")
        logging.info("                        bot =>> {}".format(bot_info.first_name))
        if bot_info.dc_id:
            logging.info("                        DC ID =>> {}".format(str(bot_info.dc_id)))
        logging.info("                        server ip =>> {}:{}".format(bind_address, Var.PORT))
        if Var.ON_HEROKU:
            logging.info("                        app running on =>> {}".format(Var.FQDN))
        logging.info("------------------------------------------------------------------")
        await idle()
    except Exception as e:
        logging.error(e.with_traceback(None))
        await cleanup()

async def cleanup():
    await server.cleanup()
    await StreamBot.stop()

if __name__ == "__main__":
    try:
        bot_loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        pass
    except Exception as err:
        logging.error(err.with_traceback(None))
    finally:
        bot_loop.run_until_complete(cleanup())
        bot_loop.stop()
        logging.info("------------------------ Stopped Services ------------------------")
