#!/bin/bash

# Karaoke Backend - Clean Restart Script
# This script stops all services, flushes Redis, cleans up files, and restarts

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧹 Clean Restart of Karaoke Backend...${NC}"

# Change to the backend directory (parent of scripts)
cd "$(dirname "$0")/.." || {
    echo -e "${RED}❌ Error: Could not change to backend directory${NC}"
    exit 1
}

# Check if we're in the right directory
if [ ! -f "app.py" ] || [ ! -f "worker.py" ]; then
    echo -e "${RED}❌ Error: Backend directory structure is incorrect${NC}"
    exit 1
fi

# Stop existing processes
echo -e "${BLUE}🛑 Stopping existing services...${NC}"

# Find and kill existing processes
pkill -f "python.*app.py" 2>/dev/null || true
pkill -f "python.*worker.py" 2>/dev/null || true
pkill -f "celery.*worker" 2>/dev/null || true
pkill -f "uvicorn.*app:app" 2>/dev/null || true

# Wait a moment for processes to stop
sleep 2

echo -e "${GREEN}✅ Existing services stopped${NC}"

# Activate virtual environment if available
if [ -d "venv" ]; then
    echo -e "${BLUE}📦 Activating virtual environment...${NC}"
    source ./venv/bin/activate
else
    echo -e "${YELLOW}⚠️  Warning: No virtual environment found${NC}"
fi

# Flush Redis database
echo -e "${BLUE}🗑️  Flushing Redis database...${NC}"
python3 -c "
from database.redis_client import get_redis_client
from utils.logger import get_logger

logger = get_logger('cleanup')

try:
    with get_redis_client() as redis_client:
        # Flush all data in the current database
        redis_client.client.flushdb()
        logger.info('Redis database flushed successfully')
        print('✅ Redis database flushed')
except Exception as e:
    logger.error('Failed to flush Redis database', error=str(e))
    print(f'❌ Failed to flush Redis: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to flush Redis database${NC}"
    exit 1
fi

# Clean up storage directories but keep the structure
echo -e "${BLUE}🧽 Cleaning up storage directories...${NC}"

# Remove all files from uploads directory
if [ -d "storage/uploads" ]; then
    rm -rf storage/uploads/*
    echo "   ✅ Cleaned uploads directory"
fi

# Remove all files from jobs directory
if [ -d "storage/jobs" ]; then
    rm -rf storage/jobs/*
    mkdir -p storage/jobs/temp
    echo "   ✅ Cleaned jobs directory"
fi

# Clean up log files (optional - keep recent ones)
if [ -d "logs" ]; then
    find logs -name "*.log" -mtime +7 -delete 2>/dev/null || true
    echo "   ✅ Cleaned old log files"
fi

# Clean up any temporary files
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.temp" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

echo -e "${GREEN}✅ Cleanup completed${NC}"

# Recreate necessary directories
echo -e "${BLUE}📁 Recreating directory structure...${NC}"
mkdir -p storage/uploads storage/jobs storage/jobs/temp logs models

# Wait a moment before starting
echo -e "${BLUE}⏳ Waiting before restart...${NC}"
sleep 1

# Start the server
echo -e "${GREEN}🚀 Starting clean server...${NC}"
exec ./scripts/start_server.sh 