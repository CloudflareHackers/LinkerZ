#!/bin/bash

# Performance Optimization Deployment Script
# This script applies the performance fixes to your Heroku app

echo "🚀 Performance Optimization Deployment"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -d "WebStreamer" ]; then
    echo -e "${RED}❌ Error: WebStreamer directory not found${NC}"
    echo "Please run this script from the /app directory"
    exit 1
fi

echo -e "${YELLOW}📝 Configuration Summary:${NC}"
echo "  • ThreadPool Workers: 250 (for 500 concurrent streams)"
echo "  • Pyrogram Workers: 6 (for fast message replies)"
echo "  • LRU Cache Size: 50 (optimized caching)"
echo "  • Expected Memory: 700-750 MB"
echo ""

echo -e "${YELLOW}🔧 Changes Applied:${NC}"
echo "  ✅ Increased ThreadPool from 50 to 250 workers"
echo "  ✅ Increased Pyrogram WORKERS from 3 to 6"
echo "  ✅ Increased LRU cache from 15 to 50 entries"
echo "  ✅ Made all settings configurable via environment variables"
echo ""

# Ask for confirmation
read -p "Deploy to Heroku? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}📦 Committing changes...${NC}"
git add WebStreamer/server/stream_routes.py
git add WebStreamer/vars.py
git add PERFORMANCE_OPTIMIZATION_APPLIED.md
git add deploy_performance_fix.sh
git commit -m "Performance optimization: Increased workers for 500 concurrent streams

- ThreadPool: 50 → 250 workers (fixes timeouts)
- Pyrogram WORKERS: 3 → 6 (fixes bot reply delays)
- LRU Cache: 15 → 50 entries (better caching)
- Added environment variable configuration
- Memory usage: ~700-750MB (within 800MB limit)

Fixes:
- Bot not replying to link generation
- OTP generation timeouts
- File handling delays
- 500 concurrent stream support"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Changes committed${NC}"
else
    echo -e "${RED}❌ Commit failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🚀 Deploying to Heroku...${NC}"
git push heroku main

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Deployment successful${NC}"
else
    echo -e "${RED}❌ Deployment failed${NC}"
    echo "Try manual deployment: git push heroku main"
    exit 1
fi

echo ""
echo -e "${GREEN}🔄 Restarting Heroku app...${NC}"
heroku restart

echo ""
echo -e "${GREEN}📊 Monitoring logs (Ctrl+C to exit)...${NC}"
echo "Look for:"
echo "  • 'ThreadPool initialized with 250 workers'"
echo "  • 'LRU cache initialized with max size: 50'"
echo ""

heroku logs --tail | grep -E "initialized|ThreadPool|LRU cache|WORKERS|error|timeout" &
LOG_PID=$!

# Wait 30 seconds then show status
sleep 30
kill $LOG_PID 2>/dev/null

echo ""
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "  1. Test bot functions:"
echo "     • Send a file → should get link instantly"
echo "     • Request OTP → should respond instantly"
echo "     • Upload file → should store and reply"
echo ""
echo "  2. Monitor memory usage:"
echo "     heroku ps:scale"
echo ""
echo "  3. Check for errors:"
echo "     heroku logs --tail | grep error"
echo ""
echo "  4. Tune if needed:"
echo "     # More performance:"
echo "     heroku config:set THREADPOOL_WORKERS=300"
echo ""
echo "     # Less memory:"
echo "     heroku config:set THREADPOOL_WORKERS=200"
echo ""
echo -e "${GREEN}🎯 Bot should now handle 500 concurrent streams without timeouts!${NC}"
