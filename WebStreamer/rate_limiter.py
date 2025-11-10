# Rate limiting system for download links
import logging
from datetime import datetime, timedelta
from typing import Tuple

class RateLimiter:
    """Handle rate limiting for download link generation"""
    
    # Limits
    HOUR_LIMIT = 10
    DAY_LIMIT = 50
    
    def __init__(self, db_conn):
        self.conn = db_conn
    
    def check_and_increment(self, telegram_user_id: int) -> Tuple[bool, str]:
        """
        Check if user is within limits and increment counters
        
        Returns:
            (allowed: bool, message: str)
        """
        try:
            cursor = self.conn.cursor()
            
            # Get or create rate limit record
            cursor.execute("""
                SELECT hour_count, day_count, hour_reset, day_reset
                FROM rate_limits WHERE telegram_user_id = %s
            """, (telegram_user_id,))
            
            result = cursor.fetchone()
            
            current_time = datetime.now()
            
            if not result:
                # Create new rate limit record
                hour_reset = current_time + timedelta(hours=1)
                day_reset = current_time + timedelta(days=1)
                
                cursor.execute("""
                    INSERT INTO rate_limits 
                    (telegram_user_id, hour_count, day_count, hour_reset, day_reset)
                    VALUES (%s, 1, 1, %s, %s)
                """, (telegram_user_id, hour_reset, day_reset))
                
                cursor.close()
                logging.info(f"Created rate limit record for user {telegram_user_id}")
                return (True, "Link generated successfully")
            
            hour_count, day_count, hour_reset, day_reset = result
            
            # Reset hour counter if time has passed
            if current_time >= hour_reset:
                hour_count = 0
                hour_reset = current_time + timedelta(hours=1)
            
            # Reset day counter if time has passed
            if current_time >= day_reset:
                day_count = 0
                day_reset = current_time + timedelta(days=1)
            
            # Check limits
            if hour_count >= self.HOUR_LIMIT:
                cursor.close()
                minutes_left = int((hour_reset - current_time).total_seconds() / 60)
                return (False, f"Hourly limit reached ({self.HOUR_LIMIT}/hour). Try again in {minutes_left} minutes.")
            
            if day_count >= self.DAY_LIMIT:
                cursor.close()
                hours_left = int((day_reset - current_time).total_seconds() / 3600)
                return (False, f"Daily limit reached ({self.DAY_LIMIT}/day). Try again in {hours_left} hours.")
            
            # Increment counters
            cursor.execute("""
                UPDATE rate_limits
                SET hour_count = %s, day_count = %s, hour_reset = %s, day_reset = %s
                WHERE telegram_user_id = %s
            """, (hour_count + 1, day_count + 1, hour_reset, day_reset, telegram_user_id))
            
            cursor.close()
            
            remaining_hour = self.HOUR_LIMIT - (hour_count + 1)
            remaining_day = self.DAY_LIMIT - (day_count + 1)
            
            logging.info(f"Rate limit check passed for user {telegram_user_id}. Remaining: {remaining_hour}/hour, {remaining_day}/day")
            return (True, f"Link generated. Remaining: {remaining_hour}/hour, {remaining_day}/day")
            
        except Exception as e:
            logging.error(f"Rate limit check failed: {e}")
            # Fail open - allow the request if rate limiting fails
            return (True, "Link generated (rate limit check skipped)")
    
    def get_limits(self, telegram_user_id: int) -> dict:
        """Get current rate limit status for user"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT hour_count, day_count, hour_reset, day_reset
                FROM rate_limits WHERE telegram_user_id = %s
            """, (telegram_user_id,))
            
            result = cursor.fetchone()
            cursor.close()
            
            if not result:
                return {
                    'hour_used': 0,
                    'hour_limit': self.HOUR_LIMIT,
                    'day_used': 0,
                    'day_limit': self.DAY_LIMIT,
                    'hour_resets_in': 60,
                    'day_resets_in': 1440
                }
            
            hour_count, day_count, hour_reset, day_reset = result
            current_time = datetime.now()
            
            # Calculate time until reset
            hour_minutes = max(0, int((hour_reset - current_time).total_seconds() / 60))
            day_minutes = max(0, int((day_reset - current_time).total_seconds() / 60))
            
            # Reset counts if time has passed
            if current_time >= hour_reset:
                hour_count = 0
                hour_minutes = 60
            
            if current_time >= day_reset:
                day_count = 0
                day_minutes = 1440
            
            return {
                'hour_used': hour_count,
                'hour_limit': self.HOUR_LIMIT,
                'day_used': day_count,
                'day_limit': self.DAY_LIMIT,
                'hour_resets_in': hour_minutes,
                'day_resets_in': day_minutes
            }
            
        except Exception as e:
            logging.error(f"Failed to get rate limits: {e}")
            return {
                'hour_used': 0,
                'hour_limit': self.HOUR_LIMIT,
                'day_used': 0,
                'day_limit': self.DAY_LIMIT,
                'hour_resets_in': 60,
                'day_resets_in': 1440
            }
