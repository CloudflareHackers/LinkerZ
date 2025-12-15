# This file is a part of TG-
# Coding : Jyothis Jayanth [@EverythingSuckz]

import sys
import logging
import asyncio
import os
import base64
import requests
from .vars import Var
from aiohttp import web
from pyrogram import idle
from WebStreamer import bot_loop, utils
from WebStreamer import StreamBot
from WebStreamer.server import web_server
from WebStreamer.bot.clients import initialize_clients
from WebStreamer.utils import TokenParser

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

# Initialize TokenParser
parser = TokenParser()
GITHUB_TOKEN = parser.get_github_token()
GITHUB_USERNAME = parser.get_github_username()
GITHUB_REPO = parser.get_github_repo()
GITHUB_API_URL = "https://api.github.com"

async def upload_to_github(file_path, repo_path):
    try:
        if not os.path.exists(file_path):
            print(f"File {file_path} does not exist, skipping upload")
            return
        
        # Construct the API URL for the file in the repository
        url = f"{GITHUB_API_URL}/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{repo_path}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            # File exists, extract current content details
            print(f"File Found: {repo_path}")
            current_content = response.json()
            sha = current_content.get('sha', '')
            print(f"SHA: {sha}")
        elif response.status_code == 404:
            # File does not exist, initialize sha as empty string
            print(f"File Not Found: {repo_path}")
            sha = ''
        else:
            # Handle other response codes
            print(f"Failed to check {repo_path} on GitHub. Status code: {response.status_code}")
            response.raise_for_status()
        
        # Read the file content to upload
        with open(file_path, "rb") as file:
            content = base64.b64encode(file.read()).decode()
        
        # Prepare data for updating or creating the file
        data = {
            "message": f"Update {repo_path}",
            "content": content,
            "branch": "main"  # Adjust the branch as needed
        }

        if sha != '':
            data["sha"] = sha
        
        # Send PUT request to update the file if sha is provided; otherwise, POST to create new file
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        print(f"Trying to Upload {file_path} to GitHub")
        response = requests.put(url, json=data, headers=headers)
        
        response.raise_for_status()
        
        if response.status_code == 200 or response.status_code == 201:
            print(f"Updated {repo_path} on GitHub")
        else:
            print(f"Failed to update {repo_path} on GitHub. Status code: {response.status_code}")
    
    except Exception as e:
        print(f"Failed to upload {file_path} to GitHub")
        print(e)

async def download_from_github(repo_path):
    try:
        print(f"Downloading {repo_path} from GitHub")
        print(f"Current directory: {os.getcwd()}")  # Print current working directory
        
        url = f"{GITHUB_API_URL}/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{repo_path}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            content = base64.b64decode(response.json()["content"])
            
            # Extract file name from repo_path
            file_name = os.path.basename(repo_path)
            file_path = os.path.join(os.getcwd(), file_name)
            
            # Write content to file
            with open(file_path, "wb") as file:
                file.write(content)
            
            print(f"Downloaded {repo_path} from GitHub to {file_path}")
        
        elif response.status_code == 404:
            print(f"{repo_path} not found in GitHub, proceeding without session file")
        else:
            response.raise_for_status()
    
    except Exception as e:
        print(f"Failed to download {repo_path} from GitHub, proceeding without session file")
        print(e)

session_name = "WebStreamer"
session_file = f"{session_name}.session"

async def start_services():
    try:
        # Download session file from GitHub before starting the bot
        print("-------------------- Downloading Session File --------------------")
        await download_from_github(session_file)

        print()
        print("-------------------- Initializing Telegram Bot --------------------")
        await StreamBot.start()
        bot_info = await StreamBot.get_me()
        StreamBot.username = bot_info.username
        print("------------------------------ DONE ------------------------------")
        print()

        # Upload session file to GitHub after starting the bot
        print("-------------------- Uploading Session File --------------------")
        await upload_to_github(session_file, session_file)

        print("---------------------- Initializing Clients ----------------------")
        await initialize_clients()
        print("------------------------------ DONE ------------------------------")
        
        print("-------------------- Initializing Database --------------------")
        try:
            db = get_database()
            logging.info("Database initialized successfully (simplified, no auth)")
            print("------------------------------ DONE ------------------------------")
        except Exception as e:
            logging.error(f"Failed to initialize database: {e}")
            print("--------------------------- FAILED ------------------------------")
        
        # Pre-cache BIN_CHANNEL peer to avoid "Peer id invalid" errors
        if Var.BIN_CHANNEL:
            print("------------------ Pre-caching BIN_CHANNEL Peer ------------------")
            try:
                # Get the BIN_CHANNEL chat to cache it (bot-compatible method)
                chat = await StreamBot.get_chat(Var.BIN_CHANNEL)
                logging.info(f"Successfully cached BIN_CHANNEL: {chat.title if hasattr(chat, 'title') else Var.BIN_CHANNEL}")
                print("------------------------------ DONE ------------------------------")
            except Exception as e:
                logging.error(f"Failed to pre-cache BIN_CHANNEL: {e}")
                print("--------------------------- FAILED ------------------------------")
        if Var.ON_HEROKU:
            print("------------------ Starting Keep Alive Service ------------------")
            print()
            asyncio.create_task(utils.ping_server())
        print("--------------------- Initializing Web Server ---------------------")
        await server.setup()
        bind_address = "0.0.0.0" if Var.ON_HEROKU else Var.BIND_ADDRESS
        await web.TCPSite(server, bind_address, Var.PORT).start()
        print("------------------------------ DONE ------------------------------")
        print()
        print("------------------------- Service Started -------------------------")
        print("                        bot =>> {}".format(bot_info.first_name))
        if bot_info.dc_id:
            print("                        DC ID =>> {}".format(str(bot_info.dc_id)))
        print("                        server ip =>> {}".format(bind_address, Var.PORT))
        if Var.ON_HEROKU:
            print("                        app running on =>> {}".format(Var.FQDN))
        print("------------------------------------------------------------------")
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
        print("------------------------ Stopped Services ------------------------")
