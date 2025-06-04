"""
Database operations for content library functionality.
"""
from datetime import datetime as dt
from typing import List, Dict, Any, Optional, Union
from uuid import UUID
from app.core.logging import logger
from app.core.database import supabase
import json

# Table names for database operations (Updated to match new schema)
ORG_CONTENT_SOURCES_TABLE = "org_content_sources"  # Updated from "orgcontentsources"
ORG_CONTENT_LIBRARY_TABLE = "org_content_library"  # Updated from "orgcontentlibrary"
CONTENT_LIB_JOBS_TABLE = "contentlibraryjobs"  # LEGACY - will use processing_jobs
PROCESSING_JOBS_TABLE = "processing_jobs"  # NEW - unified job processing
CONTENT_LIBRARY_RESULTS_TABLE = "content_library_results"  # NEW - structured results

async def create_content_library_job(job_id: str, org_id: UUID, source_ids: List[UUID], user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new content library processing job.
    UPDATED: Now uses unified processing_jobs table.

    Args:
        job_id: Unique job ID
        org_id: Organization ID
        source_ids: List of content source IDs to process
        user_id: User ID who created the job

    Returns:
        The created job record
    """
    # Import the unified job creation function
    from app.core.database import create_processing_job

    # Use the new unified job processing system
    job_record = await create_processing_job(
        job_id=job_id,
        job_type="content_library",
        org_id=str(org_id),
        user_id=user_id,
        source_ids=[str(source_id) for source_id in source_ids],
        total_items=len(source_ids),
        metadata={
            "source_count": len(source_ids),
            "processed_count": 0,
            "source_ids": [str(source_id) for source_id in source_ids]
        }
    )

    if job_record:
        logger.info(f"Created content library job: {job_id} for org_id: {org_id}")
        return job_record
    else:
        # Fallback record for backward compatibility
        fallback_record = {
            "job_id": job_id,
            "org_id": str(org_id),
            "status": "pending",
            "source_count": len(source_ids),
            "processed_count": 0,
            "source_ids": [str(source_id) for source_id in source_ids],
            "created_by": user_id,
            "created_at": dt.now().isoformat(),
            "updated_at": dt.now().isoformat()
        }
        logger.warning(f"Using fallback record for content library job {job_id}")
        return fallback_record

async def get_content_library_job(job_id: str, org_id: Optional[UUID] = None) -> Optional[Dict[str, Any]]:
    """
    Get a content library job by ID.
    
    Args:
        job_id: Unique job ID
        org_id: Optional organization ID for security check
        
    Returns:
        The job record or None if not found
    """
    try:
        query = supabase.table(CONTENT_LIB_JOBS_TABLE).select("*").eq("job_id", job_id)
        
        if org_id:
            query = query.eq("org_id", str(org_id))
            
        response = query.execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting content library job {job_id}: {str(e)}")
        return None

async def update_content_library_job_status(job_id: str, status: str, processed_count: Optional[int] = None, error: Optional[str] = None, org_id: Optional[UUID] = None) -> Optional[Dict[str, Any]]:
    """
    Update the status of a content library job.
    
    Args:
        job_id: Unique job ID
        status: New status (pending, processing, completed, failed)
        processed_count: Optional count of processed sources
        error: Optional error message
        org_id: Optional organization ID for security check
        
    Returns:
        The updated job record or None if failed
    """
    update_data = {
        "status": status,
        "updated_at": dt.now().isoformat()
    }
    
    if processed_count is not None:
        update_data["processed_count"] = processed_count
        
    if error:
        update_data["error"] = error
    
    try:
        query = supabase.table(CONTENT_LIB_JOBS_TABLE).update(update_data).eq("job_id", job_id)
        
        if org_id:
            query = query.eq("org_id", str(org_id))
            
        response = query.execute()
        logger.info(f"Updated content library job {job_id} status to {status}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating content library job status: {str(e)}")
        return None

async def get_content_sources(source_ids: List[UUID], org_id: UUID) -> List[Dict[str, Any]]:
    """
    Get content sources by IDs.
    
    Args:
        source_ids: List of content source IDs
        org_id: Organization ID
        
    Returns:
        List of content source records
    """
    try:
        source_id_strings = [str(source_id) for source_id in source_ids]
        
        # Get sources that match the source_ids and org_id
        response = supabase.table(ORG_CONTENT_SOURCES_TABLE).select("*").in_("id", source_id_strings).eq("org_id", str(org_id)).execute()
        
        if response.data:
            return response.data
        return []
    except Exception as e:
        logger.error(f"Error getting content sources: {str(e)}")
        return []

async def store_content_library_item(org_id: UUID, source_id: UUID, content_type: str, content: Dict[str, Any], user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Store a content library item.
    
    Args:
        org_id: Organization ID
        source_id: Content source ID
        content_type: Type of content (e.g., 'services', 'team', 'case_studies')
        content: Content data
        user_id: User ID who created the item
        
    Returns:
        The created item record or None if failed
    """
    item_record = {
        "org_id": str(org_id),
        "source_id": str(source_id),
        "content_type": content_type,
        "content": content,
        "created_by": user_id,
        "created_at": dt.now().isoformat(),
        "updated_at": dt.now().isoformat()
    }
    
    try:
        response = supabase.table(ORG_CONTENT_LIBRARY_TABLE).insert(item_record).execute()
        logger.info(f"Stored content library item of type {content_type} for org_id: {org_id}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error storing content library item: {str(e)}")
        return None

async def store_business_information(org_id: UUID, source_ids: List[UUID], business_info: Union[Dict[str, Any], str], user_id: Optional[str] = None):
    """
    Store complete business information in content library as a single document.
    
    Args:
        org_id: Organization ID
        source_ids: List of content source IDs
        business_info: Complete structured business information (can be dict or string)
        user_id: User ID who initiated the process
        
    Returns:
        Result of the storage operation
    """
    results = {
        "stored_items": 0,
        "source_ids": [str(sid) for sid in source_ids],
        "content_type": "business_information"
    }
    
    try:
        # Get the primary source ID (first in the list)
        primary_source_id = source_ids[0] if source_ids else None
        
        if not primary_source_id:
            return {"error": "No source ID provided"}
        
        # Ensure business_info is properly formatted
        if isinstance(business_info, str):
            # If it's a string that looks like JSON, try to parse it
            if business_info.strip().startswith('{'):
                try:
                    business_info = json.loads(business_info)
                except json.JSONDecodeError:
                    # If it's not valid JSON, wrap it in a content field
                    business_info = {"content": business_info}
            else:
                # For plain text/markdown, wrap it in a content field
                business_info = {"content": business_info}
        
        # Ensure we have a dictionary
        if not isinstance(business_info, dict):
            business_info = {"content": str(business_info)}
        
        # Store the complete business information as a single document
        item = await store_content_library_item(
            org_id=org_id,
            source_id=primary_source_id,
            content_type="business_information",
            content=business_info,
            user_id=user_id
        )
        
        if item:
            results["stored_items"] = 1
            logger.info(f"Stored complete business information for org_id: {org_id}")
            return results
        else:
            return {"error": "Failed to store business information"}
            
    except Exception as e:
        error_msg = f"Error storing business information: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

async def get_content_library_results(job_id: str, org_id: UUID) -> Dict[str, Any]:
    """
    Get the results of a content library processing job.
    
    Args:
        job_id: Unique job ID
        org_id: Organization ID
        
    Returns:
        Job information and content library items
    """
    try:
        # Get the job details
        job = await get_content_library_job(job_id, org_id)
        if not job:
            return {"error": "Job not found or access denied"}
        
        # Get the primary source ID
        source_id = job.get("source_ids", [None])[0] if job.get("source_ids") else None
        if not source_id:
            return {"error": "No source ID found in job"}
        
        # Get the complete business information document
        result = supabase.table(ORG_CONTENT_LIBRARY_TABLE) \
            .select("*") \
            .eq("org_id", str(org_id)) \
            .eq("source_id", str(source_id)) \
            .eq("content_type", "business_information") \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        
        if not result.data:
            return {
                "job_id": job_id,
                "org_id": str(org_id),
                "status": job.get("status", "unknown"),
                "source_count": len(job.get("source_ids", [])),
                "processed_count": job.get("processed_count", 0),
                "data": {},
                "error": None
            }
        
        # Get the first (most recent) result
        content_data = result.data[0].get("content", {}) if result.data else {}
        
        # Return the complete business information
        return {
            "job_id": job_id,
            "org_id": str(org_id),
            "status": job.get("status", "unknown"),
            "source_count": len(job.get("source_ids", [])),
            "processed_count": job.get("processed_count", 0),
            "data": content_data,
            "error": None
        }
        
    except Exception as e:
        error_msg = f"Error getting content library results: {str(e)}"
        logger.error(error_msg)
        return {
            "job_id": job_id,
            "org_id": str(org_id),
            "status": job.get("status", "unknown") if job else "unknown",
            "error": error_msg
        }
