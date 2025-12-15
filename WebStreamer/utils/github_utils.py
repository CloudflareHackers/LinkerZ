# Shared GitHub utilities for session file management
# Using aiohttp for async HTTP operations

import os
import base64
import logging
import aiohttp
from typing import Optional
from ..utils import TokenParser

# Initialize parser and get GitHub credentials
parser = TokenParser()
GITHUB_TOKEN = parser.get_github_token()
GITHUB_USERNAME = parser.get_github_username()
GITHUB_REPO = parser.get_github_repo()
GITHUB_API_URL = "https://api.github.com"


async def upload_to_github(file_path: str, repo_path: str) -> bool:
    """
    Upload a file to GitHub repository using async HTTP.
    
    Args:
        file_path: Local path to the file to upload
        repo_path: Path in the GitHub repository
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not os.path.exists(file_path):
            logging.warning(f"File {file_path} does not exist, skipping upload")
            return False
        
        if not GITHUB_TOKEN or not GITHUB_USERNAME or not GITHUB_REPO:
            logging.warning("GitHub credentials not configured, skipping upload")
            return False
        
        # Construct the API URL for the file in the repository
        url = f"{GITHUB_API_URL}/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{repo_path}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with aiohttp.ClientSession() as session:
            # Check if file exists
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    # File exists, extract current content details
                    logging.info(f"File Found: {repo_path}")
                    current_content = await response.json()
                    sha = current_content.get('sha', '')
                    logging.debug(f"SHA: {sha}")
                elif response.status == 404:
                    # File does not exist, initialize sha as empty string
                    logging.info(f"File Not Found: {repo_path}")
                    sha = ''
                else:
                    # Handle other response codes
                    logging.error(f"Failed to check {repo_path} on GitHub. Status code: {response.status}")
                    return False
            
            # Read the file content to upload
            with open(file_path, "rb") as file:
                content = base64.b64encode(file.read()).decode()
            
            # Prepare data for updating or creating the file
            data = {
                "message": f"Update {repo_path}",
                "content": content,
                "branch": "main"  # Adjust the branch as needed
            }

            if sha:
                data["sha"] = sha
            
            # Send PUT request to update/create the file
            logging.info(f"Uploading {file_path} to GitHub")
            async with session.put(url, json=data, headers=headers) as response:
                if response.status in (200, 201):
                    logging.info(f"Updated {repo_path} on GitHub")
                    return True
                else:
                    logging.error(f"Failed to update {repo_path} on GitHub. Status code: {response.status}")
                    return False
    
    except Exception as e:
        logging.error(f"Failed to upload {file_path} to GitHub: {e}")
        return False


async def download_from_github(repo_path: str, local_path: Optional[str] = None) -> bool:
    """
    Download a file from GitHub repository using async HTTP.
    
    Args:
        repo_path: Path in the GitHub repository
        local_path: Local path to save the file (defaults to current directory)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logging.info(f"Downloading {repo_path} from GitHub")
        logging.debug(f"Current directory: {os.getcwd()}")
        
        if not GITHUB_TOKEN or not GITHUB_USERNAME or not GITHUB_REPO:
            logging.warning("GitHub credentials not configured, skipping download")
            return False
        
        url = f"{GITHUB_API_URL}/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{repo_path}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    content = base64.b64decode(data["content"])
                    
                    # Determine file path
                    if local_path:
                        file_path = local_path
                    else:
                        file_name = os.path.basename(repo_path)
                        file_path = os.path.join(os.getcwd(), file_name)
                    
                    # Write content to file
                    with open(file_path, "wb") as file:
                        file.write(content)
                    
                    logging.info(f"Downloaded {repo_path} from GitHub to {file_path}")
                    return True
                
                elif response.status == 404:
                    logging.info(f"{repo_path} not found in GitHub, proceeding without session file")
                    return False
                else:
                    logging.error(f"Failed to download {repo_path}. Status code: {response.status}")
                    return False
    
    except Exception as e:
        logging.error(f"Failed to download {repo_path} from GitHub: {e}")
        return False
