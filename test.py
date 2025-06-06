# #!/usr/bin/env python3
# """
# Test script to verify and setup Supabase storage bucket.
# Run this script to check if your storage is properly configured.
# """

# import os
# import sys
# from supabase import create_client
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()

# def test_storage_setup():
#     """Test Supabase storage configuration and create bucket if needed."""
    
#     # Get configuration
#     supabase_url = os.getenv("SUPABASE_URL")
#     supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
#     bucket_name = os.getenv("STORAGE_BUCKET_NAME", "websiteassets")
    
#     if not supabase_url:
#         print("❌ SUPABASE_URL not found in environment variables")
#         return False
    
#     if not supabase_service_key:
#         print("❌ SUPABASE_SERVICE_ROLE_KEY not found in environment variables")
#         return False
    
#     print(f"🔧 Testing Supabase storage configuration...")
#     print(f"   URL: {supabase_url}")
#     print(f"   Bucket: {bucket_name}")
    
#     try:
#         # Initialize Supabase client
#         supabase = create_client(supabase_url, supabase_service_key)
#         print("✅ Supabase client initialized successfully")
        
#         # Check if bucket exists
#         try:
#             buckets = supabase.storage.list_buckets()
#             bucket_exists = any(bucket.name == bucket_name for bucket in buckets)
            
#             if bucket_exists:
#                 print(f"✅ Storage bucket '{bucket_name}' exists")
#             else:
#                 print(f"❌ Storage bucket '{bucket_name}' not found")
#                 print("   Available buckets:", [bucket.name for bucket in buckets])
                
#                 # Try to create the bucket
#                 print(f"🔄 Attempting to create bucket '{bucket_name}'...")
#                 try:
#                     create_result = supabase.storage.create_bucket(bucket_name, {"public": True})
#                     print(f"✅ Successfully created bucket '{bucket_name}'")
#                     bucket_exists = True
#                 except Exception as create_error:
#                     print(f"❌ Failed to create bucket: {create_error}")
#                     print("   Please create the bucket manually in the Supabase dashboard")
#                     return False
            
#             if bucket_exists:
#                 # Test upload
#                 test_content = b"Hello, World! This is a test file."
#                 test_file_path = "test/test_file.txt"
                
#                 print(f"🔄 Testing file upload to bucket '{bucket_name}'...")
#                 try:
#                     upload_result = supabase.storage.from_(bucket_name).upload(
#                         test_file_path, 
#                         test_content,
#                         {"content-type": "text/plain", "x-upsert": "true"}
#                     )
                    
#                     # Check if upload was successful (Supabase returns the file data on success)
#                     if upload_result and hasattr(upload_result, 'path'):
#                         print("✅ File upload successful")
#                         print(f"   Uploaded to: {upload_result.path}")
                        
#                         # Test public URL generation
#                         public_url = supabase.storage.from_(bucket_name).get_public_url(test_file_path)
#                         print(f"✅ Public URL generated: {public_url}")
                        
#                         # Clean up test file
#                         try:
#                             supabase.storage.from_(bucket_name).remove([test_file_path])
#                             print("✅ Test file cleaned up")
#                         except Exception as cleanup_error:
#                             print(f"⚠️  Failed to clean up test file: {cleanup_error}")
                        
#                         return True
#                     else:
#                         print(f"❌ File upload failed: {upload_result}")
#                         return False
                        
#                 except Exception as upload_error:
#                     print(f"❌ File upload failed: {upload_error}")
#                     return False
                    
#         except Exception as bucket_error:
#             print(f"❌ Error checking buckets: {bucket_error}")
#             return False
            
#     except Exception as e:
#         print(f"❌ Failed to initialize Supabase client: {e}")
#         return False

# def main():
#     """Main function to run storage tests."""
#     print("🚀 Supabase Storage Setup Test")
#     print("=" * 50)
    
#     success = test_storage_setup()
    
#     print("\n" + "=" * 50)
#     if success:
#         print("✅ Storage setup test completed successfully!")
#         print("   Your storage configuration is ready for document processing.")
#     else:
#         print("❌ Storage setup test failed!")
#         print("   Please check the errors above and follow the setup guide.")
#         print("\n📖 Setup Guide:")
#         print("   1. Ensure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set")
#         print("   2. Create 'websiteassets' bucket in Supabase dashboard")
#         print("   3. Set bucket to public if you need direct URL access")
#         print("   4. Configure appropriate RLS policies")
        
#         sys.exit(1)

# if __name__ == "__main__":
#     main()

'''
docling test
'''


# from docling.document_converter import DocumentConverter
# import time

# source = "https://hkaduwuhnhauzxgyohhn.supabase.co/storage/v1/object/public/websiteassets/documents/4/e5bd90a4-d9ca-4b00-bd02-bc8e34b7d3f8.pdf?"  # PDF path or URL
# converter = DocumentConverter()
# start_time = time.time()
# result = converter.convert(source)
# end_time = time.time()

# print(f"Processing took {end_time - start_time:.2f} seconds")
# print(result.document.export_to_markdown())  # output: "### Docling Technical Report[...]"


'''
apify lcient test
'''
from apify_client import ApifyClient
from app.core.config import settings

client = ApifyClient(settings.APIFY_API_TOKEN)

# Prepare the Actor input
run_input = {
    "http_sources": [{ "url": "https://hkaduwuhnhauzxgyohhn.supabase.co/storage/v1/object/public/websiteassets/documents/4/d51e3a86-280c-425c-92f3-c08bc5b13908.pdf" }],
    "options": { "to_formats": ["md"] },
}

# Run the Actor and wait for it to finish
run = client.actor("vancura/docling").call(run_input=run_input)

# Fetch and print Actor results from the run's dataset (if there are any)
print("💾 Check your data here: https://console.apify.com/storage/datasets/" + run["defaultDatasetId"])
for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    print(item)

# 📚 Want to learn more 📖? Go to → https://docs.apify.com/api/client/python/docs/quick-start