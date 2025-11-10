# Authentication system with OTP and session management
import hmac
import hashlib
import secrets
import logging
import time
from typing import Optional, Tuple
from datetime import datetime, timedelta

class AuthSystem:
    """Handle OTP generation, verification, and session management"""
    
    def __init__(self, db_conn):
        self.conn = db_conn
        self.create_tables()
    
    def create_tables(self):
        """Create necessary authentication tables"""
        try:
            cursor = self.conn.cursor()
            
            # Users table - create first as it's referenced by foreign keys
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_user_id BIGINT PRIMARY KEY,
                    first_name TEXT,
                    last_name TEXT,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                );
            """)
            self.conn.commit()
            
            # OTP sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS otp_sessions (
                    id SERIAL PRIMARY KEY,
                    telegram_user_id BIGINT NOT NULL,
                    otp VARCHAR(6) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    verified BOOLEAN DEFAULT FALSE,
                    verified_at TIMESTAMP
                );
            """)
            self.conn.commit()
            
            # Rate limits table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    telegram_user_id BIGINT PRIMARY KEY,
                    hour_count INTEGER DEFAULT 0,
                    day_count INTEGER DEFAULT 0,
                    hour_reset TIMESTAMP,
                    day_reset TIMESTAMP
                );
            """)
            self.conn.commit()
            
            # Login sessions table - create after users table is committed
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS login_sessions (
                    session_token VARCHAR(64) PRIMARY KEY,
                    telegram_user_id BIGINT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            self.conn.commit()
            
            # Add foreign key constraint if it doesn't exist
            try:
                cursor.execute("""
                    DO $$ 
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.table_constraints 
                            WHERE constraint_name = 'login_sessions_telegram_user_id_fkey'
                            AND table_name = 'login_sessions'
                        ) THEN
                            ALTER TABLE login_sessions 
                            ADD CONSTRAINT login_sessions_telegram_user_id_fkey 
                            FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id);
                        END IF;
                    END $$;
                """)
                self.conn.commit()
            except Exception as fk_error:
                logging.warning(f"Foreign key constraint may already exist: {fk_error}")
            
            # Add index for OTP lookup
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_otp_user_verified 
                ON otp_sessions(telegram_user_id, verified);
            """)
            self.conn.commit()
            
            # Add index for session lookup
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_expires 
                ON login_sessions(session_token, expires_at);
            """)
            self.conn.commit()
            
            cursor.close()
            logging.info("Authentication tables created successfully")
            
        except Exception as e:
            logging.error(f"Failed to create auth tables: {e}")
            raise
    
    def generate_otp(self, telegram_user_id: int) -> str:
        """Generate a 6-digit OTP valid for 10 minutes"""
        try:
            # Generate random 6-digit OTP
            otp = str(secrets.randbelow(1000000)).zfill(6)
            
            # Set expiration to 10 minutes from now
            expires_at = datetime.now() + timedelta(minutes=10)
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO otp_sessions (telegram_user_id, otp, expires_at)
                VALUES (%s, %s, %s)
            """, (telegram_user_id, otp, expires_at))
            self.conn.commit()
            cursor.close()
            
            logging.info(f"Generated OTP for user {telegram_user_id}")
            return otp
            
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Failed to generate OTP: {e}")
            raise
    
    def verify_otp(self, telegram_user_id: int, otp: str) -> bool:
        """Verify OTP and mark as used"""
        try:
            cursor = self.conn.cursor()
            
            # Get the latest unverified OTP for this user
            cursor.execute("""
                SELECT id, expires_at FROM otp_sessions
                WHERE telegram_user_id = %s AND otp = %s AND verified = FALSE
                ORDER BY created_at DESC
                LIMIT 1
            """, (telegram_user_id, otp))
            
            result = cursor.fetchone()
            
            if not result:
                logging.warning(f"Invalid OTP for user {telegram_user_id}")
                cursor.close()
                return False
            
            otp_id, expires_at = result
            
            # Check if OTP has expired
            if datetime.now() > expires_at:
                logging.warning(f"Expired OTP for user {telegram_user_id}")
                cursor.close()
                return False
            
            # Mark OTP as verified
            cursor.execute("""
                UPDATE otp_sessions
                SET verified = TRUE, verified_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (otp_id,))
            self.conn.commit()
            
            cursor.close()
            logging.info(f"OTP verified for user {telegram_user_id}")
            return True
            
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Failed to verify OTP: {e}")
            return False
    
    def create_user(self, telegram_user_id: int, first_name: str = None, 
                   last_name: str = None, username: str = None) -> bool:
        """Create or update user record"""
        try:
            cursor = self.conn.cursor()
            
            # Upsert user
            cursor.execute("""
                INSERT INTO users (telegram_user_id, first_name, last_name, username, last_login)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (telegram_user_id) DO UPDATE
                SET first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    username = EXCLUDED.username,
                    last_login = CURRENT_TIMESTAMP
            """, (telegram_user_id, first_name, last_name, username))
            self.conn.commit()
            
            cursor.close()
            logging.info(f"User record created/updated for {telegram_user_id}")
            return True
            
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Failed to create user: {e}")
            return False
    
    def create_session(self, telegram_user_id: int) -> Optional[str]:
        """Create a new session token valid for 7 days"""
        try:
            # Generate secure session token
            session_token = secrets.token_urlsafe(48)
            
            # Set expiration to 7 days from now
            expires_at = datetime.now() + timedelta(days=7)
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO login_sessions (session_token, telegram_user_id, expires_at)
                VALUES (%s, %s, %s)
            """, (session_token, telegram_user_id, expires_at))
            self.conn.commit()
            cursor.close()
            
            logging.info(f"Session created for user {telegram_user_id}")
            return session_token
            
        except Exception as e:
            logging.error(f"Failed to create session: {e}")
            return None
    
    def validate_session(self, session_token: str) -> Optional[int]:
        """Validate session and return telegram_user_id if valid"""
        try:
            cursor = self.conn.cursor()
            
            # Get session and check expiration
            cursor.execute("""
                SELECT telegram_user_id, expires_at FROM login_sessions
                WHERE session_token = %s
            """, (session_token,))
            
            result = cursor.fetchone()
            
            if not result:
                cursor.close()
                return None
            
            telegram_user_id, expires_at = result
            
            # Check if session has expired
            if datetime.now() > expires_at:
                # Delete expired session
                cursor.execute("""
                    DELETE FROM login_sessions WHERE session_token = %s
                """, (session_token,))
                self.conn.commit()
                cursor.close()
                return None
            
            # Update last activity
            cursor.execute("""
                UPDATE login_sessions
                SET last_activity = CURRENT_TIMESTAMP
                WHERE session_token = %s
            """, (session_token,))
            self.conn.commit()
            
            cursor.close()
            return telegram_user_id
            
        except Exception as e:
            logging.error(f"Failed to validate session: {e}")
            return None
    
    def get_user(self, telegram_user_id: int) -> Optional[dict]:
        """Get user information"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT telegram_user_id, first_name, last_name, username, created_at, last_login
                FROM users WHERE telegram_user_id = %s
            """, (telegram_user_id,))
            
            result = cursor.fetchone()
            cursor.close()
            
            if not result:
                return None
            
            return {
                'telegram_user_id': result[0],
                'first_name': result[1],
                'last_name': result[2],
                'username': result[3],
                'created_at': result[4],
                'last_login': result[5]
            }
            
        except Exception as e:
            logging.error(f"Failed to get user: {e}")
            return None
    
    def cleanup_expired_otps(self):
        """Clean up expired OTP records"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                DELETE FROM otp_sessions
                WHERE expires_at < CURRENT_TIMESTAMP
            """)
            deleted = cursor.rowcount
            self.conn.commit()
            cursor.close()
            
            if deleted > 0:
                logging.info(f"Cleaned up {deleted} expired OTP records")
                
        except Exception as e:
            logging.error(f"Failed to cleanup OTPs: {e}")
    
    def cleanup_expired_sessions(self):
        """Clean up expired session records"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                DELETE FROM login_sessions
                WHERE expires_at < CURRENT_TIMESTAMP
            """)
            deleted = cursor.rowcount
            self.conn.commit()
            cursor.close()
            
            if deleted > 0:
                logging.info(f"Cleaned up {deleted} expired session records")
                
        except Exception as e:
            logging.error(f"Failed to cleanup sessions: {e}")


def generate_download_signature(unique_file_id: str, expires_at: int, secret_key: str) -> str:
    """Generate HMAC signature for download link integrity"""
    message = f"{unique_file_id}:{expires_at}"
    signature = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


def verify_download_signature(unique_file_id: str, expires_at: int, 
                              signature: str, secret_key: str) -> bool:
    """Verify download link signature"""
    expected_signature = generate_download_signature(unique_file_id, expires_at, secret_key)
    return hmac.compare_digest(signature, expected_signature)
