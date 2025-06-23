#!/bin/bash

# Karaoke Backend - Health Check Script
# This script checks the status of all services and components

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏥 Karaoke Backend Health Check${NC}"
echo -e "${BLUE}===============================${NC}\n"

# Initialize counters
CHECKS_PASSED=0
TOTAL_CHECKS=0

# Function to check and report status
check_status() {
    local service_name=$1
    local check_command=$2
    local success_msg=$3
    local failure_msg=$4
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    echo -e "${BLUE}🔍 Checking $service_name...${NC}"
    
    if eval "$check_command"; then
        echo -e "${GREEN}   ✅ $success_msg${NC}"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
        return 0
    else
        echo -e "${RED}   ❌ $failure_msg${NC}"
        return 1
    fi
}

# Change to the backend directory (parent of scripts)
cd "$(dirname "$0")/.." || {
    echo -e "${RED}❌ Error: Could not change to backend directory${NC}"
    exit 1
}

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo -e "${RED}❌ Error: Backend directory structure is incorrect${NC}"
    exit 1
fi

# Check virtual environment
check_status "Virtual Environment" \
    "[ -d 'venv' ] && [ -n '$VIRTUAL_ENV' ]" \
    "Virtual environment is active" \
    "Virtual environment not found or not activated"

# Check Redis connection
check_status "Redis Connection" \
    "redis-cli ping &>/dev/null" \
    "Redis is running and accessible" \
    "Redis is not running or not accessible"

# Check if FastAPI server is running
check_status "FastAPI Server Process" \
    "pgrep -f 'python.*app.py' &>/dev/null || pgrep -f 'uvicorn.*app:app' &>/dev/null" \
    "FastAPI server process is running" \
    "FastAPI server process not found"

# Check if Celery worker is running
check_status "Celery Worker Process" \
    "pgrep -f 'python.*worker.py' &>/dev/null || pgrep -f 'celery.*worker' &>/dev/null" \
    "Celery worker process is running" \
    "Celery worker process not found"

# Check API endpoint
check_status "API Endpoint" \
    "curl -s http://localhost:8000/health &>/dev/null" \
    "API endpoint is responding" \
    "API endpoint is not responding"

# Check Redis database with Python
if [ -d "venv" ]; then
    source ./venv/bin/activate 2>/dev/null || true
fi

check_status "Redis Database Connection (Python)" \
    "python3 -c 'from database.redis_client import test_redis_connection; exit(0 if test_redis_connection() else 1)' 2>/dev/null" \
    "Redis database connection working" \
    "Redis database connection failed"

# Check Celery worker health
check_status "Celery Worker Health" \
    "python3 -c 'from celery_app import celery_app; celery_app.control.ping(); exit(0)' 2>/dev/null" \
    "Celery worker is healthy" \
    "Celery worker health check failed"

# Check required directories
check_status "Required Directories" \
    "[ -d 'storage/uploads' ] && [ -d 'storage/jobs' ] && [ -d 'logs' ]" \
    "All required directories exist" \
    "Some required directories are missing"

# Check port availability/usage
echo -e "\n${BLUE}🔌 Port Status:${NC}"
if command -v lsof &> /dev/null; then
    if lsof -i :8000 &> /dev/null; then
        echo -e "${GREEN}   Port 8000: In use (expected for running server)${NC}"
        lsof -i :8000 | tail -n +2 | while read line; do
            echo -e "${BLUE}   $line${NC}"
        done
    else
        echo -e "${YELLOW}   Port 8000: Available (server might not be running)${NC}"
    fi
else
    echo -e "${YELLOW}   Cannot check port status (lsof not available)${NC}"
fi

# Display disk usage for storage
echo -e "\n${BLUE}💾 Storage Usage:${NC}"
if [ -d "storage" ]; then
    du -sh storage/* 2>/dev/null | while read size dir; do
        echo -e "${BLUE}   $dir: $size${NC}"
    done
else
    echo -e "${YELLOW}   Storage directory not found${NC}"
fi

# Check log files
echo -e "\n${BLUE}📋 Recent Log Activity:${NC}"
if [ -d "logs" ] && [ "$(ls -A logs/ 2>/dev/null)" ]; then
    log_files=$(find logs -name "*.log" -type f -mtime -1 2>/dev/null | head -3)
    if [ -n "$log_files" ]; then
        echo "$log_files" | while read logfile; do
            if [ -f "$logfile" ]; then
                lines=$(wc -l < "$logfile" 2>/dev/null || echo "0")
                size=$(du -sh "$logfile" 2>/dev/null | cut -f1 || echo "unknown")
                echo -e "${BLUE}   $logfile: $lines lines, $size${NC}"
            fi
        done
    else
        echo -e "${YELLOW}   No recent log files found${NC}"
    fi
else
    echo -e "${YELLOW}   No log files found${NC}"
fi

# Summary
echo -e "\n${BLUE}📊 Health Check Summary${NC}"
echo -e "${BLUE}=======================${NC}"

if [ $CHECKS_PASSED -eq $TOTAL_CHECKS ]; then
    echo -e "${GREEN}🎉 All systems operational! ($CHECKS_PASSED/$TOTAL_CHECKS checks passed)${NC}"
    exit 0
elif [ $CHECKS_PASSED -gt $((TOTAL_CHECKS / 2)) ]; then
    echo -e "${YELLOW}⚠️  System partially operational ($CHECKS_PASSED/$TOTAL_CHECKS checks passed)${NC}"
    echo -e "${YELLOW}💡 Some services may need attention${NC}"
    exit 1
else
    echo -e "${RED}❌ System needs attention ($CHECKS_PASSED/$TOTAL_CHECKS checks passed)${NC}"
    echo -e "${RED}💡 Multiple services are not running properly${NC}"
    exit 2
fi 