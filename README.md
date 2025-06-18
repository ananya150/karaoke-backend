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

### Installation

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

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start Redis server** (if not already running)
   ```bash
   redis-server
   ```

6. **Run the application**
   ```bash
   # Start the API server
   uvicorn app:app --reload
   
   # In another terminal, start Celery workers
   celery -A celery_app worker --loglevel=info
   ```

## Project Structure

```
karaoke-backend/
├── About.md                 # Project documentation
├── Checklist.md            # Implementation checklist
├── README.md               # This file
├── requirements.txt        # Python dependencies
├── config.py              # Configuration management
├── app.py                 # Main FastAPI application
├── celery_app.py          # Celery configuration
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