#!/usr/bin/env python3
"""
Full system test for karaoke backend processing with espresso.mp3
Tests the complete pipeline: upload -> stem separation -> transcription -> beat analysis
"""

import requests
import time
import json
from pathlib import Path

# Configuration
BASE_URL = "http://127.0.0.1:8000"
AUDIO_FILE = "./espresso.mp3"  # Make sure this exists in current directory

def upload_file():
    """Upload audio file and get job ID"""
    print("🎵 Uploading espresso.mp3...")
    
    if not Path(AUDIO_FILE).exists():
        print(f"❌ Audio file not found: {AUDIO_FILE}")
        return None
    
    with open(AUDIO_FILE, 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{BASE_URL}/api/process", files=files)
    
    if response.status_code == 200:
        data = response.json()
        job_id = data['job_id']
        print(f"✅ Upload successful! Job ID: {job_id}")
        return job_id
    else:
        print(f"❌ Upload failed: {response.status_code} - {response.text}")
        return None

def monitor_job(job_id):
    """Monitor job progress with detailed status updates every 2 seconds"""
    print(f"\n🔍 Monitoring job {job_id}...")
    print("=" * 80)
    
    start_time = time.time()
    last_status = None
    last_progress = None
    
    while True:
        try:
            response = requests.get(f"{BASE_URL}/api/status/{job_id}")
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'UNKNOWN')
                progress = data.get('progress', 0)
                current_time = time.time() - start_time
                
                # Show status change
                if status != last_status or progress != last_progress:
                    print(f"[{current_time:6.1f}s] Status: {status:12} | Progress: {progress:3}%")
                    
                    # Show detailed information for each stage
                    if 'stage_details' in data:
                        stage_details = data['stage_details']
                        for stage, details in stage_details.items():
                            if details.get('status') == 'processing':
                                stage_progress = details.get('progress', 0)
                                print(f"         └─ {stage}: {stage_progress}%")
                    
                    # Show additional details
                    if status == 'PROCESSING':
                        if 'current_stage' in data:
                            print(f"         Current stage: {data['current_stage']}")
                        
                        # Show stem separation progress
                        if 'stem_separation_progress' in data:
                            stem_progress = data['stem_separation_progress']
                            print(f"         Stem separation: {stem_progress}%")
                        
                        # Show beat analysis progress
                        if 'beat_analysis_progress' in data:
                            beat_progress = data['beat_analysis_progress']
                            print(f"         Beat analysis: {beat_progress}%")
                    
                    last_status = status
                    last_progress = progress
                
                # Check if job is complete
                if status in ['COMPLETED', 'FAILED']:
                    print(f"\n🎯 Job {status.lower()} after {current_time:.1f} seconds")
                    
                    if status == 'COMPLETED':
                        print("\n📊 Final Results:")
                        if 'results' in data:
                            results = data['results']
                            
                            # Stem separation results
                            if 'stem_separation' in results:
                                stems = results['stem_separation']
                                print(f"   🎼 Stems: {stems.get('stems_count', 0)} files")
                                print(f"   ⏱️  Processing time: {stems.get('processing_time', 0):.1f}s")
                            
                            # Beat analysis results
                            if 'beat_analysis' in results:
                                beats = results['beat_analysis']
                                print(f"   🥁 Tempo: {beats.get('tempo_bpm', 0)} BPM")
                                print(f"   📊 Beat count: {beats.get('beat_count', 0)}")
                                print(f"   🎵 Time signature: {beats.get('time_signature', 'Unknown')}")
                            
                            # Transcription results (if enabled)
                            if 'transcription' in results:
                                transcription = results['transcription']
                                print(f"   📝 Words: {transcription.get('word_count', 0)}")
                                print(f"   🌍 Language: {transcription.get('language', 'Unknown')}")
                    
                    elif status == 'FAILED':
                        print(f"❌ Error: {data.get('error', 'Unknown error')}")
                    
                    break
                
            else:
                print(f"❌ Status check failed: {response.status_code}")
                break
                
        except requests.RequestException as e:
            print(f"❌ Request error: {e}")
            break
        except KeyboardInterrupt:
            print(f"\n⏹️  Monitoring stopped by user")
            break
        
        # Wait 2 seconds before next check
        time.sleep(2)

def get_results(job_id):
    """Get final results"""
    print(f"\n📋 Getting results for job {job_id}...")
    
    response = requests.get(f"{BASE_URL}/api/results/{job_id}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Results retrieved successfully!")
        
        # Show file structure
        if 'files' in data:
            files = data['files']
            print(f"\n📁 Generated files ({len(files)} total):")
            for file_info in files:
                file_path = file_info.get('path', 'Unknown')
                file_size = file_info.get('size', 0)
                print(f"   📄 {file_path} ({file_size} bytes)")
        
        # Show processing summary
        if 'processing_summary' in data:
            summary = data['processing_summary']
            print(f"\n⏱️  Processing Summary:")
            print(f"   Total time: {summary.get('total_time', 0):.1f}s")
            print(f"   Stages completed: {summary.get('stages_completed', 0)}")
        
        return data
    else:
        print(f"❌ Failed to get results: {response.status_code} - {response.text}")
        return None

def main():
    """Run complete system test"""
    print("🎤 Karaoke Backend Full System Test")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Server not responding. Please start the server first.")
            return
    except requests.RequestException:
        print("❌ Cannot connect to server. Please start the server first.")
        return
    
    print("✅ Server is running")
    
    # Upload file
    job_id = upload_file()
    if not job_id:
        return
    
    # Monitor progress
    monitor_job(job_id)
    
    # Get final results
    results = get_results(job_id)
    
    print("\n🎉 Test completed!")

if __name__ == "__main__":
    main() 