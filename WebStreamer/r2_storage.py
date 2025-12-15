# R2 Storage Integration Module - Simplified for Direct Streaming
# Using disk-based caching instead of in-memory (Heroku clears on restart)
import requests
import logging
import time
import threading
import os
import json
from typing import Optional, Dict
from .vars import Var

# Disk cache directory (ephemeral on Heroku - cleared on restart)
CACHE_DIR = "/tmp/r2_cache"

class R2Storage:
    """Handler for Cloudflare R2 storage operations - metadata only"""
    
    # Cache TTL in seconds (5 minutes)
    CACHE_TTL = 300
    # Recently uploaded files TTL (60 seconds) - skip R2 check for recently uploaded
    UPLOAD_TTL = 60
    
    def __init__(self):
        self.r2_domain = Var.R2_Domain
        self.r2_folder = Var.R2_Folder
        self.r2_public = Var.R2_Public
        # Lock for thread-safe cache operations
        self._cache_lock = threading.Lock()
        # Ensure cache directory exists
        self._ensure_cache_dir()
        
    def _ensure_cache_dir(self):
        """Ensure cache directory exists"""
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            os.makedirs(os.path.join(CACHE_DIR, "recent"), exist_ok=True)
            logging.info(f"Disk cache directory ready: {CACHE_DIR}")
        except Exception as e:
            logging.error(f"Failed to create cache directory: {e}")
    
    def _get_cache_path(self, unique_file_id: str, recent: bool = False) -> str:
        """Get the file path for a cached file"""
        subdir = "recent" if recent else ""
        return os.path.join(CACHE_DIR, subdir, f"{unique_file_id}.json")
    
    def _read_cache_file(self, filepath: str, ttl: int) -> Optional[Dict]:
        """Read and validate cache file"""
        try:
            if not os.path.exists(filepath):
                return None
            
            # Check if file is expired based on modification time
            file_mtime = os.path.getmtime(filepath)
            if time.time() - file_mtime > ttl:
                # Expired, remove it
                try:
                    os.remove(filepath)
                except:
                    pass
                return None
            
            # Read and parse JSON
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.debug(f"Error reading cache file {filepath}: {e}")
            return None
    
    def _write_cache_file(self, filepath: str, data: Dict):
        """Write data to cache file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception as e:
            logging.debug(f"Error writing cache file {filepath}: {e}")
        
    def _get_from_cache(self, unique_file_id: str) -> Optional[Dict]:
        """Get file metadata from disk cache if not expired"""
        with self._cache_lock:
            # Check recently uploaded first (higher priority)
            recent_path = self._get_cache_path(unique_file_id, recent=True)
            data = self._read_cache_file(recent_path, self.UPLOAD_TTL)
            if data:
                logging.debug(f"Disk cache hit (recently uploaded): {unique_file_id}")
                return data
            
            # Check regular cache
            cache_path = self._get_cache_path(unique_file_id, recent=False)
            data = self._read_cache_file(cache_path, self.CACHE_TTL)
            if data:
                logging.debug(f"Disk cache hit: {unique_file_id}")
                return data
        
        return None
    
    def _set_cache(self, unique_file_id: str, data: Dict, is_upload: bool = False):
        """Set file metadata in disk cache"""
        with self._cache_lock:
            # Write to main cache
            cache_path = self._get_cache_path(unique_file_id, recent=False)
            self._write_cache_file(cache_path, data)
            
            # Also write to recent cache if upload
            if is_upload:
                recent_path = self._get_cache_path(unique_file_id, recent=True)
                self._write_cache_file(recent_path, data)
    
    def is_recently_uploaded(self, unique_file_id: str) -> bool:
        """Check if file was recently uploaded (skip redundant checks)"""
        with self._cache_lock:
            recent_path = self._get_cache_path(unique_file_id, recent=True)
            if os.path.exists(recent_path):
                file_mtime = os.path.getmtime(recent_path)
                return time.time() - file_mtime < self.UPLOAD_TTL
        return False
    
    def get_cached_data(self, unique_file_id: str) -> Optional[Dict]:
        """Get cached data without making R2 request"""
        return self._get_from_cache(unique_file_id)
        
    def get_file_metadata(self, unique_file_id: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Get file metadata from R2 storage
        
        Args:
            unique_file_id: Unique file identifier
            use_cache: If True, check cache first (default True)
            
        Returns:
            Dict with file metadata if exists, None otherwise
        """
        try:
            # Check cache first
            if use_cache:
                cached_data = self._get_from_cache(unique_file_id)
                if cached_data is not None:
                    return cached_data
            
            # Build R2 public URL
            url = f"https://{self.r2_public}/{self.r2_folder}/{unique_file_id}.json"
            
            # Make GET request
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                # File exists, parse and return JSON data
                file_data = response.json()
                logging.info(f"File metadata found in R2: {unique_file_id}")
                # Cache the result
                self._set_cache(unique_file_id, file_data)
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
                # Cache the uploaded data immediately (mark as recently uploaded)
                self._set_cache(unique_file_id, file_data, is_upload=True)
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
                        message_id: int, channel_id: int, caption: str = None,
                        file_type: str = None, video_duration: int = None,
                        video_width: int = None, video_height: int = None,
                        existing_data: Dict = None) -> Dict:
        """
        Format file metadata for R2 storage with complete structure
        Merges with existing data if provided
        
        Args:
            unique_file_id: Unique file identifier
            bot_user_id: Telegram bot's user ID (used as key in bot_file_ids)
            file_id: Telegram file ID
            file_name: Name of the file
            file_size: File size in bytes
            mime_type: MIME type
            message_id: Original message ID
            channel_id: Source channel ID
            caption: Message caption (optional)
            file_type: Type of file - "video", "audio", or "document" (optional)
            video_duration: Video duration in seconds (optional, for videos)
            video_width: Video width in pixels (optional, for videos)
            video_height: Video height in pixels (optional, for videos)
            existing_data: Existing R2 data to merge with (optional)
            
        Returns:
            Formatted dictionary ready for R2 upload
        """
        # Start with existing data if available, otherwise create new
        if existing_data:
            data = existing_data.copy()
            # Merge bot_file_ids - keep existing ones and add new
            if "bot_file_ids" not in data:
                data["bot_file_ids"] = {}
            data["bot_file_ids"][str(bot_user_id)] = file_id
        else:
            data = {
                "unique_id": unique_file_id,
                "bot_file_ids": {
                    str(bot_user_id): file_id
                },
                "file_name": file_name,
                "file_size_bytes": file_size,
                "mime_type": mime_type,
                "original_message_id": message_id,
                "source_channel_id": channel_id
            }
            
            # Add optional fields if provided
            if caption:
                data["caption"] = caption
                
            if file_type:
                data["file_type"] = file_type
                
            # Add video-specific metadata if available
            if video_duration is not None:
                data["video_duration_seconds"] = video_duration
            if video_width is not None:
                data["video_width"] = video_width
            if video_height is not None:
                data["video_height"] = video_height
            
        return data

# Global R2 storage instance
r2_storage_instance = None

def get_r2_storage() -> R2Storage:
    """Get or create R2 storage instance"""
    global r2_storage_instance
    if r2_storage_instance is None:
        r2_storage_instance = R2Storage()
    return r2_storage_instance
