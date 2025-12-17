import asyncio
import logging
from ..vars import Var
from pyrogram import Client
from WebStreamer.utils import TokenParser, upload_to_github, download_from_github
from . import multi_clients, work_loads, StreamBot

parser = TokenParser()

# Base session name from BOT_ID
base_session_name = str(Var.BOT_ID) if Var.BOT_ID else "WebStreamer"

async def initialize_clients():
    multi_clients[0] = StreamBot
    work_loads[0] = 0
    all_tokens = parser.parse_from_env()
    if not all_tokens:
        logging.info("No additional clients found, using default client")
        return

    async def start_client(client_id, token):
        try:
            # Add staggered delay to prevent all clients from starting simultaneously
            # This helps prevent thread exhaustion
            await asyncio.sleep(client_id * 2)  # 2 seconds delay between each client
            
            logging.info(f"Starting - Client {client_id}")
            if client_id == len(all_tokens):
                logging.info("This will take some time, please wait...")
            # Session name includes base bot_id for unique identification per server
            session_name = f"{base_session_name}_client_{client_id}"
            session_file = f"{session_name}.session"

            # Download session file from GitHub
            await download_from_github(session_file)

            client = await Client(
                name=session_name,
                api_id=Var.API_ID,
                api_hash=Var.API_HASH,
                bot_token=token,
                sleep_threshold=Var.SLEEP_THRESHOLD,
                no_updates=False,  # Changed to False to receive updates for media handling
                in_memory=False
            ).start()
            work_loads[client_id] = 0

            # Wait a moment for session file to be fully written
            await asyncio.sleep(1)
            
            # Upload session file to GitHub (use full path for reliability)
            import os
            session_file_path = os.path.join(os.getcwd(), session_file)
            logging.info(f"Uploading session file: {session_file_path}")
            await upload_to_github(session_file_path, session_file)

            return client_id, client
        except Exception:
            logging.error(f"Failed starting Client - {client_id} Error:", exc_info=True)

    clients = await asyncio.gather(*[start_client(i, token) for i, token in all_tokens.items()])
    multi_clients.update(dict(clients))
    if len(multi_clients) != 1:
        Var.MULTI_CLIENT = True
        logging.info("Multi-Client Mode Enabled")
        
        # Register media handlers on all multi clients
        from WebStreamer.bot.plugins.media_handler import register_multi_client_handlers
        register_multi_client_handlers()
        logging.info(f"Registered media handlers on {len(multi_clients) - 1} additional bot(s)")
    else:
        logging.info("No additional clients were initialized, using default client")
