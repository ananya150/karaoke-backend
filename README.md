# Karaoke Backend

A powerful backend application for processing audio files into karaoke-ready content with stem separation, vocal transcription, and beat analysis.

## Features

- 🎵 **Audio Stem Separation**: Split songs into vocals, drums, bass, and other instruments
- 🎤 **Vocal Transcription**: Generate synchronized lyrics with precise timing
- 🥁 **Beat Analysis**: Extract tempo and beat grid information
- 🚀 **Asynchronous Processing**: Handle multiple audio files concurrently
- 📡 **RESTful API**: Easy integration with frontend applications

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Redis server
- Git

### Easy Setup (Recommended)

Use our automated setup and management scripts:

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd karaoke-backend
   ./run.sh setup    # Automated setup
   ```

2. **Start Redis** (if not already running)
   ```bash
   brew services start redis    # macOS
   sudo systemctl start redis  # Linux
   ```

3. **Start everything**
   ```bash
   ./run.sh start    # Starts both server and worker
   ```

4. **Check health**
   ```bash
   ./run.sh health   # Verify everything is working
   ```

### Manual Setup

If you prefer manual setup:

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd karaoke-backend
   ```

2. **Set up virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   # Start the API server
   python app.py
   
   # In another terminal, start Celery workers
   python worker.py
   ```

## Management Scripts

The project includes convenient management scripts in the `scripts/` directory:

### Quick Commands
```bash
./run.sh start      # Start server and worker
./run.sh stop       # Stop all services
./run.sh restart    # Clean restart (flushes database)
./run.sh setup      # Development environment setup
./run.sh health     # System health check
./run.sh help       # Show all commands
```

### Direct Script Usage
```bash
./scripts/start_server.sh     # Start everything
./scripts/stop_server.sh      # Stop services
./scripts/restart_clean.sh    # Clean restart
./scripts/dev_setup.sh        # Setup environment
./scripts/health_check.sh     # Health check
```

For detailed script documentation, see [`scripts/SCRIPTS_README.md`](scripts/SCRIPTS_README.md).

## Project Structure

```
karaoke-backend/
├── About.md                 # Project documentation
├── Checklist.md            # Implementation checklist
├── README.md               # This file
├── requirements.txt        # Python dependencies
├── run.sh                  # Script runner (./run.sh start)
├── config.py              # Configuration management
├── app.py                 # Main FastAPI application
├── celery_app.py          # Celery configuration
├── worker.py              # Celery worker script
├── scripts/               # Management scripts
│   ├── start_server.sh    # Start server and worker
│   ├── stop_server.sh     # Stop all services
│   ├── restart_clean.sh   # Clean restart
│   ├── dev_setup.sh       # Development setup
│   ├── health_check.sh    # System health check
│   └── SCRIPTS_README.md  # Detailed script documentation
├── routes/                # API route handlers
├── tasks/                 # Background task definitions
├── ai_models/             # AI model handlers
├── database/              # Database connections
├── utils/                 # Utility functions
├── storage/               # File storage
│   ├── uploads/           # Uploaded files
│   └── jobs/              # Processing results
├── logs/                  # Application logs
├── models/                # AI model files
└── tests/                 # Test files
```

## API Endpoints

- `POST /process` - Upload audio file and start processing
- `GET /status/{job_id}` - Check processing status
- `GET /results/{job_id}` - Get processing results
- `GET /static/{path}` - Serve processed files
- `GET /health` - Health check

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
flake8 .
```

### Using Docker
```bash
docker-compose up -d
```

## Configuration

The application uses environment variables for configuration. See `config.py` for all available options.

Key settings:
- `REDIS_HOST`: Redis server hostname
- `MAX_FILE_SIZE`: Maximum upload file size
- `WHISPER_MODEL`: Whisper model for transcription
- `MAX_CONCURRENT_JOBS`: Number of concurrent processing jobs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License. 