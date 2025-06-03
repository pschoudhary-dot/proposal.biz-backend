# test_docling_server.py
import asyncio
from app.utils.docling_client import DoclingClient

async def test_docling_server():
    client = DoclingClient("http://127.0.0.1:5001")
    
    # Test with a simple text file
    test_content = b"# Test Document\n\nThis is a test."
    
    try:
        # Submit for conversion
        result = await client.convert_file_async(test_content, "trial.txt")
        print(f"Submission result: {result}")
        
        task_id = result.get("task_id")
        if task_id:
            # Wait for completion
            status = await client.wait_for_completion(task_id)
            print(f"Final status: {status}")
            
            # Get result
            final_result = await client.get_result(task_id)
            print(f"Conversion result: {final_result}")
            
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_docling_server())