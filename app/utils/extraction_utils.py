"""
Utility functions for website data extraction.
"""

import time
from typing import Optional, Dict, Any
from app.core.logging import logger
from app.schemas.extraction import WebsiteExtraction

# In-memory store for tracking extraction status (supplement to database)
extraction_statuses: Dict[str, Dict[str, Any]] = {}
extraction_results: Dict[str, Dict[str, Any]] = {}


def get_extraction_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the current status of an extraction job from cache.
    
    Args:
        job_id: ID of the extraction job (Hyperbrowser jobId)
        
    Returns:
        Optional[Dict[str, Any]]: The extraction status, or None if not found
    """
    return extraction_statuses.get(job_id)


def update_extraction_status(
    job_id: str, 
    status: str, 
    message: Optional[str] = None,
    result_url: Optional[str] = None,
    error: Optional[str] = None
) -> None:
    """
    Update the status of an extraction job in cache.
    
    Args:
        job_id: ID of the extraction job
        status: New status value
        message: Optional status message
        result_url: Optional URL to access the result
        error: Optional error message
    """
    if job_id in extraction_statuses:
        extraction_statuses[job_id]["status"] = status
        extraction_statuses[job_id]["updated_at"] = time.time()
        
        if message:
            extraction_statuses[job_id]["message"] = message
            
        if result_url:
            extraction_statuses[job_id]["result_url"] = result_url
            
        if error:
            extraction_statuses[job_id]["error"] = error
            
        logger.info(f"Updated extraction status for {job_id}: {status} - {message}")


def create_extraction_status(url: str, job_id: str, org_id: int) -> Dict[str, Any]:
    """
    Create a new extraction status entry in cache.
    
    Args:
        url: The URL being extracted
        job_id: Hyperbrowser job ID
        org_id: Organization ID (integer)
        
    Returns:
        Dict[str, Any]: The newly created status
    """
    # Create initial status
    current_time = time.time()
    status = {
        "job_id": job_id,
        "url": url,
        "org_id": org_id,
        "status": "queued",
        "created_at": current_time,
        "updated_at": current_time,
        "message": "Extraction job queued",
        "result_url": f"/api/v1/extraction/extract/{job_id}",
        "error": None
    }
    
    # Store in the in-memory store
    extraction_statuses[job_id] = status
    
    logger.info(f"Created extraction status for {job_id} (URL: {url}, Org: {org_id})")
    
    return status


def process_extraction_result(
    result_data: Dict[str, Any],
    job_id: str,
    url: str,
    org_id: int
) -> Optional[WebsiteExtraction]:
    """
    Process and validate extraction result data.
    
    Args:
        result_data: The raw data from the extraction
        job_id: ID of the extraction job
        url: URL that was extracted
        org_id: Organization ID (integer)
        
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
        
        # Add required fields if not present
        if 'url' not in data:
            data['url'] = url
        
        # Create and validate WebsiteExtraction object
        extraction_data = WebsiteExtraction(**data)
        
        # Store result in memory for later retrieval
        extraction_results[job_id] = {
            "data": extraction_data.dict(),
            "org_id": org_id,
            "processed_at": time.time()
        }
        
        return extraction_data
    except Exception as e:
        logger.error(f"Error processing extraction result: {str(e)}")
        return None


def get_extraction_result(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the extraction result for a job from cache.
    
    Args:
        job_id: ID of the extraction job
        
    Returns:
        Optional[Dict[str, Any]]: The extraction result, or None if not found
    """
    return extraction_results.get(job_id)


def clear_old_cache_entries(max_age_hours: int = 24) -> None:
    """
    Clear old cache entries to prevent memory leaks.
    
    Args:
        max_age_hours: Maximum age in hours before entries are removed
    """
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    
    # Clear old status entries
    old_status_keys = []
    for job_id, status in extraction_statuses.items():
        if current_time - status.get("updated_at", 0) > max_age_seconds:
            old_status_keys.append(job_id)
    
    for job_id in old_status_keys:
        del extraction_statuses[job_id]
        logger.info(f"Removed old status entry for job {job_id}")
    
    # Clear old result entries
    old_result_keys = []
    for job_id, result in extraction_results.items():
        if current_time - result.get("processed_at", 0) > max_age_seconds:
            old_result_keys.append(job_id)
    
    for job_id in old_result_keys:
        del extraction_results[job_id]
        logger.info(f"Removed old result entry for job {job_id}")
    
    if old_status_keys or old_result_keys:
        logger.info(f"Cache cleanup completed: removed {len(old_status_keys)} status entries and {len(old_result_keys)} result entries")


def get_cache_stats() -> Dict[str, Any]:
    """
    Get statistics about the current cache state.
    
    Returns:
        Dict[str, Any]: Cache statistics
    """
    return {
        "status_entries": len(extraction_statuses),
        "result_entries": len(extraction_results),
        "memory_usage_estimate_kb": (
            len(str(extraction_statuses)) + len(str(extraction_results))
        ) / 1024
    }