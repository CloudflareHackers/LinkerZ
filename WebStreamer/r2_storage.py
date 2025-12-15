# R2 Storage Integration Module - Simplified for Direct Streaming
import requests
import logging
from typing import Optional, Dict
from .vars import Var

class R2Storage:
    """Handler for Cloudflare R2 storage operations - metadata only"""
    
    def __init__(self):
        self.r2_domain = Var.R2_Domain
        self.r2_folder = Var.R2_Folder
        self.r2_public = Var.R2_Public
        
    def get_file_metadata(self, unique_file_id: str) -> Optional[Dict]:
        """
        Get file metadata from R2 storage
        
        Args:
            unique_file_id: Unique file identifier
            
        Returns:
            Dict with file metadata if exists, None otherwise
        """
        try:
            # Build R2 public URL
            url = f"https://{self.r2_public}/{self.r2_folder}/{unique_file_id}.json"
            
            # Make GET request
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                # File exists, parse and return JSON data
                file_data = response.json()
                logging.info(f"File metadata found in R2: {unique_file_id}")
                return file_data
            elif response.status_code == 404:
                # File doesn't exist
                logging.info(f"File metadata not found in R2: {unique_file_id}")
                return None
            else:
                logging.warning(f"Unexpected R2 status code {response.status_code} for {unique_file_id}")
                return None
                
        except requests.exceptions.Timeout:
            logging.error(f"Timeout checking R2 for {unique_file_id}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Error checking R2 for {unique_file_id}: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error checking R2: {e}")
            return None
    
    def upload_file_metadata(self, unique_file_id: str, file_data: Dict) -> bool:
        """
        Upload file metadata to R2 storage
        
        Args:
            unique_file_id: Unique file identifier
            file_data: Dictionary containing file metadata
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            # Build R2 upload URL
            url = f"https://{self.r2_domain}/tga-r2/{self.r2_folder}?id={unique_file_id}"
            
            # Make PUT request with JSON data
            response = requests.put(
                url,
                json=file_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                logging.info(f"Successfully uploaded metadata to R2: {unique_file_id}")
                return True
            else:
                logging.error(f"Failed to upload to R2. Status: {response.status_code}, Response: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logging.error(f"Timeout uploading to R2 for {unique_file_id}")
            return False
        except requests.exceptions.RequestException as e:
            logging.error(f"Error uploading to R2 for {unique_file_id}: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error uploading to R2: {e}")
            return False
    
    def format_file_metadata(self, unique_file_id: str, bot_user_id: int, file_id: str,
                        file_name: str, file_size: int, mime_type: str,
                        message_id: int, channel_id: int) -> Dict:
        """
        Format file metadata for R2 storage with bot_file_ids structure (for compatibility)
        
        Args:
            unique_file_id: Unique file identifier
            bot_user_id: Telegram bot's user ID
            file_id: Telegram file ID
            file_name: Name of the file
            file_size: File size in bytes
            mime_type: MIME type
            message_id: Original message ID
            channel_id: Source channel ID
            
        Returns:
            Formatted dictionary ready for R2 upload (compatible with old format)
        """
        # Format: b_{bot_telegram_id}_file_id for compatibility
        bot_key = f"b_{bot_user_id}_file_id"
        
        return {
            "unique_id": unique_file_id,
            "bot_file_ids": {
                bot_key: file_id
            },
            "file_name": file_name,
            "file_size_bytes": file_size,
            "mime_type": mime_type,
            "original_message_id": message_id,
            "source_channel_id": channel_id
        }

# Global R2 storage instance
r2_storage_instance = None

def get_r2_storage() -> R2Storage:
    """Get or create R2 storage instance"""
    global r2_storage_instance
    if r2_storage_instance is None:
        r2_storage_instance = R2Storage()
    return r2_storage_instance
