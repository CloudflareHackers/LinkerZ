#!/usr/bin/env python3
"""
Simple memory usage checker for the WebStreamer application.
Run this to see current memory consumption.
"""

import sys
import os

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("Note: Install psutil for detailed memory info: pip install psutil")

def get_memory_usage():
    """Get current memory usage"""
    if HAS_PSUTIL:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        rss_mb = memory_info.rss / 1024 / 1024
        vms_mb = memory_info.vms / 1024 / 1024
        
        print("=" * 60)
        print("MEMORY USAGE REPORT")
        print("=" * 60)
        print(f"RSS (Resident Set Size): {rss_mb:.2f} MB")
        print(f"VMS (Virtual Memory):    {vms_mb:.2f} MB")
        print()
        
        # Check against Heroku limits
        heroku_limit_mb = 512  # Default, change if you have larger dyno
        
        if 'DYNO' in os.environ:
            print("Running on Heroku")
            # Try to detect dyno size
            if os.environ.get('DYNO_RAM'):
                heroku_limit_mb = int(os.environ['DYNO_RAM'])
            else:
                # Manual check - you should update this
                heroku_limit_mb = 1024  # Assuming 1GB dyno
            
            usage_percent = (rss_mb / heroku_limit_mb) * 100
            print(f"Heroku Dyno Limit:       {heroku_limit_mb} MB")
            print(f"Usage:                   {usage_percent:.1f}%")
            print()
            
            if usage_percent > 90:
                print("⚠️  WARNING: Memory usage over 90%!")
            elif usage_percent > 80:
                print("⚠️  CAUTION: Memory usage over 80%")
            elif usage_percent > 70:
                print("ℹ️  INFO: Memory usage over 70%")
            else:
                print("✅ Memory usage is healthy")
        
        print("=" * 60)
        
    else:
        # Fallback without psutil
        print("=" * 60)
        print("BASIC MEMORY CHECK")
        print("=" * 60)
        print("Install psutil for detailed info:")
        print("  pip install psutil")
        print("=" * 60)

if __name__ == "__main__":
    get_memory_usage()
