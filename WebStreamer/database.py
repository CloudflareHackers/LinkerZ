# Simplified Database module for PostgreSQL operations
import psycopg2
import logging
import random
from typing import Optional, Dict, List
from .vars import Var
from os import environ

class Database:
    def __init__(self):
        self.db_url = environ.get("DATABASE_URL")
        if not self.db_url:
            logging.error("DATABASE_URL not found in environment variables")
            raise ValueError("DATABASE_URL is required")
        
        self.conn = None
        self.connect()
        self.create_table()
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.conn.autocommit = False
            logging.info("Successfully connected to PostgreSQL database")
        except Exception as e:
            logging.error(f"Failed to connect to database: {e}")
            raise
    
    def create_table(self):
        """Create the simplified media_files table if it doesn't exist"""
        try:
            cursor = self.conn.cursor()
            create_table_query = """
            CREATE TABLE IF NOT EXISTS media_files (
                unique_file_id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                file_name TEXT,
                file_size BIGINT,
                mime_type TEXT,
                channel_id BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cursor.execute(create_table_query)
            self.conn.commit()
            cursor.close()
            logging.info("Table 'media_files' is ready")
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Failed to create table: {e}")
            raise
    
    def store_file(self, unique_file_id: str, file_id: str, 
                   file_name: str = None, file_size: int = None, mime_type: str = None,
                   channel_id: int = None):
        """
        Store or update file information
        
        Args:
            unique_file_id: Unique file identifier from Telegram
            file_id: Telegram file ID
            file_name: Name of the file
            file_size: Size of the file in bytes
            mime_type: MIME type of the file
            channel_id: Channel ID where file was posted
        """
        try:
            cursor = self.conn.cursor()
            
            # Check if file already exists
            cursor.execute(
                "SELECT unique_file_id FROM media_files WHERE unique_file_id = %s",
                (unique_file_id,)
            )
            exists = cursor.fetchone()
            
            if exists:
                # Update existing record
                update_query = """
                UPDATE media_files 
                SET file_id = %s, file_name = %s, file_size = %s, mime_type = %s, channel_id = %s
                WHERE unique_file_id = %s
                """
                cursor.execute(update_query, (file_id, file_name, file_size, mime_type, channel_id, unique_file_id))
                self.conn.commit()
                logging.info(f"Updated file {unique_file_id}")
            else:
                # Insert new record
                insert_query = """
                INSERT INTO media_files 
                (unique_file_id, file_id, file_name, file_size, mime_type, channel_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (unique_file_id, file_id, file_name, file_size, mime_type, channel_id))
                self.conn.commit()
                logging.info(f"Inserted new file {unique_file_id}")
            
            cursor.close()
            return True
            
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Failed to store file: {e}")
            return False
    
    def get_file_info(self, unique_file_id: str) -> Optional[Dict]:
        """
        Get file information by unique_file_id
        
        Returns:
            Dictionary with file information, or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT file_id, file_name, file_size, mime_type, channel_id
                FROM media_files WHERE unique_file_id = %s
                """,
                (unique_file_id,)
            )
            result = cursor.fetchone()
            cursor.close()
            
            if not result:
                logging.warning(f"File not found: {unique_file_id}")
                return None
            
            return {
                'file_id': result[0],
                'file_name': result[1],
                'file_size': result[2],
                'mime_type': result[3],
                'channel_id': result[4]
            }
            
        except Exception as e:
            logging.error(f"Failed to get file info: {e}")
            return None
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logging.info("Database connection closed")

# Global database instance
db_instance = None

def get_database() -> Database:
    """Get or create database instance"""
    global db_instance
    if db_instance is None:
        db_instance = Database()
    return db_instance
