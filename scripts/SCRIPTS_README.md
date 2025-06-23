# Karaoke Backend - Management Scripts

This directory contains several utility scripts to help you manage the Karaoke Backend server easily.

## Scripts Overview

### 🚀 `start_server.sh`
**Purpose**: Start the entire system with one command
- Starts both the FastAPI server and Celery worker
- Activates the virtual environment automatically  
- Checks Redis connection before starting
- Handles graceful shutdown with Ctrl+C
- Shows running services status

**Usage**:
```bash
./scripts/start_server.sh
```

**What it does**:
- ✅ Checks virtual environment
- ✅ Verifies Redis is running
- ✅ Creates necessary directories
- ✅ Starts Celery worker in background
- ✅ Starts FastAPI server
- ✅ Shows status and URLs

---

### 🛑 `stop_server.sh`
**Purpose**: Gracefully stop all running services
- Stops FastAPI server processes
- Stops Celery worker processes
- Shows port status after shutdown

**Usage**:
```bash
./scripts/stop_server.sh
```

**What it does**:
- 🛑 Graceful SIGTERM shutdown first
- 🛑 Force SIGKILL if needed
- 📊 Shows remaining processes
- 🔌 Checks port availability

---

### 🧹 `restart_clean.sh`
**Purpose**: Clean restart with full database and storage reset
- Stops all services
- Flushes Redis database (removes all jobs)
- Cleans storage directories
- Restarts the server fresh

**Usage**:
```bash
./scripts/restart_clean.sh
```

**What it does**:
- 🛑 Stops all services
- 🗑️ Flushes Redis database
- 🧽 Cleans upload/job directories
- 🧹 Removes temporary files and old logs
- 📁 Recreates directory structure
- 🚀 Starts fresh server

**⚠️ Warning**: This will delete all job data and uploaded files!

---

### 🛠️ `dev_setup.sh`
**Purpose**: Initial development environment setup
- Creates virtual environment
- Installs dependencies
- Checks system requirements
- Creates configuration files

**Usage**:
```bash
./scripts/dev_setup.sh
```

**What it does**:
- 🐍 Checks Python version (3.8+)
- 📦 Creates/activates virtual environment
- 📚 Installs requirements.txt
- 🔍 Checks Redis installation
- 📁 Creates necessary directories
- ⚙️ Creates .env file template
- 🧪 Tests basic imports

---

### 🏥 `health_check.sh`
**Purpose**: Comprehensive system health check
- Verifies all services are running
- Checks database connections
- Shows resource usage
- Provides detailed status report

**Usage**:
```bash
./scripts/health_check.sh
```

**What it checks**:
- 📦 Virtual environment status
- 🔍 Redis connection (CLI and Python)
- 🚀 FastAPI server process
- 🔄 Celery worker process
- 🌐 API endpoint response
- 🔄 Celery worker health
- 📁 Required directories
- 🔌 Port usage (8000)
- 💾 Storage usage
- 📋 Recent logs

**Exit codes**:
- `0`: All systems operational
- `1`: Partially operational
- `2`: Multiple issues detected

---

## Quick Start Guide

### First Time Setup
```bash
# 1. Run the development setup
./scripts/dev_setup.sh

# 2. Make sure Redis is running
brew services start redis    # macOS
# or
sudo systemctl start redis  # Linux

# 3. Start the server
./scripts/start_server.sh
```

### Daily Development Workflow
```bash
# Start everything
./scripts/start_server.sh

# Check if everything is working
./scripts/health_check.sh

# When you're done
./scripts/stop_server.sh
```

### When Things Go Wrong
```bash
# Clean restart (removes all data)
./scripts/restart_clean.sh

# Or step by step:
./scripts/stop_server.sh
./scripts/health_check.sh
./scripts/start_server.sh
```

---

## Service URLs

When the server is running, you can access:

- **Main API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Frontend**: http://localhost:8000/static/karaoke_frontend.html  
- **Health Check**: http://localhost:8000/health

---

## Troubleshooting

### Redis Issues
```bash
# Check if Redis is installed
redis-cli --version

# Start Redis manually
redis-server

# Test Redis connection
redis-cli ping
```

### Port Issues
```bash
# Check what's using port 8000
lsof -i :8000

# Kill processes on port 8000
./scripts/stop_server.sh
```

### Virtual Environment Issues
```bash
# Recreate virtual environment
rm -rf venv
./scripts/dev_setup.sh
```

### Permission Issues
```bash
# Make scripts executable
chmod +x *.sh
```

---

## Script Dependencies

All scripts require:
- **Bash**: Shell to run the scripts
- **Python 3.8+**: For the application
- **Redis**: For job storage
- **Virtual Environment**: Python dependencies isolation

Optional tools for enhanced functionality:
- **lsof**: Port checking (usually pre-installed)
- **curl**: API endpoint testing (usually pre-installed)
- **pgrep/pkill**: Process management (usually pre-installed)

---

## Environment Variables

The scripts will use these key environment variables (from `.env`):
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `DEBUG`: Debug mode (default: true)
- `REDIS_HOST`: Redis host (default: localhost)
- `REDIS_PORT`: Redis port (default: 6379)

---

## Logging

All services log to the `logs/` directory:
- Application logs: JSON format with structured data
- Celery worker logs: Task execution details
- Error logs: Automatically captured exceptions

Use `./scripts/health_check.sh` to see recent log activity.

---

**Happy coding! 🎤🚀** 