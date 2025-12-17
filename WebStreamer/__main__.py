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
from WebStreamer.bot import session_name as bot_session_name

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

# Session file named based on BOT_ID from env (e.g., "123456789.session")
session_file = f"{bot_session_name}.session"

# Helper function to log and flush immediately (ensures logs appear on Heroku)
def log_flush(message, level="info"):
    """Log a message and flush stdout immediately for Heroku visibility"""
    if level == "error":
        logging.error(message)
    elif level == "warning":
        logging.warning(message)
    else:
        logging.info(message)
    sys.stdout.flush()
    sys.stderr.flush()

async def start_services():
    try:
        # Download session file from GitHub before starting the bot
        logging.info("=" * 70)
        logging.info("STEP 1: DOWNLOADING SESSION FILE FROM GITHUB")
        logging.info("=" * 70)
        logging.info(f"Session file to download: {session_file}")
        download_result = await download_from_github(session_file)
        if download_result:
            logging.info(f"✓ Session file downloaded successfully from GitHub")
        else:
            logging.info(f"! Session file not found in GitHub (will create new one)")
        logging.info("")

        logging.info("=" * 70)
        logging.info("STEP 2: INITIALIZING TELEGRAM BOT")
        logging.info("=" * 70)
        
        # Try to start the bot with existing session
        session_retry = False
        session_file_path = os.path.join(os.getcwd(), session_file)
        
        logging.info(f"Session file path: {session_file_path}")
        logging.info(f"Session file exists: {os.path.exists(session_file_path)}")
        logging.info(f"Current working directory: {os.getcwd()}")
        logging.info("Attempting to start bot with existing session...")
        
        try:
            await StreamBot.start()
            bot_info = await StreamBot.get_me()
            StreamBot.username = bot_info.username
            
            # Cache bot info for later use (avoids repeated API calls)
            cached_bot_info["username"] = bot_info.username
            cached_bot_info["first_name"] = bot_info.first_name
            cached_bot_info["id"] = bot_info.id
            
            logging.info(f"✓ Bot started successfully with existing session")
            logging.info(f"✓ Bot name: {bot_info.first_name}")
            logging.info(f"✓ Bot username: @{bot_info.username}")
            logging.info(f"✓ Bot ID: {bot_info.id}")
            logging.info("-" * 70)
            logging.info("")
        except Exception as session_error:
            error_str = str(session_error)
            error_str_lower = error_str.lower()
            
            logging.error("=" * 70)
            logging.error("SESSION ERROR DETECTED!")
            logging.error("=" * 70)
            logging.error(f"Error type: {type(session_error).__name__}")
            logging.error(f"Error message: {session_error}")
            logging.error("-" * 70)
            
            # Check if it's a session-related error
            if any(err in error_str_lower for err in ["no such table", "session", "auth", "database is locked", "database disk image is malformed"]):
                logging.warning(f"✓ Identified as session-related error, will re-authenticate")
                logging.info("")
                logging.info("=" * 70)
                logging.info("STEP 2B: RE-AUTHENTICATING WITH BOT TOKEN")
                logging.info("=" * 70)
                
                # Delete corrupted session file
                if os.path.exists(session_file_path):
                    logging.info(f"Deleting corrupted session file: {session_file_path}")
                    try:
                        os.remove(session_file_path)
                        logging.info(f"✓ Deleted corrupted session file successfully")
                    except Exception as delete_error:
                        logging.error(f"✗ Failed to delete session file: {delete_error}")
                else:
                    logging.info(f"! Session file doesn't exist, no need to delete")
                
                # Retry with fresh session (bot_token will create new session)
                logging.info("Starting fresh bot authentication with BOT_TOKEN...")
                try:
                    await StreamBot.start()
                    logging.info("✓ Bot.start() completed")
                    
                    bot_info = await StreamBot.get_me()
                    logging.info("✓ Bot.get_me() completed")
                    
                    StreamBot.username = bot_info.username
                    
                    # Cache bot info for later use
                    cached_bot_info["username"] = bot_info.username
                    cached_bot_info["first_name"] = bot_info.first_name
                    cached_bot_info["id"] = bot_info.id
                    
                    session_retry = True
                    logging.info("")
                    logging.info("✓✓✓ RE-AUTHENTICATION SUCCESSFUL ✓✓✓")
                    logging.info(f"✓ Bot name: {bot_info.first_name}")
                    logging.info(f"✓ Bot username: @{bot_info.username}")
                    logging.info(f"✓ Bot ID: {bot_info.id}")
                    
                    # Verify new session file was created
                    if os.path.exists(session_file_path):
                        file_size = os.path.getsize(session_file_path)
                        logging.info(f"✓ New session file created: {session_file_path} ({file_size} bytes)")
                    else:
                        logging.error(f"✗ Session file was NOT created at: {session_file_path}")
                    
                    logging.info("-" * 70)
                    logging.info("")
                except Exception as retry_error:
                    logging.error("=" * 70)
                    logging.error("RE-AUTHENTICATION FAILED!")
                    logging.error("=" * 70)
                    logging.error(f"Error type: {type(retry_error).__name__}")
                    logging.error(f"Error message: {retry_error}")
                    logging.error("-" * 70)
                    raise
            else:
                # Not a session error, re-raise
                logging.error(f"✗ NOT a session error, re-raising exception")
                raise

        # Upload session file to GitHub after starting the bot
        logging.info("=" * 70)
        logging.info("STEP 3: UPLOADING SESSION FILE TO GITHUB")
        logging.info("=" * 70)
        
        if session_retry:
            logging.info("! This is a NEW session (re-authenticated), uploading to GitHub...")
        else:
            logging.info("! This is an EXISTING session, updating GitHub backup...")
        
        logging.info(f"Session file to upload: {session_file}")
        logging.info(f"Session file path: {session_file_path}")
        logging.info(f"Session file exists: {os.path.exists(session_file_path)}")
        
        if os.path.exists(session_file_path):
            file_size = os.path.getsize(session_file_path)
            logging.info(f"Session file size: {file_size} bytes")
        
        logging.info("Starting GitHub upload...")
        upload_success = await upload_to_github(session_file, session_file)
        
        if upload_success:
            logging.info("✓✓✓ SESSION FILE UPLOADED TO GITHUB SUCCESSFULLY ✓✓✓")
            if session_retry:
                logging.info("✓ NEW session is now backed up to GitHub")
        else:
            logging.error("✗✗✗ GITHUB UPLOAD FAILED ✗✗✗")
            if session_retry:
                logging.warning("✗ NEW session was NOT backed up - manual backup recommended!")
        
        logging.info("-" * 70)
        logging.info("")

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
    try:
        await server.cleanup()
    except Exception as e:
        logging.error(f"Error during server cleanup: {e}")
    
    try:
        # Check if StreamBot is already stopped before attempting to stop
        if StreamBot.is_connected:
            await StreamBot.stop()
            logging.info("Bot stopped successfully")
        else:
            logging.info("Bot already stopped, skipping stop")
    except ConnectionError as e:
        if "already terminated" in str(e).lower():
            logging.info("Client already terminated, cleanup complete")
        else:
            logging.error(f"Connection error during bot cleanup: {e}")
    except Exception as e:
        logging.error(f"Error during bot cleanup: {e}")

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
