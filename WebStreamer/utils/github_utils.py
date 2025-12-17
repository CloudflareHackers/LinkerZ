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
        logging.info(f"[GitHub Upload] Starting upload process...")
        logging.info(f"[GitHub Upload] Local file path: {file_path}")
        logging.info(f"[GitHub Upload] GitHub repo path: {repo_path}")
        
        if not os.path.exists(file_path):
            logging.warning(f"[GitHub Upload] ✗ File {file_path} does not exist, skipping upload")
            return False
        
        file_size = os.path.getsize(file_path)
        logging.info(f"[GitHub Upload] File size: {file_size} bytes")
        
        if not GITHUB_TOKEN or not GITHUB_USERNAME or not GITHUB_REPO:
            logging.warning(f"[GitHub Upload] ✗ GitHub credentials not configured:")
            logging.warning(f"[GitHub Upload]   - GITHUB_TOKEN: {'SET' if GITHUB_TOKEN else 'NOT SET'}")
            logging.warning(f"[GitHub Upload]   - GITHUB_USERNAME: {GITHUB_USERNAME if GITHUB_USERNAME else 'NOT SET'}")
            logging.warning(f"[GitHub Upload]   - GITHUB_REPO: {GITHUB_REPO if GITHUB_REPO else 'NOT SET'}")
            logging.warning(f"[GitHub Upload] Skipping upload")
            return False
        
        logging.info(f"[GitHub Upload] ✓ GitHub credentials configured")
        logging.info(f"[GitHub Upload] Target repo: {GITHUB_USERNAME}/{GITHUB_REPO}")
        
        # Construct the API URL for the file in the repository
        url = f"{GITHUB_API_URL}/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{repo_path}"
        logging.info(f"[GitHub Upload] API URL: {url}")
        
        headers = {
            "Authorization": f"token {GITHUB_TOKEN[:10]}...",  # Only log first 10 chars
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with aiohttp.ClientSession() as session:
            # Check if file exists
            logging.info(f"[GitHub Upload] Checking if file exists on GitHub...")
            async with session.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}) as response:
                if response.status == 200:
                    # File exists, extract current content details
                    logging.info(f"[GitHub Upload] ✓ File exists on GitHub: {repo_path}")
                    current_content = await response.json()
                    sha = current_content.get('sha', '')
                    logging.info(f"[GitHub Upload] Current SHA: {sha[:10]}...")
                elif response.status == 404:
                    # File does not exist, initialize sha as empty string
                    logging.info(f"[GitHub Upload] ! File does not exist on GitHub (will create new): {repo_path}")
                    sha = ''
                else:
                    # Handle other response codes
                    logging.error(f"[GitHub Upload] ✗ Failed to check file on GitHub")
                    logging.error(f"[GitHub Upload] Status code: {response.status}")
                    try:
                        error_body = await response.text()
                        logging.error(f"[GitHub Upload] Response: {error_body[:200]}")
                    except:
                        pass
                    return False
            
            # Read the file content to upload
            logging.info(f"[GitHub Upload] Reading file content...")
            with open(file_path, "rb") as file:
                content = base64.b64encode(file.read()).decode()
            
            content_length = len(content)
            logging.info(f"[GitHub Upload] Encoded content length: {content_length} chars")
            
            # Prepare data for updating or creating the file
            data = {
                "message": f"Update {repo_path}",
                "content": content,
                "branch": "main"  # Adjust the branch as needed
            }

            if sha:
                data["sha"] = sha
                logging.info(f"[GitHub Upload] Mode: UPDATE (with SHA)")
            else:
                logging.info(f"[GitHub Upload] Mode: CREATE (no SHA)")
            
            # Send PUT request to update/create the file
            logging.info(f"[GitHub Upload] Sending PUT request to GitHub...")
            async with session.put(url, json=data, headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}) as response:
                if response.status in (200, 201):
                    logging.info(f"[GitHub Upload] ✓✓✓ SUCCESS! File uploaded to GitHub")
                    logging.info(f"[GitHub Upload] Status code: {response.status}")
                    return True
                else:
                    logging.error(f"[GitHub Upload] ✗✗✗ FAILED to upload to GitHub")
                    logging.error(f"[GitHub Upload] Status code: {response.status}")
                    try:
                        error_body = await response.text()
                        logging.error(f"[GitHub Upload] Response: {error_body[:500]}")
                    except:
                        pass
                    return False
    
    except Exception as e:
        logging.error(f"[GitHub Upload] ✗✗✗ EXCEPTION during upload: {e}")
        import traceback
        logging.error(f"[GitHub Upload] Traceback: {traceback.format_exc()}")
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
        logging.info(f"[GitHub Download] Starting download process...")
        logging.info(f"[GitHub Download] GitHub repo path: {repo_path}")
        logging.info(f"[GitHub Download] Current directory: {os.getcwd()}")
        
        if not GITHUB_TOKEN or not GITHUB_USERNAME or not GITHUB_REPO:
            logging.warning(f"[GitHub Download] ✗ GitHub credentials not configured:")
            logging.warning(f"[GitHub Download]   - GITHUB_TOKEN: {'SET' if GITHUB_TOKEN else 'NOT SET'}")
            logging.warning(f"[GitHub Download]   - GITHUB_USERNAME: {GITHUB_USERNAME if GITHUB_USERNAME else 'NOT SET'}")
            logging.warning(f"[GitHub Download]   - GITHUB_REPO: {GITHUB_REPO if GITHUB_REPO else 'NOT SET'}")
            logging.warning(f"[GitHub Download] Skipping download")
            return False
        
        logging.info(f"[GitHub Download] ✓ GitHub credentials configured")
        logging.info(f"[GitHub Download] Target repo: {GITHUB_USERNAME}/{GITHUB_REPO}")
        
        url = f"{GITHUB_API_URL}/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{repo_path}"
        logging.info(f"[GitHub Download] API URL: {url}")
        
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with aiohttp.ClientSession() as session:
            logging.info(f"[GitHub Download] Sending GET request to GitHub...")
            async with session.get(url, headers=headers) as response:
                logging.info(f"[GitHub Download] Response status: {response.status}")
                
                if response.status == 200:
                    logging.info(f"[GitHub Download] ✓ File found on GitHub")
                    data = await response.json()
                    
                    # Check if content exists
                    if "content" not in data:
                        logging.error(f"[GitHub Download] ✗ No content in response")
                        return False
                    
                    logging.info(f"[GitHub Download] Decoding base64 content...")
                    content = base64.b64decode(data["content"])
                    content_size = len(content)
                    logging.info(f"[GitHub Download] Decoded content size: {content_size} bytes")
                    
                    # Determine file path
                    if local_path:
                        file_path = local_path
                    else:
                        file_name = os.path.basename(repo_path)
                        file_path = os.path.join(os.getcwd(), file_name)
                    
                    logging.info(f"[GitHub Download] Writing to file: {file_path}")
                    
                    # Write content to file
                    with open(file_path, "wb") as file:
                        file.write(content)
                    
                    # Verify file was written
                    if os.path.exists(file_path):
                        written_size = os.path.getsize(file_path)
                        logging.info(f"[GitHub Download] ✓✓✓ SUCCESS! File saved: {file_path}")
                        logging.info(f"[GitHub Download] File size: {written_size} bytes")
                        return True
                    else:
                        logging.error(f"[GitHub Download] ✗ File was not written to disk")
                        return False
                
                elif response.status == 404:
                    logging.info(f"[GitHub Download] ! File not found on GitHub: {repo_path}")
                    logging.info(f"[GitHub Download] This is normal for first-time setup")
                    return False
                else:
                    logging.error(f"[GitHub Download] ✗ Failed to download from GitHub")
                    logging.error(f"[GitHub Download] Status code: {response.status}")
                    try:
                        error_body = await response.text()
                        logging.error(f"[GitHub Download] Response: {error_body[:500]}")
                    except:
                        pass
                    return False
    
    except Exception as e:
        logging.error(f"[GitHub Download] ✗✗✗ EXCEPTION during download: {e}")
        import traceback
        logging.error(f"[GitHub Download] Traceback: {traceback.format_exc()}")
        return False
