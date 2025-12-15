#!/usr/bin/env python3
"""
Verification script for bot fixes
Checks if all required functions and configurations are in place
"""

import sys
import importlib.util

def check_file_syntax(filepath, description):
    """Check if a Python file has valid syntax"""
    try:
        spec = importlib.util.spec_from_file_location("module", filepath)
        module = importlib.util.module_from_spec(spec)
        print(f"✅ {description}: Syntax valid")
        return True
    except SyntaxError as e:
        print(f"❌ {description}: Syntax error - {e}")
        return False
    except Exception as e:
        print(f"⚠️  {description}: {e}")
        return False

def check_function_exists(filepath, function_name):
    """Check if a function exists in a file"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            if f"def {function_name}" in content:
                print(f"✅ Function '{function_name}' exists in {filepath}")
                return True
            else:
                print(f"❌ Function '{function_name}' NOT FOUND in {filepath}")
                return False
    except Exception as e:
        print(f"❌ Error checking {filepath}: {e}")
        return False

def check_import_exists(filepath, import_text):
    """Check if an import statement exists in a file"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            if import_text in content:
                print(f"✅ Import '{import_text}' exists in {filepath}")
                return True
            else:
                print(f"❌ Import '{import_text}' NOT FOUND in {filepath}")
                return False
    except Exception as e:
        print(f"❌ Error checking {filepath}: {e}")
        return False

def main():
    print("=" * 70)
    print("🔍 VERIFICATION SCRIPT - Bot Fixes")
    print("=" * 70)
    print()
    
    all_checks_passed = True
    
    # Check 1: media_handler.py syntax
    print("📋 Check 1: Verifying media_handler.py syntax...")
    if not check_file_syntax("/app/WebStreamer/bot/plugins/media_handler.py", "media_handler.py"):
        all_checks_passed = False
    print()
    
    # Check 2: register_multi_client_handlers function exists
    print("📋 Check 2: Verifying register_multi_client_handlers() exists...")
    if not check_function_exists("/app/WebStreamer/bot/plugins/media_handler.py", "register_multi_client_handlers"):
        all_checks_passed = False
    print()
    
    # Check 3: clients.py syntax
    print("📋 Check 3: Verifying clients.py syntax...")
    if not check_file_syntax("/app/WebStreamer/bot/clients.py", "clients.py"):
        all_checks_passed = False
    print()
    
    # Check 4: ThreadPoolExecutor import in clients.py
    print("📋 Check 4: Verifying ThreadPoolExecutor import in clients.py...")
    if not check_import_exists("/app/WebStreamer/bot/clients.py", "from concurrent.futures import ThreadPoolExecutor"):
        all_checks_passed = False
    print()
    
    # Check 5: bot/__init__.py syntax
    print("📋 Check 5: Verifying bot/__init__.py syntax...")
    if not check_file_syntax("/app/WebStreamer/bot/__init__.py", "bot/__init__.py"):
        all_checks_passed = False
    print()
    
    # Check 6: ThreadPoolExecutor import in bot/__init__.py
    print("📋 Check 6: Verifying ThreadPoolExecutor import in bot/__init__.py...")
    if not check_import_exists("/app/WebStreamer/bot/__init__.py", "from concurrent.futures import ThreadPoolExecutor"):
        all_checks_passed = False
    print()
    
    # Check 7: Button generation code exists
    print("📋 Check 7: Verifying button generation code exists...")
    try:
        with open("/app/WebStreamer/bot/plugins/media_handler.py", 'r') as f:
            content = f.read()
            if 'InlineKeyboardButton("DL Link"' in content:
                print("✅ Button generation code found")
            else:
                print("❌ Button generation code NOT FOUND")
                all_checks_passed = False
    except Exception as e:
        print(f"❌ Error: {e}")
        all_checks_passed = False
    print()
    
    # Check 8: Executor configuration in clients.py
    print("📋 Check 8: Verifying executor configuration in clients.py...")
    try:
        with open("/app/WebStreamer/bot/clients.py", 'r') as f:
            content = f.read()
            if 'executor=executor' in content:
                print("✅ Executor configuration found in clients.py")
            else:
                print("❌ Executor configuration NOT FOUND in clients.py")
                all_checks_passed = False
    except Exception as e:
        print(f"❌ Error: {e}")
        all_checks_passed = False
    print()
    
    # Final Result
    print("=" * 70)
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED! Bot is ready for deployment.")
        print("=" * 70)
        return 0
    else:
        print("❌ SOME CHECKS FAILED! Please review the errors above.")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
