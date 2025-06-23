#!/bin/bash

# Karaoke Backend - Stop Server Script
# This script gracefully stops all running services

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping Karaoke Backend services...${NC}"

# Change to the backend directory (parent of scripts)
cd "$(dirname "$0")/.." || {
    echo -e "${RED}❌ Error: Could not change to backend directory${NC}"
    exit 1
}

# Function to stop process by name pattern
stop_processes() {
    local pattern=$1
    local service_name=$2
    
    local pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}   Stopping $service_name (PIDs: $pids)...${NC}"
        
        # Try graceful shutdown first
        echo "$pids" | xargs -r kill -TERM 2>/dev/null || true
        
        # Wait a bit for graceful shutdown
        sleep 3
        
        # Check if any processes are still running
        local remaining_pids=$(pgrep -f "$pattern" 2>/dev/null || true)
        
        if [ -n "$remaining_pids" ]; then
            echo -e "${YELLOW}   Force stopping remaining $service_name processes...${NC}"
            echo "$remaining_pids" | xargs -r kill -KILL 2>/dev/null || true
        fi
        
        echo -e "${GREEN}   ✅ $service_name stopped${NC}"
    else
        echo -e "${GREEN}   ✅ No $service_name processes found${NC}"
    fi
}

# Stop FastAPI server
stop_processes "python.*app.py" "FastAPI server"
stop_processes "uvicorn.*app:app" "Uvicorn server"

# Stop Celery worker
stop_processes "python.*worker.py" "Celery worker"
stop_processes "celery.*worker" "Celery processes"

# Wait a moment to ensure all processes are stopped
sleep 1

# Check for any remaining Python processes that might be related
remaining=$(pgrep -f "(app\.py|worker\.py|celery)" 2>/dev/null || true)
if [ -n "$remaining" ]; then
    echo -e "${YELLOW}⚠️  Warning: Some processes might still be running (PIDs: $remaining)${NC}"
    echo -e "${BLUE}💡 Use 'ps aux | grep python' to check manually${NC}"
else
    echo -e "${GREEN}🎉 All Karaoke Backend services stopped successfully${NC}"
fi

# Optional: Show port status
echo -e "\n${BLUE}📊 Port status:${NC}"
if command -v lsof &> /dev/null; then
    if lsof -i :8000 &> /dev/null; then
        echo -e "${YELLOW}   Port 8000: Still in use${NC}"
        lsof -i :8000
    else
        echo -e "${GREEN}   Port 8000: Available${NC}"
    fi
else
    echo -e "${YELLOW}   lsof not available, cannot check port status${NC}"
fi 