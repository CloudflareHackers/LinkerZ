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
            
            log_flush("=" * 70, "error")
            log_flush("SESSION ERROR DETECTED!", "error")
            log_flush("=" * 70, "error")
            log_flush(f"Error type: {type(session_error).__name__}", "error")
            log_flush(f"Error message: {session_error}", "error")
            log_flush("-" * 70, "error")
            
            # Check if it's a session-related error
            if any(err in error_str_lower for err in ["no such table", "session", "auth", "database is locked", "database disk image is malformed"]):
                log_flush("✓ Identified as session-related error, will re-authenticate", "warning")
                log_flush("")
                log_flush("=" * 70)
                log_flush("STEP 2B: RE-AUTHENTICATING WITH BOT TOKEN")
                log_flush("=" * 70)
                
                # Delete corrupted session file and any related files
                for file_to_delete in [session_file_path, session_file_path + "-journal", session_file_path + "-wal", session_file_path + "-shm"]:
                    if os.path.exists(file_to_delete):
                        log_flush(f"Deleting: {file_to_delete}")
                        try:
                            os.remove(file_to_delete)
                            log_flush(f"✓ Deleted: {file_to_delete}")
                        except Exception as delete_error:
                            log_flush(f"✗ Failed to delete {file_to_delete}: {delete_error}", "error")
                
                # Retry with fresh session (bot_token will create new session)
                log_flush("Starting fresh bot authentication with BOT_TOKEN...")
                try:
                    await StreamBot.start()
                    log_flush("✓ Bot.start() completed")
                    
                    bot_info = await StreamBot.get_me()
                    log_flush("✓ Bot.get_me() completed")
                    
                    StreamBot.username = bot_info.username
                    
                    # Cache bot info for later use
                    cached_bot_info["username"] = bot_info.username
                    cached_bot_info["first_name"] = bot_info.first_name
                    cached_bot_info["id"] = bot_info.id
                    
                    session_retry = True
                    log_flush("")
                    log_flush("✓✓✓ RE-AUTHENTICATION SUCCESSFUL ✓✓✓")
                    log_flush(f"✓ Bot name: {bot_info.first_name}")
                    log_flush(f"✓ Bot username: @{bot_info.username}")
                    log_flush(f"✓ Bot ID: {bot_info.id}")
                    
                    # Verify new session file was created
                    if os.path.exists(session_file_path):
                        file_size = os.path.getsize(session_file_path)
                        log_flush(f"✓ New session file created: {session_file_path} ({file_size} bytes)")
                        
                        # IMMEDIATE UPLOAD after re-authentication to ensure it happens
                        log_flush(">>> IMMEDIATE SESSION UPLOAD AFTER RE-AUTH <<<")
                        try:
                            immediate_upload = await upload_to_github(session_file_path, session_file)
                            if immediate_upload:
                                log_flush("✓✓✓ IMMEDIATE UPLOAD SUCCESSFUL ✓✓✓")
                            else:
                                log_flush("✗ Immediate upload returned False", "warning")
                        except Exception as imm_err:
                            log_flush(f"✗ Immediate upload exception: {imm_err}", "error")
                    else:
                        log_flush(f"✗ Session file was NOT created at: {session_file_path}", "error")
                        # List directory contents for debugging
                        log_flush(f"Directory contents of {os.getcwd()}:")
                        for f in os.listdir(os.getcwd()):
                            if 'session' in f.lower():
                                log_flush(f"  - {f}")
                    
                    log_flush("-" * 70)
                    log_flush("")
                except Exception as retry_error:
                    log_flush("=" * 70, "error")
                    log_flush("RE-AUTHENTICATION FAILED!", "error")
                    log_flush("=" * 70, "error")
                    log_flush(f"Error type: {type(retry_error).__name__}", "error")
                    log_flush(f"Error message: {retry_error}", "error")
                    log_flush("-" * 70, "error")
                    raise
            else:
                # Not a session error, re-raise
                log_flush(f"✗ NOT a session error, re-raising exception", "error")
                raise

        # Upload session file to GitHub after starting the bot
        log_flush("=" * 70)
        log_flush("STEP 3: UPLOADING SESSION FILE TO GITHUB")
        log_flush("=" * 70)
        
        if session_retry:
            log_flush("! This is a NEW session (re-authenticated), uploading to GitHub...")
        else:
            log_flush("! This is an EXISTING session, updating GitHub backup...")
        
        log_flush(f"Session file to upload: {session_file}")
        log_flush(f"Session file path: {session_file_path}")
        log_flush(f"Session file exists: {os.path.exists(session_file_path)}")
        
        if os.path.exists(session_file_path):
            file_size = os.path.getsize(session_file_path)
            log_flush(f"Session file size: {file_size} bytes")
            
            # Upload with retry logic (use full path for reliability)
            upload_success = False
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                log_flush(f"GitHub upload attempt {attempt}/{max_retries}...")
                try:
                    upload_success = await upload_to_github(session_file_path, session_file)
                    if upload_success:
                        log_flush(f"✓✓✓ SESSION FILE UPLOADED TO GITHUB SUCCESSFULLY (attempt {attempt}) ✓✓✓")
                        if session_retry:
                            log_flush("✓ NEW session is now backed up to GitHub")
                        break
                    else:
                        log_flush(f"✗ Upload attempt {attempt} returned False", "warning")
                except Exception as upload_err:
                    log_flush(f"✗ Upload attempt {attempt} failed: {upload_err}", "error")
                
                if attempt < max_retries:
                    log_flush(f"Waiting 2 seconds before retry...")
                    await asyncio.sleep(2)
            
            if not upload_success:
                log_flush("✗✗✗ GITHUB UPLOAD FAILED AFTER ALL RETRIES ✗✗✗", "error")
                if session_retry:
                    log_flush("✗ NEW session was NOT backed up - manual backup recommended!", "warning")
        else:
            log_flush(f"✗ Session file not found at {session_file_path}, cannot upload", "error")
        
        log_flush("-" * 70)
        log_flush("")

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
