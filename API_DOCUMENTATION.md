 # Karaoke Backend API Documentation

## Overview

The Karaoke Backend API provides a complete solution for processing audio files into karaoke-ready content. It handles audio stem separation, vocal transcription, and beat analysis through an asynchronous job queue system.

**Base URL**: `http://localhost:8000`  
**API Version**: 1.0.0  
**Content-Type**: `application/json`

---

## Authentication

Currently, no authentication is required. All endpoints are publicly accessible.

---

## Core Workflow

1. **Upload** audio file → Get job ID
2. **Monitor** job progress → Check status
3. **Retrieve** results → Download processed files

---

## Endpoints Reference

### 1. Health Check

#### `GET /health`
Check if the API is running and healthy.

**Response:**
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2024-01-01T10:00:00",
  "uptime": 3600.5,
  "services": {
    "redis": "connected|disconnected",
    "celery": "active|inactive"
  }
}
```

**Status Codes:**
- `200` - Service is healthy
- `503` - Service is degraded/unhealthy

---

### 2. File Upload & Processing

#### `POST /api/process`
Upload an audio file for processing.

**Content-Type**: `multipart/form-data`

**Parameters:**
- `file` (required): Audio file (mp3, wav, m4a, flac)
- `max_file_size`: 100MB

**Request Example:**
```javascript
const formData = new FormData();
formData.append('file', audioFile);

fetch('/api/process', {
  method: 'POST',
  body: formData
})
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "File uploaded successfully. Processing started.",
  "estimated_time": "2-5 minutes",
  "file_info": {
    "filename": "song.mp3",
    "size": 4500000,
    "format": "mp3"
  }
}
```

**Status Codes:**
- `200` - File uploaded successfully
- `400` - Invalid file format or size
- `413` - File too large
- `500` - Server error

**Supported Formats:**
- MP3 (.mp3)
- WAV (.wav)
- M4A (.m4a)
- FLAC (.flac)

---

### 3. Job Status Monitoring

#### `GET /api/status/{job_id}`
Get comprehensive job status and progress.

**Path Parameters:**
- `job_id` (string): Unique job identifier

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing|completed|failed|queued",
  "progress": 75,
  "current_step": "beat_analysis",
  "created_at": "2024-01-01T10:00:00",
  "updated_at": "2024-01-01T10:03:45",
  "estimated_completion": "30.5 seconds",
  "processing_time": 225.8,
  "error_message": null,
  
  "stem_separation": {
    "status": "completed",
    "progress": 100,
    "vocals_path": "/path/to/vocals.wav",
    "drums_path": "/path/to/drums.wav",
    "bass_path": "/path/to/bass.wav",
    "other_path": "/path/to/other.wav",
    "processing_time": 45.2,
    "error": null
  },
  
  "transcription": {
    "status": "completed",
    "progress": 100,
    "transcription_path": "/path/to/transcription.json",
    "language": "en",
    "word_count": 156,
    "processing_time": 12.3,
    "error": null
  },
  
  "beat_analysis": {
    "status": "processing",
    "progress": 60,
    "tempo_bpm": 120.5,
    "beat_count": 240,
    "time_signature": "4/4",
    "beat_confidence": 0.95,
    "rhythm_regularity": 0.88,
    "processing_time": null,
    "error": null
  },
  
  "audio_duration": 180.0,
  "tempo_bpm": 120.5,
  "beat_count": 240,
  "file_size": 4500000
}
```

**Status Values:**
- `queued` - Job is waiting to be processed
- `processing` - Job is currently being processed
- `completed` - Job completed successfully
- `completed_with_errors` - Job completed with some errors
- `failed` - Job failed completely

**Status Codes:**
- `200` - Success
- `404` - Job not found
- `500` - Server error

#### `GET /api/status/{job_id}/simple`
Get simplified status for quick polling.

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 75,
  "current_step": "beat_analysis",
  "error_message": null
}
```

---

### 4. Results Retrieval

#### `GET /api/results/{job_id}`
Get complete job results and processed files.

**Path Parameters:**
- `job_id` (string): Unique job identifier

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "created_at": "2024-01-01T10:00:00",
  "completed_at": "2024-01-01T10:05:30",
  "total_processing_time": 330.5,
  
  "original_filename": "song.mp3",
  "audio_duration": 180.0,
  "file_size": 4500000,
  
  "stem_separation": {
    "vocals_path": "/path/to/vocals.wav",
    "drums_path": "/path/to/drums.wav",
    "bass_path": "/path/to/bass.wav",
    "other_path": "/path/to/other.wav",
    "processing_time": 45.2,
    "separation_model": "htdemucs"
  },
  
  "transcription": {
    "transcription_path": "/path/to/transcription.json",
    "language": "en",
    "word_count": 156,
    "processing_time": 12.3,
    "confidence": 0.92
  },
  
  "beat_analysis": {
    "tempo_bpm": 120.5,
    "beat_count": 240,
    "time_signature": "4/4",
    "beat_confidence": 0.95,
    "rhythm_regularity": 0.88,
    "analysis_json": "/path/to/analysis.json",
    "beats_json": "/path/to/beats.json",
    "onsets_json": "/path/to/onsets.json",
    "processing_time": 2.1
  },
  
  "output_files": [
    "/path/to/vocals.wav",
    "/path/to/drums.wav",
    "/path/to/bass.wav",
    "/path/to/other.wav",
    "/path/to/transcription.json",
    "/path/to/analysis.json",
    "/path/to/beats.json"
  ],
  
  "download_links": {
    "vocals_stem": "/api/files/550e8400-e29b-41d4-a716-446655440000/vocals.wav",
    "drums_stem": "/api/files/550e8400-e29b-41d4-a716-446655440000/drums.wav",
    "bass_stem": "/api/files/550e8400-e29b-41d4-a716-446655440000/bass.wav",
    "other_stem": "/api/files/550e8400-e29b-41d4-a716-446655440000/other.wav",
    "transcription": "/api/files/550e8400-e29b-41d4-a716-446655440000/transcription.json",
    "beat_analysis": "/api/files/550e8400-e29b-41d4-a716-446655440000/analysis.json",
    "beat_beats": "/api/files/550e8400-e29b-41d4-a716-446655440000/beats.json"
  }
}
```

**Status Codes:**
- `200` - Success
- `404` - Job not found
- `409` - Job not completed yet
- `500` - Server error

#### `GET /api/results/{job_id}/summary`
Get results summary without file paths.

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "audio_duration": 180.0,
  "processing_completed": {
    "stem_separation": true,
    "transcription": true,
    "beat_analysis": true
  },
  "key_metrics": {
    "tempo_bpm": 120.5,
    "beat_count": 240,
    "time_signature": "4/4",
    "transcription_language": "en"
  }
}
```

---

### 5. File Downloads

#### `GET /api/files/{job_id}/{filename}`
Download a processed file.

**Path Parameters:**
- `job_id` (string): Unique job identifier
- `filename` (string): Name of the file to download

**Query Parameters:**
- `inline` (boolean, optional): Display inline (true) or as attachment (false, default)

**Response:**
- Binary file content with appropriate headers
- Content-Type set based on file extension
- Content-Disposition for download/inline display

**Example URLs:**
```
/api/files/550e8400-e29b-41d4-a716-446655440000/vocals.wav
/api/files/550e8400-e29b-41d4-a716-446655440000/transcription.json?inline=true
```

**Status Codes:**
- `200` - File served successfully
- `404` - Job or file not found
- `403` - Access denied
- `500` - Server error

#### `GET /api/files/{job_id}`
List all available files for a job.

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_count": 7,
  "files": [
    {
      "filename": "vocals.wav",
      "category": "stem_separation",
      "size": 15728640,
      "mime_type": "audio/wav",
      "download_url": "/api/files/550e8400-e29b-41d4-a716-446655440000/vocals.wav",
      "preview_url": "/api/files/550e8400-e29b-41d4-a716-446655440000/vocals.wav?inline=true"
    },
    {
      "filename": "transcription.json",
      "category": "transcription",
      "size": 5432,
      "mime_type": "application/json",
      "download_url": "/api/files/550e8400-e29b-41d4-a716-446655440000/transcription.json",
      "preview_url": "/api/files/550e8400-e29b-41d4-a716-446655440000/transcription.json?inline=true"
    }
  ]
}
```

#### `HEAD /api/files/{job_id}/{filename}`
Check if a file exists without downloading.

**Response Headers:**
- `Content-Type`: File MIME type
- `Content-Length`: File size in bytes
- `X-File-Exists`: "true"
- `X-Job-ID`: Job identifier

---

## Processing Stages

### 1. Stem Separation
Separates audio into different instrument tracks:
- **Vocals** - Isolated vocal track
- **Drums** - Drum track
- **Bass** - Bass line
- **Other** - Other instruments (guitar, piano, etc.)

**Output**: WAV files for each stem

### 2. Vocal Transcription
Transcribes vocals to text with timestamps:
- Word-level timestamps
- Language detection
- Confidence scores

**Output**: JSON file with transcription data
```json
{
  "text": "Complete transcribed lyrics",
  "language": "en",
  "segments": [
    {
      "start": 0.5,
      "end": 2.3,
      "text": "Hello world",
      "words": [
        {"word": "Hello", "start": 0.5, "end": 1.2, "confidence": 0.95},
        {"word": "world", "start": 1.3, "end": 2.3, "confidence": 0.92}
      ]
    }
  ]
}
```

### 3. Beat Analysis
Analyzes rhythm and tempo:
- BPM detection
- Beat timestamps
- Time signature
- Rhythm regularity

**Output**: JSON files with beat data
```json
{
  "tempo_bpm": 120.5,
  "time_signature": "4/4",
  "beat_times": [0.5, 1.0, 1.5, 2.0],
  "confidence": 0.95,
  "rhythm_regularity": 0.88
}
```

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": true,
  "message": "Detailed error description",
  "status_code": 400
}
```

**Common Error Codes:**
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (job/file doesn't exist)
- `409` - Conflict (job not ready)
- `413` - Payload Too Large (file too big)
- `415` - Unsupported Media Type (invalid file format)
- `500` - Internal Server Error

---

## Frontend Integration Examples

### React/JavaScript Example

```javascript
class KaraokeAPI {
  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
  }

  // Upload file
  async uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${this.baseURL}/api/process`, {
      method: 'POST',
      body: formData
    });
    
    return await response.json();
  }

  // Check status
  async getStatus(jobId) {
    const response = await fetch(`${this.baseURL}/api/status/${jobId}`);
    return await response.json();
  }

  // Get results
  async getResults(jobId) {
    const response = await fetch(`${this.baseURL}/api/results/${jobId}`);
    return await response.json();
  }

  // Download file
  getDownloadURL(jobId, filename) {
    return `${this.baseURL}/api/files/${jobId}/${filename}`;
  }

  // Poll status until complete
  async pollUntilComplete(jobId, onProgress = null) {
    while (true) {
      const status = await this.getStatus(jobId);
      
      if (onProgress) onProgress(status);
      
      if (status.status === 'completed') {
        return await this.getResults(jobId);
      } else if (status.status === 'failed') {
        throw new Error(status.error_message || 'Job failed');
      }
      
      await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds
    }
  }
}

// Usage
const api = new KaraokeAPI();

async function processAudio(audioFile) {
  try {
    // Upload
    const uploadResult = await api.uploadFile(audioFile);
    console.log('Job started:', uploadResult.job_id);
    
    // Monitor progress
    const results = await api.pollUntilComplete(
      uploadResult.job_id,
      (status) => {
        console.log(`Progress: ${status.progress}% - ${status.current_step}`);
      }
    );
    
    // Use results
    console.log('Processing complete!', results);
    
    // Download files
    const vocalsURL = api.getDownloadURL(results.job_id, 'vocals.wav');
    // Use vocalsURL in audio player
    
  } catch (error) {
    console.error('Processing failed:', error);
  }
}
```

### Vue.js Example

```vue
<template>
  <div>
    <input type="file" @change="handleFileSelect" accept="audio/*" />
    <button @click="processFile" :disabled="!selectedFile || processing">
      {{ processing ? 'Processing...' : 'Process Audio' }}
    </button>
    
    <div v-if="progress">
      <div class="progress-bar">
        <div class="progress" :style="{width: progress.progress + '%'}"></div>
      </div>
      <p>{{ progress.current_step }} - {{ progress.progress }}%</p>
    </div>
    
    <div v-if="results">
      <h3>Results:</h3>
      <div v-for="(url, type) in results.download_links" :key="type">
        <a :href="url" target="_blank">Download {{ type }}</a>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      selectedFile: null,
      processing: false,
      progress: null,
      results: null,
      api: new KaraokeAPI()
    }
  },
  
  methods: {
    handleFileSelect(event) {
      this.selectedFile = event.target.files[0];
    },
    
    async processFile() {
      if (!this.selectedFile) return;
      
      this.processing = true;
      this.progress = null;
      this.results = null;
      
      try {
        const uploadResult = await this.api.uploadFile(this.selectedFile);
        
        this.results = await this.api.pollUntilComplete(
          uploadResult.job_id,
          (status) => {
            this.progress = status;
          }
        );
        
      } catch (error) {
        alert('Processing failed: ' + error.message);
      } finally {
        this.processing = false;
      }
    }
  }
}
</script>
```

---

## Rate Limits & Quotas

- **Max file size**: 100MB
- **Concurrent jobs**: 3 per instance
- **Job timeout**: 1 hour
- **File retention**: 24 hours

---

## WebSocket Support (Future)

For real-time progress updates, WebSocket support is planned:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/status/JOB_ID');
ws.onmessage = (event) => {
  const status = JSON.parse(event.data);
  updateProgress(status);
};
```

---

## Support & Troubleshooting

### Common Issues

1. **File upload fails**
   - Check file size (max 100MB)
   - Verify file format (mp3, wav, m4a, flac)
   - Ensure stable internet connection

2. **Job stays in 'queued' status**
   - Server may be processing other jobs
   - Check server capacity (max 3 concurrent jobs)

3. **Processing fails**
   - Check file integrity
   - Verify audio file is not corrupted
   - Check server logs for detailed errors

### Health Check
Always check `/health` endpoint before starting processing to ensure all services are running.

---

This documentation covers all current API endpoints and provides comprehensive examples for frontend integration. The API is designed to be RESTful and developer-friendly with consistent response formats and proper error handling.