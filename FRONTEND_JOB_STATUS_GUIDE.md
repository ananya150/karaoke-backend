# Frontend Developer Guide: Job Status API

## Overview

This guide explains how to monitor job progress in the Karaoke Backend API. The job status endpoint provides real-time updates on audio processing tasks including stem separation, transcription, and beat analysis.

## Quick Start

### 1. Upload a File and Get Job ID
```javascript
const formData = new FormData();
formData.append('file', audioFile);

const uploadResponse = await fetch('/api/process', {
  method: 'POST',
  body: formData
});

const { job_id } = await uploadResponse.json();
// Example: "550e8400-e29b-41d4-a716-446655440000"
```

### 2. Monitor Job Progress
```javascript
const statusResponse = await fetch(`/api/status/${job_id}`);
const status = await statusResponse.json();
```

---

## API Endpoint

**`GET /api/status/{job_id}`**

Returns comprehensive job status including overall progress and individual task details.

### URL Parameters
- `job_id` (string, required): The unique job identifier returned from the upload endpoint

### Response Format

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 45,
  "current_step": "stem_separation",
  "created_at": "2024-01-01T10:00:00",
  "updated_at": "2024-01-01T10:02:30",
  "processing_time": 150.5,
  "error_message": null,
  
  "stem_separation": {
    "status": "processing",
    "progress": 65,
    "vocals_path": null,
    "drums_path": null,
    "bass_path": null,
    "other_path": null,
    "processing_time": null,
    "error": null
  },
  
  "transcription": {
    "status": "skipped",
    "progress": 100,
    "transcription_path": null,
    "language": null,
    "word_count": null,
    "processing_time": null,
    "error": null
  },
  
  "beat_analysis": {
    "status": "queued",
    "progress": 0,
    "tempo_bpm": null,
    "beat_count": null,
    "time_signature": null,
    "beat_confidence": null,
    "rhythm_regularity": null,
    "processing_time": null,
    "error": null
  },
  
  "audio_duration": 180.0,
  "file_size": 4500000
}
```

---

## Status Values

### Main Job Status
- `"queued"` - Job is waiting to be processed
- `"processing"` - Job is currently being processed
- `"completed"` - Job completed successfully
- `"failed"` - Job failed with errors
- `"unknown"` - Status could not be determined (rare)

### Individual Task Status
- `"queued"` - Task is waiting to start
- `"processing"` - Task is currently running
- `"completed"` - Task finished successfully
- `"failed"` - Task failed with errors
- `"skipped"` - Task was skipped (e.g., transcription is currently disabled)

### Processing Steps
- `"validation"` - Validating uploaded file
- `"stem_separation"` - Separating audio into stems (vocals, drums, bass, other)
- `"transcription"` - Converting vocals to text (currently skipped)
- `"beat_analysis"` - Analyzing rhythm and tempo
- `"completed"` - All processing finished

---

## Real-World Example Responses

### 1. Job Just Started
```json
{
  "job_id": "abc123",
  "status": "queued",
  "progress": 10,
  "current_step": "validation",
  "processing_time": 0.1,
  "stem_separation": {
    "status": "queued",
    "progress": 0
  },
  "transcription": {
    "status": "queued", 
    "progress": 0
  },
  "beat_analysis": {
    "status": "queued",
    "progress": 0
  }
}
```

### 2. Stem Separation in Progress
```json
{
  "job_id": "abc123",
  "status": "processing",
  "progress": 45,
  "current_step": "stem_separation",
  "processing_time": 30.5,
  "stem_separation": {
    "status": "processing",
    "progress": 65,
    "vocals_path": null,
    "processing_time": null
  },
  "transcription": {
    "status": "queued",
    "progress": 0
  },
  "beat_analysis": {
    "status": "queued", 
    "progress": 0
  }
}
```

### 3. Job Completed Successfully
```json
{
  "job_id": "abc123",
  "status": "completed",
  "progress": 100,
  "current_step": "completed",
  "processing_time": 107.1,
  "stem_separation": {
    "status": "completed",
    "progress": 100,
    "vocals_path": "/storage/abc123/espresso_vocals.wav",
    "drums_path": "/storage/abc123/espresso_drums.wav",
    "bass_path": "/storage/abc123/espresso_bass.wav",
    "other_path": "/storage/abc123/espresso_other.wav",
    "processing_time": 65.2
  },
  "transcription": {
    "status": "skipped",
    "progress": 100,
    "transcription_path": null
  },
  "beat_analysis": {
    "status": "completed",
    "progress": 100,
    "tempo_bpm": 120.5,
    "beat_count": 240,
    "time_signature": "4/4",
    "beat_confidence": 0.95,
    "processing_time": 2.1
  }
}
```

### 4. Job Failed
```json
{
  "job_id": "abc123",
  "status": "failed",
  "progress": 0,
  "current_step": "stem_separation",
  "processing_time": 5.2,
  "error_message": "Audio processing failed: Unsupported audio format",
  "stem_separation": {
    "status": "failed",
    "progress": 0,
    "error": "Unsupported audio format: .xyz"
  }
}
```

---

## Implementation Examples

### React Hook for Job Monitoring

```javascript
import { useState, useEffect, useCallback } from 'react';

export function useJobStatus(jobId) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(`/api/status/${jobId}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setStatus(data);
      setError(null);
      
      // Stop polling if job is complete or failed
      if (data.status === 'completed' || data.status === 'failed') {
        setLoading(false);
      }
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    if (!jobId) return;

    // Initial fetch
    fetchStatus();

    // Poll every 3 seconds until complete
    const interval = setInterval(() => {
      if (status?.status === 'completed' || status?.status === 'failed') {
        clearInterval(interval);
        return;
      }
      fetchStatus();
    }, 3000);

    return () => clearInterval(interval);
  }, [jobId, fetchStatus, status?.status]);

  return { status, loading, error };
}
```

### Vue.js Component Example

```vue
<template>
  <div class="job-status">
    <div v-if="loading" class="spinner">Loading...</div>
    
    <div v-else-if="error" class="error">
      Error: {{ error }}
    </div>
    
    <div v-else class="status-details">
      <h3>Job Status: {{ status.status.toUpperCase() }}</h3>
      
      <!-- Overall Progress -->
      <div class="progress-bar">
        <div 
          class="progress-fill" 
          :style="{ width: status.progress + '%' }"
        ></div>
      </div>
      <p>{{ status.progress }}% - {{ status.current_step }}</p>
      
      <!-- Individual Tasks -->
      <div class="tasks">
        <div class="task">
          <h4>Stem Separation</h4>
          <div class="task-status" :class="status.stem_separation.status">
            {{ status.stem_separation.status }} ({{ status.stem_separation.progress }}%)
          </div>
        </div>
        
        <div class="task">
          <h4>Transcription</h4>
          <div class="task-status" :class="status.transcription.status">
            {{ status.transcription.status }} ({{ status.transcription.progress }}%)
          </div>
        </div>
        
        <div class="task">
          <h4>Beat Analysis</h4>
          <div class="task-status" :class="status.beat_analysis.status">
            {{ status.beat_analysis.status }} ({{ status.beat_analysis.progress }}%)
          </div>
        </div>
      </div>
      
      <!-- Results (when completed) -->
      <div v-if="status.status === 'completed'" class="results">
        <h4>Results Ready!</h4>
        <p>Processing took {{ status.processing_time }}s</p>
        <p>Tempo: {{ status.beat_analysis.tempo_bpm }} BPM</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['jobId'],
  data() {
    return {
      status: null,
      loading: true,
      error: null,
      pollInterval: null
    };
  },
  
  mounted() {
    this.startPolling();
  },
  
  beforeUnmount() {
    this.stopPolling();
  },
  
  methods: {
    async fetchStatus() {
      try {
        const response = await fetch(`/api/status/${this.jobId}`);
        const data = await response.json();
        this.status = data;
        this.error = null;
        
        if (data.status === 'completed' || data.status === 'failed') {
          this.stopPolling();
        }
      } catch (err) {
        this.error = err.message;
        this.stopPolling();
      } finally {
        this.loading = false;
      }
    },
    
    startPolling() {
      this.fetchStatus();
      this.pollInterval = setInterval(this.fetchStatus, 3000);
    },
    
    stopPolling() {
      if (this.pollInterval) {
        clearInterval(this.pollInterval);
        this.pollInterval = null;
      }
    }
  }
};
</script>

<style scoped>
.progress-bar {
  width: 100%;
  height: 20px;
  background: #f0f0f0;
  border-radius: 10px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #45a049);
  transition: width 0.3s ease;
}

.task-status.processing { color: #ff9800; }
.task-status.completed { color: #4caf50; }
.task-status.failed { color: #f44336; }
.task-status.skipped { color: #9e9e9e; }
.task-status.queued { color: #2196f3; }
</style>
```

### Plain JavaScript Example

```javascript
class JobStatusMonitor {
  constructor(jobId, onUpdate, onComplete, onError) {
    this.jobId = jobId;
    this.onUpdate = onUpdate;
    this.onComplete = onComplete;
    this.onError = onError;
    this.pollInterval = null;
    this.isPolling = false;
  }

  async fetchStatus() {
    try {
      const response = await fetch(`/api/status/${this.jobId}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const status = await response.json();
      
      // Call update callback
      if (this.onUpdate) {
        this.onUpdate(status);
      }
      
      // Check if job is complete
      if (status.status === 'completed') {
        this.stopPolling();
        if (this.onComplete) {
          this.onComplete(status);
        }
      } else if (status.status === 'failed') {
        this.stopPolling();
        if (this.onError) {
          this.onError(status.error_message || 'Job failed');
        }
      }
      
      return status;
      
    } catch (error) {
      this.stopPolling();
      if (this.onError) {
        this.onError(error.message);
      }
      throw error;
    }
  }

  startPolling(intervalMs = 3000) {
    if (this.isPolling) return;
    
    this.isPolling = true;
    
    // Initial fetch
    this.fetchStatus();
    
    // Set up polling
    this.pollInterval = setInterval(() => {
      this.fetchStatus();
    }, intervalMs);
  }

  stopPolling() {
    this.isPolling = false;
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }
}

// Usage Example
const monitor = new JobStatusMonitor(
  'your-job-id-here',
  
  // onUpdate callback
  (status) => {
    console.log(`Progress: ${status.progress}%`);
    updateProgressBar(status.progress);
    updateTaskStatuses(status);
  },
  
  // onComplete callback
  (status) => {
    console.log('Job completed!', status);
    showResults(status);
  },
  
  // onError callback
  (error) => {
    console.error('Job failed:', error);
    showError(error);
  }
);

// Start monitoring
monitor.startPolling();
```

---

## Best Practices

### 1. Polling Frequency
- **Recommended**: Poll every 3-5 seconds
- **Too frequent**: < 1 second (unnecessary server load)
- **Too slow**: > 10 seconds (poor user experience)

### 2. Error Handling
```javascript
// Always handle network errors
try {
  const response = await fetch(`/api/status/${jobId}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const status = await response.json();
} catch (error) {
  console.error('Failed to fetch status:', error);
  // Show user-friendly error message
}
```

### 3. Stop Polling When Complete
```javascript
// Stop polling to save resources
if (status.status === 'completed' || status.status === 'failed') {
  clearInterval(pollInterval);
}
```

### 4. Progress Visualization
```javascript
// Show progress for each task
function updateTaskProgress(taskName, taskStatus) {
  const progressBar = document.getElementById(`${taskName}-progress`);
  const statusText = document.getElementById(`${taskName}-status`);
  
  progressBar.style.width = `${taskStatus.progress}%`;
  statusText.textContent = `${taskStatus.status} (${taskStatus.progress}%)`;
  statusText.className = `status ${taskStatus.status}`;
}
```

### 5. User Feedback
- Show overall progress prominently
- Display current processing step
- Provide estimated time remaining when possible
- Show individual task status for detailed feedback

---

## Troubleshooting

### Common Issues

1. **404 Error**: Job ID not found
   - Check if job ID is correct
   - Job may have expired (jobs are cleaned up after 24 hours)

2. **Status Stuck**: Progress not updating
   - Check if backend services are running
   - Verify Celery worker is active
   - Check server logs for errors

3. **Long Processing Time**: Stem separation taking 60+ seconds
   - This is normal for longer audio files
   - Progress should update every 2-3 seconds during processing

### HTTP Status Codes
- `200`: Success
- `404`: Job not found
- `500`: Server error

---

## Testing

You can test the API using curl:

```bash
# Check job status
curl http://localhost:8000/api/status/YOUR_JOB_ID

# Pretty print JSON response
curl -s http://localhost:8000/api/status/YOUR_JOB_ID | jq '.'
```

---

## Summary

The job status API provides comprehensive real-time monitoring of audio processing jobs. Key points:

- Poll every 3-5 seconds for optimal balance of responsiveness and efficiency
- Monitor both overall progress and individual task status
- Handle completion and error states appropriately
- Stop polling when job is complete to save resources
- Provide clear user feedback throughout the process

### Getting Results and Downloads

Once a job is completed, use the `/api/results/{job_id}` endpoint to get download links:

```javascript
// After job is completed
const results = await fetch(`/api/results/${job_id}`).then(r => r.json());

// Download links are provided in the response
const downloadLinks = results.download_links;
// Example:
// {
//   "vocals_stem": "/api/files/job_id/espresso_vocals.wav",
//   "drums_stem": "/api/files/job_id/espresso_drums.wav",
//   "bass_stem": "/api/files/job_id/espresso_bass.wav",
//   "other_stem": "/api/files/job_id/espresso_other.wav"
// }

// Use these URLs to download or play the files
const vocalsUrl = `http://localhost:8000${downloadLinks.vocals_stem}`;
```

The API is designed to give your users detailed insight into the processing pipeline, from initial upload through final completion of all karaoke preparation tasks. 