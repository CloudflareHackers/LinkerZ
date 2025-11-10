#!/usr/bin/env python3
"""
Fix database schema - rename users.id to users.telegram_user_id
"""
import psycopg2
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s] => %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)

DATABASE_URL = "postgresql://ub43lrb060grpj:p6b25662823ff195e64587ea3d463bc0481c6f5d923e27771b1de8534307bf5a9@caq9uabolvh3on.cluster-czz5s0kz4scl.eu-west-1.rds.amazonaws.com:5432/d81se6dparnrca"

def fix_schema():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        logging.info("Fixing database schema...")
        
        # Step 1: Check if users table has 'id' column
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'id';
        """)
        has_id = cursor.fetchone()
        
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'telegram_user_id';
        """)
        has_telegram_user_id = cursor.fetchone()
        
        if has_id and not has_telegram_user_id:
            logging.info("Found users.id column, need to rename to telegram_user_id")
            
            # Drop any existing foreign key constraints first
            logging.info("Dropping existing foreign key constraints...")
            cursor.execute("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'login_sessions' AND constraint_type = 'FOREIGN KEY';
            """)
            constraints = cursor.fetchall()
            for constraint in constraints:
                logging.info(f"  Dropping constraint: {constraint[0]}")
                cursor.execute(f"ALTER TABLE login_sessions DROP CONSTRAINT IF EXISTS {constraint[0]} CASCADE;")
            
            # Rename the column
            logging.info("Renaming users.id to users.telegram_user_id...")
            cursor.execute("""
                ALTER TABLE users RENAME COLUMN id TO telegram_user_id;
            """)
            logging.info("✓ Column renamed successfully")
            
            # Recreate the foreign key constraint
            logging.info("Adding foreign key constraint...")
            cursor.execute("""
                ALTER TABLE login_sessions 
                ADD CONSTRAINT login_sessions_telegram_user_id_fkey 
                FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id);
            """)
            logging.info("✓ Foreign key constraint added")
            
        elif has_telegram_user_id:
            logging.info("✓ users.telegram_user_id column already exists")
            
            # Just make sure foreign key exists
            cursor.execute("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'login_sessions' 
                  AND constraint_type = 'FOREIGN KEY'
                  AND constraint_name = 'login_sessions_telegram_user_id_fkey';
            """)
            fk_exists = cursor.fetchone()
            
            if not fk_exists:
                logging.info("Adding missing foreign key constraint...")
                try:
                    cursor.execute("""
                        ALTER TABLE login_sessions 
                        ADD CONSTRAINT login_sessions_telegram_user_id_fkey 
                        FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id);
                    """)
                    logging.info("✓ Foreign key constraint added")
                except Exception as e:
                    logging.warning(f"Could not add foreign key (may already exist): {e}")
        else:
            logging.error("Unexpected schema state")
        
        # Verify the fix
        logging.info("\nVerifying schema...")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name IN ('id', 'telegram_user_id');
        """)
        columns = cursor.fetchall()
        for col in columns:
            logging.info(f"  users.{col[0]} ({col[1]})")
        
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
        
        logging.info("\n✅ Schema fix completed successfully!")
        return True
        
    except Exception as e:
        logging.error(f"\n❌ Schema fix failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = fix_schema()
    sys.exit(0 if success else 1)
