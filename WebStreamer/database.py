# Database module for PostgreSQL operations
import psycopg2
import logging
import random
from typing import Optional, Dict, List
from .vars import Var
from os import environ
from .auth import AuthSystem
from .rate_limiter import RateLimiter

class Database:
    def __init__(self):
        self.db_url = environ.get("DATABASE_URL")
        if not self.db_url:
            logging.error("DATABASE_URL not found in environment variables")
            raise ValueError("DATABASE_URL is required")
        
        self.conn = None
        self.auth = None
        self.rate_limiter = None
        self.connect()
        self.create_table()
        self.initialize_auth_system()
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(self.db_url)
            # Don't use autocommit for table creation, manual commits give better control
            self.conn.autocommit = False
            logging.info("Successfully connected to PostgreSQL database")
        except Exception as e:
            logging.error(f"Failed to connect to database: {e}")
            raise
    
    def create_table(self):
        """Create the media_files table if it doesn't exist"""
        try:
            cursor = self.conn.cursor()
            create_table_query = """
            CREATE TABLE IF NOT EXISTS media_files (
                unique_file_id TEXT PRIMARY KEY,
                b_1 TEXT,
                b_2 TEXT,
                b_3 TEXT,
                b_4 TEXT,
                b_5 TEXT,
                b_6 TEXT,
                b_7 TEXT,
                b_8 TEXT,
                b_9 TEXT,
                b_10 TEXT,
                b_11 TEXT,
                file_name TEXT,
                file_size BIGINT,
                mime_type TEXT,
                dc_id INTEGER,
                channel_id BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cursor.execute(create_table_query)
            self.conn.commit()
            
            # Add columns if they don't exist (for existing databases)
            try:
                cursor.execute("ALTER TABLE media_files ADD COLUMN IF NOT EXISTS dc_id INTEGER;")
                cursor.execute("ALTER TABLE media_files ADD COLUMN IF NOT EXISTS channel_id BIGINT;")
                self.conn.commit()
            except Exception as alter_error:
                self.conn.rollback()
                logging.warning(f"Could not alter table: {alter_error}")
            
            cursor.close()
            logging.info("Table 'media_files' is ready")
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Failed to create table: {e}")
            raise
    
    def store_file(self, unique_file_id: str, bot_index: int, file_id: str, 
                   file_name: str = None, file_size: int = None, mime_type: str = None,
                   dc_id: int = None, channel_id: int = None):
        """
        Store or update file information
        
        Args:
            unique_file_id: Unique file identifier from Telegram
            bot_index: Bot number (0-10, maps to b_1 to b_11)
            file_id: File ID from the specific bot
            file_name: Name of the file
            file_size: Size of the file in bytes
            mime_type: MIME type of the file
            dc_id: Telegram DC ID where file is stored
            channel_id: Channel ID where file was posted
        """
        try:
            cursor = self.conn.cursor()
            
            # Validate bot_index
            if bot_index < 0 or bot_index > 10:
                logging.error(f"Invalid bot_index: {bot_index}. Must be between 0 and 10")
                return False
            
            bot_column = f"b_{bot_index + 1}"
            
            # Check if file already exists
            cursor.execute(
                "SELECT unique_file_id FROM media_files WHERE unique_file_id = %s",
                (unique_file_id,)
            )
            exists = cursor.fetchone()
            
            if exists:
                # Update existing record
                update_query = f"""
                UPDATE media_files 
                SET {bot_column} = %s, updated_at = CURRENT_TIMESTAMP
                WHERE unique_file_id = %s
                """
                cursor.execute(update_query, (file_id, unique_file_id))
                self.conn.commit()
                logging.info(f"Updated file {unique_file_id} with {bot_column} = {file_id}")
            else:
                # Insert new record
                insert_query = f"""
                INSERT INTO media_files 
                (unique_file_id, {bot_column}, file_name, file_size, mime_type, dc_id, channel_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (unique_file_id, file_id, file_name, file_size, mime_type, dc_id, channel_id))
                self.conn.commit()
                logging.info(f"Inserted new file {unique_file_id} with {bot_column} = {file_id}")
            
            cursor.close()
            return True
            
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Failed to store file: {e}")
            return False
    
    def get_file_ids(self, unique_file_id: str) -> Optional[Dict]:
        """
        Get all file_ids and metadata for a unique_file_id
        
        Returns:
            Dictionary with bot file_ids and metadata, or None if not found
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT b_1, b_2, b_3, b_4, b_5, b_6, b_7, b_8, b_9, b_10, b_11,
                       file_name, file_size, mime_type, dc_id, channel_id
                FROM media_files WHERE unique_file_id = %s
                """,
                (unique_file_id,)
            )
            result = cursor.fetchone()
            cursor.close()
            
            if not result:
                logging.warning(f"File not found: {unique_file_id}")
                return None
            
            # Build response dictionary
            file_data = {
                'bot_file_ids': {},
                'file_name': result[11],
                'file_size': result[12],
                'mime_type': result[13],
                'dc_id': result[14],
                'channel_id': result[15]
            }
            
            # Collect non-null file_ids
            for i in range(11):
                if result[i]:
                    file_data['bot_file_ids'][i] = result[i]
            
            return file_data
            
        except Exception as e:
            logging.error(f"Failed to get file_ids: {e}")
            return None
    
    def get_random_file_id(self, unique_file_id: str) -> Optional[tuple]:
        """
        Get a random available file_id for streaming
        
        Returns:
            Tuple of (bot_index, file_id) or None if not found
        """
        file_data = self.get_file_ids(unique_file_id)
        if not file_data or not file_data['bot_file_ids']:
            return None
        
        # Get random bot_index from available file_ids
        available_bots = list(file_data['bot_file_ids'].keys())
        bot_index = random.choice(available_bots)
        file_id = file_data['bot_file_ids'][bot_index]
        
        logging.info(f"Selected bot {bot_index + 1} for streaming {unique_file_id}")
        return (bot_index, file_id)
    
    def get_all_files(self, search_query: str = None, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Get all files from database with optional search
        
        Args:
            search_query: Optional filename search string
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            List of dictionaries with file information
        """
        try:
            cursor = self.conn.cursor()
            
            if search_query:
                # Search by filename
                query = """
                SELECT unique_file_id, file_name, file_size, mime_type, created_at, updated_at
                FROM media_files
                WHERE file_name ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """
                cursor.execute(query, (f"%{search_query}%", limit, offset))
            else:
                # Get all files
                query = """
                SELECT unique_file_id, file_name, file_size, mime_type, created_at, updated_at
                FROM media_files
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """
                cursor.execute(query, (limit, offset))
            
            results = cursor.fetchall()
            cursor.close()
            
            # Convert to list of dictionaries
            files = []
            for row in results:
                files.append({
                    'unique_file_id': row[0],
                    'file_name': row[1],
                    'file_size': row[2],
                    'mime_type': row[3],
                    'created_at': row[4],
                    'updated_at': row[5]
                })
            
            return files
            
        except Exception as e:
            logging.error(f"Failed to get files: {e}")
            return []
    
    def get_file_count(self, search_query: str = None) -> int:
        """
        Get total count of files
        
        Args:
            search_query: Optional filename search string
            
        Returns:
            Total number of files
        """
        try:
            cursor = self.conn.cursor()
            
            if search_query:
                query = "SELECT COUNT(*) FROM media_files WHERE file_name ILIKE %s"
                cursor.execute(query, (f"%{search_query}%",))
            else:
                query = "SELECT COUNT(*) FROM media_files"
                cursor.execute(query)
            
            count = cursor.fetchone()[0]
            cursor.close()
            return count
            
        except Exception as e:
            logging.error(f"Failed to get file count: {e}")
            return 0
    
    def initialize_auth_system(self):
        """Initialize authentication and rate limiting systems"""
        try:
            self.auth = AuthSystem(self.conn)
            self.rate_limiter = RateLimiter(self.conn)
            logging.info("Authentication system initialized")
        except Exception as e:
            logging.error(f"Failed to initialize auth system: {e}")
            raise
    
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
