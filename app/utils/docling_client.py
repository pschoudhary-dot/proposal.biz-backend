"""
Client for interacting with Docling server API.
"""
import httpx
import asyncio
from typing import Dict, Any, List
from app.core.logging import logger
from app.core.config import settings


class DoclingClient:
    """Client for interacting with Docling server."""
    
    def __init__(self, base_url: str = None):
        self.base_url = (base_url or settings.DOCLING_SERVER_URL).rstrip('/')
        # Longer timeout for document processing
        self.client = httpx.AsyncClient(timeout=300.0)
    
    async def convert_file_async(
        self, 
        file_content: bytes, 
        filename: str,
        to_formats: List[str] = None,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Submit file for async conversion.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            to_formats: List of output formats (default: ["md"])
            options: Additional conversion options
            
        Returns:
            Response with task_id and status
        """
        try:
            # Prepare form data as list of tuples for proper multipart
            form_data = []
            
            # Add file with proper content type
            files = [("files", (filename, file_content, "application/octet-stream"))]
            
            # Add output formats
            formats = to_formats or ["md"]
            for fmt in formats:
                form_data.append(("to_formats", fmt))
            
            # Add boolean fields with defaults
            form_data.extend([
                ("return_as_file", "false"),
                ("do_ocr", str(options.get("do_ocr", True)).lower() if options else "true"),
                ("do_table_structure", str(options.get("do_table_structure", True)).lower() if options else "true")
            ])
            
            # Add any additional options
            if options:
                for key, value in options.items():
                    if key not in ["do_ocr", "do_table_structure"]:  # Already added
                        form_data.append((key, str(value)))
            
            logger.info(f"Submitting {filename} to Docling server for conversion")
            
            response = await self.client.post(
                f"{self.base_url}/v1alpha/convert/file/async",
                files=files,
                data=form_data
            )
            response.raise_for_status()
            
            result = response.json()
            task_id = result.get('task_id')
            if not task_id:
                raise ValueError("No task_id in response from Docling server")
                
            logger.info(f"Docling server accepted file {filename}, task_id: {task_id}")
            return result
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error from Docling server: {e.response.status_code}"
            if e.response.text:
                error_msg += f" - {e.response.text}"
            logger.error(error_msg)
            raise
        except Exception as e:
            logger.error(f"Error submitting file to Docling server: {str(e)}")
            raise
    
    async def check_status(self, task_id: str, wait: int = 0) -> Dict[str, Any]:
        """
        Check conversion task status.
        
        Args:
            task_id: Task ID from Docling server
            wait: Time to wait for status update (0 = immediate return)
            
        Returns:
            Task status information
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/v1alpha/status/poll/{task_id}",
                params={"wait": wait}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error checking task status for {task_id}: {str(e)}")
            raise
    
    async def convert_file_async_with_retry(
        self,
        file_content: bytes,
        filename: str,
        to_formats: List[str] = None,
        options: Dict[str, Any] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Submit file for async conversion with retry logic.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            to_formats: List of output formats (default: ["md"])
            options: Additional conversion options
            max_retries: Maximum number of retry attempts
            
        Returns:
            Response with task_id and status
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await self.convert_file_async(
                    file_content=file_content,
                    filename=filename,
                    to_formats=to_formats,
                    options=options
                )
            except httpx.HTTPStatusError as e:
                # Don't retry client errors (4xx) except for 429 (Too Many Requests)
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    raise
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Network error on attempt {attempt + 1}, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
        
        # If we got here, all retries failed
        error_msg = f"All {max_retries} attempts failed"
        logger.error(f"{error_msg}. Last error: {str(last_error)}")
        raise last_error or Exception(error_msg)
    
    async def get_result(self, task_id: str) -> Dict[str, Any]:
        """
        Get conversion result.
        
        Args:
            task_id: Task ID from Docling server
            
        Returns:
            Conversion result with document content
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/v1alpha/result/{task_id}"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting result for task {task_id}: {str(e)}")
            raise
    
    async def wait_for_completion(
        self, 
        task_id: str, 
        max_attempts: int = 60,
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """
        Wait for a task to complete by polling status.
        
        Args:
            task_id: Task ID to monitor
            max_attempts: Maximum polling attempts
            poll_interval: Seconds between polls
            
        Returns:
            Final task status
        """
        attempt = 0
        
        while attempt < max_attempts:
            try:
                status = await self.check_status(task_id)
                task_status = status.get("task_status", "unknown")
                
                logger.info(f"Task {task_id} status: {task_status} (attempt {attempt + 1}/{max_attempts})")
                
                if task_status == "completed":
                    return status
                elif task_status == "failed":
                    error_msg = status.get("error", "Unknown error")
                    raise Exception(f"Task failed: {error_msg}")
                
                # Wait before next poll
                await asyncio.sleep(poll_interval)
                attempt += 1
                
            except Exception as e:
                logger.error(f"Error polling task {task_id}: {str(e)}")
                if attempt >= max_attempts - 1:
                    raise
                await asyncio.sleep(poll_interval)
                attempt += 1
        
        raise TimeoutError(f"Task {task_id} did not complete within {max_attempts * poll_interval} seconds")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Create a singleton instance
docling_client = DoclingClient()