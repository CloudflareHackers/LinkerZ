#!/usr/bin/env python3
"""
Inspect database schema
"""
import psycopg2
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s] => %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)

DATABASE_URL = "postgresql://ub43lrb060grpj:p6b25662823ff195e64587ea3d463bc0481c6f5d923e27771b1de8534307bf5a9@caq9uabolvh3on.cluster-czz5s0kz4scl.eu-west-1.rds.amazonaws.com:5432/d81se6dparnrca"

def inspect_schema():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public';
        """)
        tables = cursor.fetchall()
        
        logging.info(f"Found {len(tables)} tables:")
        for table in tables:
            logging.info(f"  - {table[0]}")
        
        # Check columns for key tables
        for table_name in ['users', 'login_sessions', 'otp_sessions', 'rate_limits']:
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))
            
            columns = cursor.fetchall()
            if columns:
                logging.info(f"\nTable '{table_name}' columns:")
                for col in columns:
                    logging.info(f"  - {col[0]} ({col[1]}, nullable={col[2]})")
            else:
                logging.info(f"\nTable '{table_name}' does not exist")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_schema()
