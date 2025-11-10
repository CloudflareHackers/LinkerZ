#!/usr/bin/env python3
"""
Final verification of database fix
"""
import psycopg2
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s] => %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)

DATABASE_URL = "postgresql://ub43lrb060grpj:p6b25662823ff195e64587ea3d463bc0481c6f5d923e27771b1de8534307bf5a9@caq9uabolvh3on.cluster-czz5s0kz4scl.eu-west-1.rds.amazonaws.com:5432/d81se6dparnrca"

def verify_all():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        logging.info("=" * 60)
        logging.info("FINAL DATABASE VERIFICATION")
        logging.info("=" * 60)
        
        # Check 1: users table has telegram_user_id column
        logging.info("\n1. Checking users.telegram_user_id column...")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'telegram_user_id';
        """)
        result = cursor.fetchone()
        if result:
            logging.info(f"   ✅ users.telegram_user_id exists ({result[1]})")
        else:
            logging.error("   ❌ users.telegram_user_id NOT FOUND")
            return False
        
        # Check 2: users table has last_login column
        logging.info("\n2. Checking users.last_login column...")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'last_login';
        """)
        result = cursor.fetchone()
        if result:
            logging.info(f"   ✅ users.last_login exists ({result[1]})")
        else:
            logging.error("   ❌ users.last_login NOT FOUND")
            return False
        
        # Check 3: login_sessions has telegram_user_id column
        logging.info("\n3. Checking login_sessions.telegram_user_id column...")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'login_sessions' AND column_name = 'telegram_user_id';
        """)
        result = cursor.fetchone()
        if result:
            logging.info(f"   ✅ login_sessions.telegram_user_id exists ({result[1]})")
        else:
            logging.error("   ❌ login_sessions.telegram_user_id NOT FOUND")
            return False
        
        # Check 4: Foreign key constraint exists
        logging.info("\n4. Checking foreign key constraint...")
        cursor.execute("""
            SELECT constraint_name, table_name
            FROM information_schema.table_constraints 
            WHERE table_name = 'login_sessions' 
              AND constraint_type = 'FOREIGN KEY'
              AND constraint_name = 'login_sessions_telegram_user_id_fkey';
        """)
        result = cursor.fetchone()
        if result:
            logging.info(f"   ✅ Foreign key constraint exists: {result[0]}")
        else:
            logging.warning("   ⚠️  Foreign key constraint not found (optional)")
        
        # Check 5: All required tables exist
        logging.info("\n5. Checking all required tables...")
        required_tables = ['users', 'login_sessions', 'otp_sessions', 'rate_limits', 'media_files']
        for table_name in required_tables:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                );
            """, (table_name,))
            exists = cursor.fetchone()[0]
            if exists:
                logging.info(f"   ✅ Table '{table_name}' exists")
            else:
                logging.error(f"   ❌ Table '{table_name}' NOT FOUND")
                return False
        
        # Check 6: Test a simple insert/delete operation
        logging.info("\n6. Testing database write operations...")
        try:
            test_user_id = 999999999
            
            # Try to insert a test user
            cursor.execute("""
                INSERT INTO users (telegram_user_id, first_name, last_name, username, last_login)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (telegram_user_id) DO UPDATE
                SET last_login = CURRENT_TIMESTAMP;
            """, (test_user_id, "Test", "User", "testuser"))
            
            # Delete the test user
            cursor.execute("DELETE FROM users WHERE telegram_user_id = %s;", (test_user_id,))
            
            logging.info("   ✅ Write operations working correctly")
        except Exception as e:
            logging.error(f"   ❌ Write operations failed: {e}")
            return False
        
        cursor.close()
        conn.close()
        
        logging.info("\n" + "=" * 60)
        logging.info("✅ ALL CHECKS PASSED - DATABASE IS READY")
        logging.info("=" * 60)
        return True
        
    except Exception as e:
        logging.error(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = verify_all()
    sys.exit(0 if success else 1)
