# Karaoke Backend Application

## Project Overview

This backend application powers a karaoke system by processing audio files to extract vocals, generate synchronized lyrics, and analyze musical timing. The system transforms regular music tracks into karaoke-ready content with separated audio stems and precise lyric timing.

## Core Features

### 🎵 Audio Processing Pipeline
- **Stem Separation**: Splits audio into vocals, drums, bass, and other instruments
- **Vocal Transcription**: Generates lyrics with precise word-level timestamps
- **Beat Analysis**: Extracts tempo and beat grid information for timeline synchronization

### 🚀 Asynchronous Processing
- **Job Queue System**: Handles long-running audio processing tasks asynchronously
- **Real-time Status Updates**: Provides progress tracking for processing jobs
- **Scalable Worker Architecture**: Supports multiple concurrent processing jobs

### 📡 RESTful API
- **File Upload Endpoint**: Accepts audio files and initiates processing
- **Status Monitoring**: Real-time job progress and status checking
- **Results Delivery**: Provides processed stems and metadata upon completion

## Technical Architecture

### API Endpoints
- `POST /process` - Upload audio file and start processing job
- `GET /status/{job_id}` - Check processing status and progress
- `GET /results/{job_id}` - Retrieve processed files and metadata
- `GET /static/{path_to_file}` - Serve processed audio files

### Technology Stack
- **Framework**: Flask/FastAPI (Python web framework)
- **Task Queue**: Celery with Redis/RabbitMQ message broker
- **AI/ML Tools**:
  - **Demucs/Spleeter**: Audio stem separation
  - **Whisper (OpenAI)**: Speech-to-text with timing
  - **Librosa**: Audio analysis and beat detection
- **Storage**: Local filesystem with optional cloud storage (S3/GCS)
- **Database**: Redis for job state management
- **Containerization**: Docker and Docker Compose

### Processing Workflow
1. **Upload**: Client uploads audio file via API
2. **Queue**: Job added to Celery task queue with unique ID
3. **Process**: Background worker performs stem separation
4. **Transcribe**: Vocal track processed for lyrics with timestamps
5. **Analyze**: Beat detection and tempo analysis
6. **Store**: Results saved and made available via API
7. **Deliver**: Client retrieves processed stems and metadata

## File Structure
Each processing job creates organized file structure:
```
jobs/
├── {job_id}/
│   ├── original.mp3
│   ├── stems/
│   │   ├── vocals.wav
│   │   ├── drums.wav
│   │   ├── bass.wav
│   │   └── other.wav
│   ├── lyrics.json
│   └── beats.json
```

## Scalability Features
- **Horizontal Scaling**: Multiple worker processes for concurrent jobs
- **Cloud Storage**: Support for AWS S3 or Google Cloud Storage
- **Load Balancing**: API can be scaled behind load balancer
- **Monitoring**: Job status tracking and error handling

## Use Cases
- **Karaoke Applications**: Generate backing tracks with synchronized lyrics
- **Music Production**: Isolate stems for remixing and analysis
- **Educational Tools**: Create learning materials with precise timing
- **Content Creation**: Extract vocals or instrumentals for creative projects

## Performance Considerations
- Processing time varies by song length (typically 1-3 minutes for 4-minute song)
- Memory usage scales with audio quality and length
- Concurrent job limits based on server resources
- Optional GPU acceleration for AI model inference 