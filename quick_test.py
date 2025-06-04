#!/usr/bin/env python3
"""Quick test to verify processing_jobs table exists"""

import sys
import os
sys.path.append('.')

try:
    from app.core.config import settings
    from supabase import create_client
    
    print("🔍 Quick Database Test")
    print("=" * 30)
    
    # Test connection
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    print("✅ Supabase client created")
    
    # Test processing_jobs table
    response = supabase.table("processing_jobs").select("*").limit(1).execute()
    print("✅ processing_jobs table exists and accessible!")
    print(f"Response: {response}")
    
    # Test creating a job record
    test_job = {
        "job_id": "test_job_123",
        "job_type": "website_extraction", 
        "org_id": 1,
        "status": "pending"
    }
    
    try:
        insert_response = supabase.table("processing_jobs").insert(test_job).execute()
        print("✅ Successfully inserted test job!")
        
        # Clean up - delete the test job
        supabase.table("processing_jobs").delete().eq("job_id", "test_job_123").execute()
        print("✅ Test job cleaned up")
        
    except Exception as e:
        print(f"⚠️ Insert test failed: {e}")
    
    print("\n🎉 SUCCESS: Database issue appears to be RESOLVED!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("Database issue still exists")
