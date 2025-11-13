#!/bin/bash

echo "========================================================================"
echo "R2 INTEGRATION VERIFICATION"
echo "========================================================================"
echo ""

echo "1. Checking New Files Created:"
echo "   --------------------------------"
ls -lh WebStreamer/r2_storage.py 2>/dev/null && echo "   ✓ R2 storage module exists" || echo "   ✗ Missing R2 storage module"
ls -lh test_r2_simple.py 2>/dev/null && echo "   ✓ Test suite exists" || echo "   ✗ Missing test suite"
ls -lh .env.example 2>/dev/null && echo "   ✓ Environment template exists" || echo "   ✗ Missing env template"
ls -lh R2_INTEGRATION_GUIDE.md 2>/dev/null && echo "   ✓ Integration guide exists" || echo "   ✗ Missing guide"
ls -lh R2_IMPLEMENTATION_SUMMARY.md 2>/dev/null && echo "   ✓ Implementation summary exists" || echo "   ✗ Missing summary"
echo ""

echo "2. Checking Modified Files:"
echo "   --------------------------------"
grep -q "R2_Domain" WebStreamer/vars.py && echo "   ✓ vars.py updated with R2 config" || echo "   ✗ vars.py not updated"
grep -q "from WebStreamer.r2_storage import" WebStreamer/bot/plugins/media_handler.py && echo "   ✓ media_handler.py integrated with R2" || echo "   ✗ media_handler.py not integrated"
echo ""

echo "3. Checking Dependencies:"
echo "   --------------------------------"
python3 -c "import requests; print('   ✓ requests library installed')" 2>/dev/null || echo "   ✗ requests library missing"
python3 -c "import aiohttp; print('   ✓ aiohttp library installed')" 2>/dev/null || echo "   ✗ aiohttp library missing"
python3 -c "import psycopg2; print('   ✓ psycopg2 library installed')" 2>/dev/null || echo "   ✗ psycopg2 library missing"
echo ""

echo "4. Testing R2 Module:"
echo "   --------------------------------"
python3 test_r2_simple.py > /tmp/r2_test_output.txt 2>&1
if [ $? -eq 0 ]; then
    echo "   ✓ R2 test suite passed"
    grep "R2_Domain:" /tmp/r2_test_output.txt | head -1
    grep "R2_Folder:" /tmp/r2_test_output.txt | head -1
    grep "R2_Public:" /tmp/r2_test_output.txt | head -1
else
    echo "   ✗ R2 test suite failed"
    echo "   Check /tmp/r2_test_output.txt for details"
fi
echo ""

echo "5. Code Structure Verification:"
echo "   --------------------------------"
echo "   R2 Storage Module Functions:"
python3 -c "
import sys
import os
os.environ['API_ID'] = '12345'
os.environ['API_HASH'] = 'test'
os.environ['BOT_TOKEN'] = 'test'
os.environ['BIN_CHANNEL'] = '123456'
os.environ['BIN_CHANNEL_WITHOUT_MINUS'] = '123456'
os.environ['DATABASE_URL'] = 'test'
from WebStreamer.r2_storage import R2Storage
import inspect
r2 = R2Storage()
for method in ['check_file_exists', 'upload_file_data', 'format_file_data']:
    if hasattr(r2, method):
        print(f'     ✓ {method}()')
    else:
        print(f'     ✗ {method}() missing')
" 2>/dev/null || echo "   ✗ Could not verify module functions"
echo ""

echo "========================================================================"
echo "VERIFICATION COMPLETE"
echo "========================================================================"
echo ""
echo "Next Steps:"
echo "1. Configure your environment variables (.env file)"
echo "2. Run the bot: python3 -m WebStreamer"
echo "3. Add bot to a Telegram channel"
echo "4. Post a file and verify R2 integration"
echo ""
echo "For detailed instructions, see:"
echo "  • R2_IMPLEMENTATION_SUMMARY.md"
echo "  • R2_INTEGRATION_GUIDE.md"
echo ""
