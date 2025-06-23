#!/usr/bin/env python3
"""
Test script to verify job status endpoint functionality.
Uploads espresso.mp3 and monitors progress every 3 seconds.
"""

import requests
import time
import json
import os
from datetime import datetime


class KaraokeAPITester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def log(self, message, level="INFO"):
        """Log with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def check_health(self):
        """Check if the API is healthy."""
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                self.log(f"API Health: {health_data.get('status', 'unknown')}")
                return True
            else:
                self.log(f"Health check failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Health check error: {e}", "ERROR")
            return False
    
    def upload_file(self, file_path):
        """Upload a file for processing."""
        if not os.path.exists(file_path):
            self.log(f"File not found: {file_path}", "ERROR")
            return None
        
        file_size = os.path.getsize(file_path)
        self.log(f"Uploading file: {file_path} ({file_size:,} bytes)")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'audio/mpeg')}
                response = self.session.post(f"{self.base_url}/api/process", files=files)
            
            if response.status_code == 200:
                result = response.json()
                job_id = result.get('job_id')
                self.log(f"Upload successful! Job ID: {job_id}")
                self.log(f"Status: {result.get('status')}")
                self.log(f"Message: {result.get('message')}")
                return job_id
            else:
                self.log(f"Upload failed: {response.status_code} - {response.text}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"Upload error: {e}", "ERROR")
            return None
    
    def get_job_status(self, job_id):
        """Get job status."""
        try:
            response = self.session.get(f"{self.base_url}/api/status/{job_id}")
            if response.status_code == 200:
                return response.json()
            else:
                self.log(f"Status check failed: {response.status_code} - {response.text}", "ERROR")
                return None
        except Exception as e:
            self.log(f"Status check error: {e}", "ERROR")
            return None
    
    def get_simple_status(self, job_id):
        """Get simplified job status."""
        try:
            response = self.session.get(f"{self.base_url}/api/status/{job_id}/simple")
            if response.status_code == 200:
                return response.json()
            else:
                self.log(f"Simple status check failed: {response.status_code}", "ERROR")
                return None
        except Exception as e:
            self.log(f"Simple status check error: {e}", "ERROR")
            return None
    
    def log_status_details(self, status_data):
        """Log detailed status information."""
        if not status_data:
            return
        
        # Log raw response for debugging (only if needed)
        # self.log(f"Raw status data: {json.dumps(status_data, indent=2)}", "DEBUG")
        
        # Main status
        main_status = status_data.get('status', 'unknown')
        progress = status_data.get('progress', 0)
        current_step = status_data.get('current_step', 'unknown')
        error_message = status_data.get('error_message')
        
        self.log(f"Status: {main_status} | Progress: {progress}% | Step: {current_step}")
        
        if error_message:
            self.log(f"Error: {error_message}", "ERROR")
        
        # Processing times
        if 'processing_time' in status_data:
            self.log(f"Processing time: {status_data['processing_time']:.1f}s")
        
        # Individual task status
        tasks = ['stem_separation', 'transcription', 'beat_analysis']
        for task in tasks:
            if task in status_data:
                task_data = status_data[task]
                if task_data is not None and isinstance(task_data, dict):
                    task_status = task_data.get('status', 'unknown')
                    task_progress = task_data.get('progress', 0)
                    task_error = task_data.get('error')
                    
                    status_msg = f"  {task}: {task_status} ({task_progress}%)"
                    if task_error:
                        status_msg += f" - ERROR: {task_error}"
                    
                    self.log(status_msg)
                else:
                    self.log(f"  {task}: {task_data} (invalid data)")
    
    def monitor_job(self, job_id, poll_interval=3):
        """Monitor job progress until completion."""
        self.log(f"Starting to monitor job: {job_id}")
        self.log(f"Polling every {poll_interval} seconds...")
        
        start_time = time.time()
        poll_count = 0
        
        while True:
            poll_count += 1
            elapsed = time.time() - start_time
            
            self.log(f"\n--- Poll #{poll_count} (elapsed: {elapsed:.1f}s) ---")
            
            # Get detailed status
            status_data = self.get_job_status(job_id)
            if status_data:
                self.log_status_details(status_data)
                
                # Check if job is complete
                job_status = status_data.get('status', '')
                if job_status in ['completed', 'failed', 'completed_with_errors']:
                    self.log(f"\nJob finished with status: {job_status}")
                    
                    if job_status == 'completed':
                        self.log("🎉 Job completed successfully!")
                        self.get_results(job_id)
                    elif job_status == 'completed_with_errors':
                        self.log("⚠️ Job completed with some errors")
                        self.get_results(job_id)
                    else:
                        self.log("❌ Job failed")
                    
                    break
            else:
                self.log("Failed to get job status", "ERROR")
            
            # Wait before next poll
            time.sleep(poll_interval)
    
    def get_results(self, job_id):
        """Get final job results."""
        try:
            response = self.session.get(f"{self.base_url}/api/results/{job_id}")
            if response.status_code == 200:
                results = response.json()
                self.log("\n=== FINAL RESULTS ===")
                self.log(f"Job ID: {results.get('job_id')}")
                self.log(f"Status: {results.get('status')}")
                self.log(f"Total processing time: {results.get('total_processing_time', 0):.1f}s")
                self.log(f"Audio duration: {results.get('audio_duration', 0):.1f}s")
                
                # Download links
                if 'download_links' in results:
                    self.log("\nDownload links:")
                    for file_type, url in results['download_links'].items():
                        self.log(f"  {file_type}: {self.base_url}{url}")
                
                return results
            else:
                self.log(f"Failed to get results: {response.status_code}", "ERROR")
                return None
        except Exception as e:
            self.log(f"Results error: {e}", "ERROR")
            return None


def main():
    """Main test function."""
    print("🎤 Karaoke Backend Job Status Test")
    print("=" * 50)
    
    # Initialize tester
    tester = KaraokeAPITester()
    
    # Check health first
    if not tester.check_health():
        print("❌ API is not healthy. Please start the server first.")
        return
    
    # Upload file
    file_path = "espresso.mp3"
    job_id = tester.upload_file(file_path)
    
    if not job_id:
        print("❌ Failed to upload file")
        return
    
    # Monitor progress
    try:
        tester.monitor_job(job_id, poll_interval=3)
    except KeyboardInterrupt:
        print("\n\n⏹️ Monitoring stopped by user")
        print(f"Job ID: {job_id}")
        print("You can check status manually with:")
        print(f"curl http://localhost:8000/api/status/{job_id}")


if __name__ == "__main__":
    main() 