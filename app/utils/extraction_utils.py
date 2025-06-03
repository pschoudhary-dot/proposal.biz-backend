"""
Utility functions for website data extraction.
"""

import time
from typing import Optional, Dict, Any
from app.core.logging import logger
from app.schemas.extraction import WebsiteExtraction

# In-memory store for tracking extraction status (replace with database in production)
extraction_statuses: Dict[str, Dict[str, Any]] = {}
extraction_results: Dict[str, Dict[str, Any]] = {}


def get_extraction_status(website_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the current status of an extraction job.
    
    Args:
        website_id: ID of the extraction job (Hyperbrowser jobId)
        
    Returns:
        Optional[Dict[str, Any]]: The extraction status, or None if not found
    """
    return extraction_statuses.get(website_id)


def update_extraction_status(
    website_id: str, 
    status: str, 
    message: Optional[str] = None,
    result_url: Optional[str] = None,
    error: Optional[str] = None
) -> None:
    """
    Update the status of an extraction job.
    
    Args:
        website_id: ID of the extraction job
        status: New status value
        message: Optional status message
        result_url: Optional URL to access the result
        error: Optional error message
    """
    if website_id in extraction_statuses:
        extraction_statuses[website_id]["status"] = status
        extraction_statuses[website_id]["updated_at"] = time.time()
        
        if message:
            extraction_statuses[website_id]["message"] = message
            
        if result_url:
            extraction_statuses[website_id]["result_url"] = result_url
            
        if error:
            extraction_statuses[website_id]["error"] = error
            
        logger.info(f"Updated extraction status for {website_id}: {status} - {message}")


def create_extraction_status(url: str, job_id: str) -> Dict[str, Any]:
    """
    Create a new extraction status entry.
    
    Args:
        url: The URL being extracted
        job_id: Hyperbrowser job ID
        
    Returns:
        Dict[str, Any]: The newly created status
    """
    # Create initial status
    current_time = time.time()
    status = {
        "website_id": job_id,
        "url": url,  # Store the URL for retry operations
        "status": "queued",
        "created_at": current_time,
        "updated_at": current_time,
        "message": "Extraction job queued",
        "result_url": f"/api/v1/extraction/result/{job_id}",
        "error": None
    }
    
    # Store in the in-memory store
    extraction_statuses[job_id] = status
    
    logger.info(f"Created extraction status for {job_id} (URL: {url})")
    
    return status


def process_extraction_result(
    result_data: Dict[str, Any],
    website_id: str,
    url: str
) -> Optional[WebsiteExtraction]:
    """
    Process and validate extraction result data.
    
    Args:
        result_data: The raw data from the extraction
        website_id: ID of the extraction job
        url: URL that was extracted
        
    Returns:
        Optional[WebsiteExtraction]: Validated extraction data or None if invalid
    """
    try:
        # Validate the result data format
        if not isinstance(result_data, dict):
            logger.error(f"Invalid result data format: {type(result_data)}")
            return None
        
        # Create a copy of the result data to avoid modifying the original
        data = result_data.copy()
        
        # Add website_id to the data
        data['website_id'] = website_id
        
        # Only add url if it's not already in the data
        if 'url' not in data:
            data['url'] = url
        
        # Create and validate WebsiteExtraction object
        extraction_data = WebsiteExtraction(**data)
        
        # Store result in memory for later retrieval
        extraction_results[website_id] = extraction_data.dict()
        
        return extraction_data
    except Exception as e:
        logger.error(f"Error processing extraction result: {str(e)}")
        return None


def get_extraction_result(website_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the extraction result for a job.
    
    Args:
        website_id: ID of the extraction job
        
    Returns:
        Optional[Dict[str, Any]]: The extraction result, or None if not found
    """
    return extraction_results.get(website_id)