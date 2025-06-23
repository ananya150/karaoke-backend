#!/bin/bash

# Karaoke Backend - Start Server Script
# This script starts both the FastAPI server and Celery worker

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🎤 Starting Karaoke Backend Server...${NC}"

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

# Activate virtual environment
if [ -d "venv" ]; then
    echo -e "${BLUE}📦 Activating virtual environment...${NC}"
    source ./venv/bin/activate
else
    echo -e "${YELLOW}⚠️  Warning: No virtual environment found. Make sure dependencies are installed.${NC}"
fi

# Check if Redis is running
echo -e "${BLUE}🔍 Checking Redis connection...${NC}"
python3 -c "
from database.redis_client import test_redis_connection
import sys
if not test_redis_connection():
    print('❌ Redis is not running or not accessible')
    print('💡 Please start Redis first: brew services start redis (on macOS) or sudo systemctl start redis (on Linux)')
    sys.exit(1)
else:
    print('✅ Redis is running')
"

if [ $? -ne 0 ]; then
    exit 1
fi

# Create necessary directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p storage/uploads storage/jobs storage/jobs/temp logs models

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down services...${NC}"
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null || true
    fi
    if [ ! -z "$WORKER_PID" ]; then
        kill $WORKER_PID 2>/dev/null || true
    fi
    echo -e "${GREEN}✅ Services stopped${NC}"
}

# Trap Ctrl+C and cleanup
trap cleanup SIGINT SIGTERM

# Start Celery worker in background
echo -e "${BLUE}🔄 Starting Celery worker...${NC}"
python3 worker.py &
WORKER_PID=$!

# Give worker a moment to start
sleep 3

# Check if worker is still running
if ! kill -0 $WORKER_PID 2>/dev/null; then
    echo -e "${RED}❌ Failed to start Celery worker${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Celery worker started (PID: $WORKER_PID)${NC}"

# Start FastAPI server
echo -e "${BLUE}🚀 Starting FastAPI server...${NC}"
python3 app.py &
SERVER_PID=$!

# Give server a moment to start
sleep 3

# Check if server is still running
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${RED}❌ Failed to start FastAPI server${NC}"
    kill $WORKER_PID 2>/dev/null || true
    exit 1
fi

echo -e "${GREEN}✅ FastAPI server started (PID: $SERVER_PID)${NC}"

# Show status
echo -e "\n${GREEN}🎉 Karaoke Backend is running!${NC}"
echo -e "${BLUE}📊 Services Status:${NC}"
echo -e "   FastAPI Server: http://localhost:8000 (PID: $SERVER_PID)"
echo -e "   Celery Worker: Running (PID: $WORKER_PID)"
echo -e "   API Documentation: http://localhost:8000/docs"
echo -e "   Frontend: http://localhost:8000/static/karaoke_frontend.html"
echo -e "\n${YELLOW}💡 Press Ctrl+C to stop all services${NC}"

# Wait for services to finish
wait $SERVER_PID $WORKER_PID 