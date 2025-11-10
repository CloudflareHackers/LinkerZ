#!/usr/bin/env python3
"""
Test script for file viewer functionality
This adds sample data to demonstrate the /files viewer
"""

import os
import psycopg2
from datetime import datetime

DATABASE_URL = 'postgresql://ub43lrb060grpj:p6b25662823ff195e64587ea3d463bc0481c6f5d923e27771b1de8534307bf5a9@caq9uabolvh3on.cluster-czz5s0kz4scl.eu-west-1.rds.amazonaws.com:5432/d81se6dparnrca'

def add_test_data():
    """Add sample files to database for testing"""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()
    
    print("🔗 Connected to database")
    
    # Sample test data
    test_files = [
        {
            'unique_file_id': 'AgADTest001',
            'b_1': 'BQAD_test_file_001',
            'file_name': 'sample_video.mp4',
            'file_size': 15728640,  # 15 MB
            'mime_type': 'video/mp4'
        },
        {
            'unique_file_id': 'AgADTest002',
            'b_1': 'BQAD_test_file_002',
            'file_name': 'audio_track.mp3',
            'file_size': 5242880,  # 5 MB
            'mime_type': 'audio/mpeg'
        },
        {
            'unique_file_id': 'AgADTest003',
            'b_1': 'BQAD_test_file_003',
            'file_name': 'document.pdf',
            'file_size': 2097152,  # 2 MB
            'mime_type': 'application/pdf'
        }
    ]
    
    print("\n📝 Adding test data...")
    for file in test_files:
        try:
            # Check if file already exists
            cursor.execute(
                "SELECT unique_file_id FROM media_files WHERE unique_file_id = %s",
                (file['unique_file_id'],)
            )
            exists = cursor.fetchone()
            
            if not exists:
                insert_query = """
                INSERT INTO media_files 
                (unique_file_id, b_1, file_name, file_size, mime_type)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (
                    file['unique_file_id'],
                    file['b_1'],
                    file['file_name'],
                    file['file_size'],
                    file['mime_type']
                ))
                print(f"✅ Added: {file['file_name']}")
            else:
                print(f"⏭️  Already exists: {file['file_name']}")
                
        except Exception as e:
            print(f"❌ Error adding {file['file_name']}: {e}")
    
    # Show current database state
    cursor.execute("SELECT COUNT(*) FROM media_files")
    total = cursor.fetchone()[0]
    print(f"\n📊 Total files in database: {total}")
    
    cursor.close()
    conn.close()
    print("\n🎉 Test setup complete!")
    print("\nℹ️  You can now visit /files route to see the file viewer")

def clear_test_data():
    """Remove test data from database"""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()
    
    print("🧹 Clearing test data...")
    
    test_ids = ['AgADTest001', 'AgADTest002', 'AgADTest003']
    
    for test_id in test_ids:
        cursor.execute(
            "DELETE FROM media_files WHERE unique_file_id = %s",
            (test_id,)
        )
    
    print("✅ Test data cleared")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        clear_test_data()
    else:
        add_test_data()
