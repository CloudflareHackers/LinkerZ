#!/usr/bin/env python3
"""
Add missing last_login column to users table
"""
import psycopg2
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s] => %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)

DATABASE_URL = "postgresql://ub43lrb060grpj:p6b25662823ff195e64587ea3d463bc0481c6f5d923e27771b1de8534307bf5a9@caq9uabolvh3on.cluster-czz5s0kz4scl.eu-west-1.rds.amazonaws.com:5432/d81se6dparnrca"

def add_last_login_column():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        logging.info("Checking if last_login column exists...")
        
        # Check if column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'last_login';
        """)
        
        exists = cursor.fetchone()
        
        if exists:
            logging.info("✓ last_login column already exists")
        else:
            logging.info("Adding last_login column to users table...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN last_login TIMESTAMP;
            """)
            logging.info("✓ last_login column added successfully")
        
        # Verify all columns
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        logging.info("\nUsers table columns:")
        for col in columns:
            logging.info(f"  - {col[0]} ({col[1]})")
        
        cursor.close()
        conn.close()
        
        logging.info("\n✅ Schema update completed!")
        return True
        
    except Exception as e:
        logging.error(f"\n❌ Failed to add column: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = add_last_login_column()
    sys.exit(0 if success else 1)
