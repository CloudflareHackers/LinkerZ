#!/usr/bin/env python3
"""
Test script for R2 Storage Integration
Tests the R2 storage check and upload functionality
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from WebStreamer.r2_storage import get_r2_storage
from WebStreamer.vars import Var

def test_r2_configuration():
    """Test R2 configuration is loaded"""
    print("=" * 60)
    print("Testing R2 Configuration")
    print("=" * 60)
    
    print(f"R2_Domain: {Var.R2_Domain}")
    print(f"R2_Folder: {Var.R2_Folder}")
    print(f"R2_Public: {Var.R2_Public}")
    print()

def test_r2_check_file():
    """Test checking if a file exists in R2"""
    print("=" * 60)
    print("Testing R2 File Check")
    print("=" * 60)
    
    r2 = get_r2_storage()
    
    # Test with a sample unique_file_id (replace with actual one for real test)
    test_file_id = "AgAD-A0AAij8UVE"
    print(f"Checking if file exists: {test_file_id}")
    
    result = r2.check_file_exists(test_file_id)
    
    if result:
        print(f"✅ File EXISTS in R2")
        print(f"File data: {result}")
    else:
        print(f"❌ File NOT FOUND in R2")
    print()
    
    return result

def test_r2_upload():
    """Test uploading data to R2"""
    print("=" * 60)
    print("Testing R2 Upload")
    print("=" * 60)
    
    r2 = get_r2_storage()
    
    # Sample data for testing
    test_unique_id = "TEST_" + "AgAD-A0AAij8UVE"
    
    test_data = r2.format_file_data(
        unique_file_id=test_unique_id,
        bot_file_ids={
            "b_1_file_id": "BQACAgQAAx0CaZ9HgwACGQJovW8pV30uZFBM3pcyXd3px7l03wAC-A0AAij8UVG-evIP_IB6ox4E"
        },
        caption="Test File Upload",
        file_size=1024000,
        file_type="document",
        message_id=12345,
        channel_id=-1001234567890,
        file_name="test_file.txt",
        mime_type="text/plain"
    )
    
    print(f"Uploading test file: {test_unique_id}")
    print(f"Data: {test_data}")
    
    success = r2.upload_file_data(test_unique_id, test_data)
    
    if success:
        print(f"✅ Upload SUCCESSFUL")
        
        # Try to verify by checking if it exists
        print(f"Verifying upload...")
        verify_result = r2.check_file_exists(test_unique_id)
        if verify_result:
            print(f"✅ Verification SUCCESSFUL - File found in R2")
        else:
            print(f"⚠️ File uploaded but not immediately available (may take time to propagate)")
    else:
        print(f"❌ Upload FAILED")
    print()

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("R2 Storage Integration Test Suite")
    print("=" * 60 + "\n")
    
    try:
        # Test 1: Configuration
        test_r2_configuration()
        
        # Test 2: Check existing file
        test_r2_check_file()
        
        # Test 3: Upload new file
        test_r2_upload()
        
        print("=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
