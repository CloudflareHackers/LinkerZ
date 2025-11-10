#!/usr/bin/env python3
"""
Clean up orphaned records and add foreign key constraint
"""
import psycopg2
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s] => %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)

DATABASE_URL = "postgresql://ub43lrb060grpj:p6b25662823ff195e64587ea3d463bc0481c6f5d923e27771b1de8534307bf5a9@caq9uabolvh3on.cluster-czz5s0kz4scl.eu-west-1.rds.amazonaws.com:5432/d81se6dparnrca"

def cleanup_and_add_fk():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        logging.info("Cleaning up orphaned records...")
        
        # Check how many orphaned records exist
        cursor.execute("""
            SELECT COUNT(*) FROM login_sessions 
            WHERE telegram_user_id NOT IN (SELECT telegram_user_id FROM users);
        """)
        orphaned_sessions = cursor.fetchone()[0]
        logging.info(f"Found {orphaned_sessions} orphaned session records")
        
        cursor.execute("""
            SELECT COUNT(*) FROM otp_sessions 
            WHERE telegram_user_id NOT IN (SELECT telegram_user_id FROM users);
        """)
        orphaned_otps = cursor.fetchone()[0]
        logging.info(f"Found {orphaned_otps} orphaned OTP records")
        
        # Delete orphaned records
        if orphaned_sessions > 0:
            logging.info("Deleting orphaned session records...")
            cursor.execute("""
                DELETE FROM login_sessions 
                WHERE telegram_user_id NOT IN (SELECT telegram_user_id FROM users);
            """)
            logging.info(f"✓ Deleted {orphaned_sessions} orphaned session records")
        
        if orphaned_otps > 0:
            logging.info("Deleting orphaned OTP records...")
            cursor.execute("""
                DELETE FROM otp_sessions 
                WHERE telegram_user_id NOT IN (SELECT telegram_user_id FROM users);
            """)
            logging.info(f"✓ Deleted {orphaned_otps} orphaned OTP records")
        
        # Now try to add the foreign key constraint
        logging.info("\nAdding foreign key constraint...")
        try:
            cursor.execute("""
                ALTER TABLE login_sessions 
                ADD CONSTRAINT login_sessions_telegram_user_id_fkey 
                FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id);
            """)
            logging.info("✓ Foreign key constraint added successfully")
        except psycopg2.errors.DuplicateObject as e:
            logging.info("✓ Foreign key constraint already exists")
        except Exception as e:
            logging.error(f"Failed to add foreign key: {e}")
            raise
        
        # Verify
        cursor.execute("""
            SELECT 
                tc.constraint_name, 
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name 
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' 
              AND tc.table_name='login_sessions';
        """)
        
        foreign_keys = cursor.fetchall()
        if foreign_keys:
            logging.info(f"\n✓ Foreign key constraints on login_sessions:")
            for fk in foreign_keys:
                logging.info(f"  - {fk[0]}: login_sessions.{fk[1]} -> {fk[2]}.{fk[3]}")
        else:
            logging.warning("\n⚠ No foreign key constraints found on login_sessions")
        
        cursor.close()
        conn.close()
        
        logging.info("\n✅ Cleanup and foreign key setup completed!")
        return True
        
    except Exception as e:
        logging.error(f"\n❌ Operation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = cleanup_and_add_fk()
    sys.exit(0 if success else 1)
