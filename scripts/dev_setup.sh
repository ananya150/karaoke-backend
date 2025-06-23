#!/bin/bash

# Karaoke Backend - Development Setup Script
# This script sets up the development environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🎤 Karaoke Backend - Development Setup${NC}"

# Change to the backend directory (parent of scripts)
cd "$(dirname "$0")/.." || {
    echo -e "${RED}❌ Error: Could not change to backend directory${NC}"
    exit 1
}

# Check if we're in the right directory
if [ ! -f "requirements.txt" ] || [ ! -f "app.py" ]; then
    echo -e "${RED}❌ Error: Backend directory structure is incorrect${NC}"
    exit 1
fi

# Check Python version
echo -e "${BLUE}🐍 Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo -e "${GREEN}   ✅ Python $python_version is compatible${NC}"
else
    echo -e "${RED}   ❌ Python $python_version is too old. Required: $required_version+${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${BLUE}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}   ✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}   ✅ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
source ./venv/bin/activate

# Upgrade pip
echo -e "${BLUE}⬆️  Upgrading pip...${NC}"
pip install --upgrade pip

# Install requirements
echo -e "${BLUE}📚 Installing Python dependencies...${NC}"
pip install -r requirements.txt

# Check Redis installation and status
echo -e "${BLUE}🔍 Checking Redis...${NC}"
if command -v redis-server &> /dev/null; then
    echo -e "${GREEN}   ✅ Redis is installed${NC}"
    
    # Check if Redis is running
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}   ✅ Redis is running${NC}"
    else
        echo -e "${YELLOW}   ⚠️  Redis is installed but not running${NC}"
        echo -e "${BLUE}   💡 To start Redis:${NC}"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo -e "      brew services start redis"
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            echo -e "      sudo systemctl start redis"
            echo -e "      # or"
            echo -e "      redis-server"
        fi
    fi
else
    echo -e "${RED}   ❌ Redis is not installed${NC}"
    echo -e "${BLUE}   💡 To install Redis:${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "      brew install redis"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo -e "      sudo apt-get install redis-server  # Ubuntu/Debian"
        echo -e "      sudo yum install redis            # CentOS/RHEL"
        echo -e "      sudo pacman -S redis             # Arch Linux"
    fi
fi

# Create necessary directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p storage/uploads storage/jobs storage/jobs/temp logs models
echo -e "${GREEN}   ✅ Directories created${NC}"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${BLUE}⚙️  Creating .env file...${NC}"
    cat > .env << 'EOF'
# Karaoke Backend Configuration
DEBUG=true
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Security
SECRET_KEY=dev-secret-key-change-in-production
CORS_ORIGINS=*

# AI Models
WHISPER_MODEL=base
DEMUCS_MODEL=htdemucs

# Processing
MAX_CONCURRENT_JOBS=3
JOB_TIMEOUT=3600
EOF
    echo -e "${GREEN}   ✅ .env file created${NC}"
else
    echo -e "${GREEN}   ✅ .env file already exists${NC}"
fi

# Make scripts executable
echo -e "${BLUE}🔧 Making scripts executable...${NC}"
chmod +x scripts/*.sh 2>/dev/null || true
echo -e "${GREEN}   ✅ Scripts are now executable${NC}"

# Test basic imports
echo -e "${BLUE}🧪 Testing basic imports...${NC}"
python3 -c "
import sys
try:
    from app import app
    from celery_app import celery_app
    from database.redis_client import test_redis_connection
    print('✅ All imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Import test failed${NC}"
    exit 1
fi

# Final status
echo -e "\n${GREEN}🎉 Development setup completed successfully!${NC}"
echo -e "\n${BLUE}📋 Next steps:${NC}"
echo -e "   1. Make sure Redis is running"
echo -e "   2. Run: ${YELLOW}./start_server.sh${NC} to start the server"
echo -e "   3. Visit: ${YELLOW}http://localhost:8000${NC} to test the API"
echo -e "   4. API docs: ${YELLOW}http://localhost:8000/docs${NC}"
echo -e "\n${BLUE}🛠️  Available scripts:${NC}"
echo -e "   ${YELLOW}./scripts/start_server.sh${NC}     - Start the server and worker"
echo -e "   ${YELLOW}./scripts/stop_server.sh${NC}      - Stop all services"
echo -e "   ${YELLOW}./scripts/restart_clean.sh${NC}    - Clean restart with Redis flush"
echo -e "   ${YELLOW}./scripts/dev_setup.sh${NC}        - Run this setup script again"

echo -e "\n${GREEN}Happy coding! 🚀${NC}" 