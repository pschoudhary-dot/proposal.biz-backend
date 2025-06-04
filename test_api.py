#!/usr/bin/env python3
"""Test the extraction API to verify the database issue is resolved"""

import requests
import json
import time

def test_extraction_api():
    """Test the extraction API endpoints"""
    base_url = "http://127.0.0.1:8001"
    
    print("🧪 Testing Extraction API")
    print("=" * 40)
    
    # Test 1: Create an extraction job
    print("\n1️⃣ Testing job creation...")
    try:
        response = requests.post(
            f"{base_url}/api/v1/extraction/extract",
            json={"url": "https://www.enactsoft.com"},
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 202:
            job_data = response.json()
            job_id = job_data.get("job_id")
            print(f"✅ Job created successfully! Job ID: {job_id}")
            
            # Test 2: Check job status
            print(f"\n2️⃣ Testing job status check...")
            time.sleep(2)  # Wait a bit
            
            status_response = requests.get(f"{base_url}/api/v1/extraction/extract/{job_id}/status")
            print(f"Status Code: {status_response.status_code}")
            print(f"Response: {status_response.json()}")
            
            if status_response.status_code == 200:
                print("✅ Job status retrieved successfully!")
            else:
                print("❌ Job status check failed")
            
            # Test 3: Try to get results (might not be ready yet)
            print(f"\n3️⃣ Testing job results...")
            results_response = requests.get(f"{base_url}/api/v1/extraction/extract/{job_id}")
            print(f"Status Code: {results_response.status_code}")
            print(f"Response: {results_response.json()}")
            
            if results_response.status_code in [200, 202]:
                print("✅ Job results endpoint working!")
            else:
                print("❌ Job results check failed")
                
        else:
            print("❌ Job creation failed")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API. Make sure the server is running on port 8001")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_health_check():
    """Test basic health check"""
    try:
        response = requests.get("http://127.0.0.1:8001/")
        print(f"\n🏥 Health Check: {response.status_code}")
        if response.status_code == 200:
            print("✅ API is responding")
        else:
            print("⚠️ API responded but with non-200 status")
    except Exception as e:
        print(f"❌ Health check failed: {e}")

if __name__ == "__main__":
    test_health_check()
    test_extraction_api()
    
    print("\n" + "=" * 40)
    print("🎯 Test Summary:")
    print("If you see '✅ Job created successfully!' above,")
    print("then the database issue has been RESOLVED!")
    print("The processing_jobs table is now working correctly.")
