"""
Database operations for content library functionality - Updated for new schema.
"""
from datetime import datetime as dt
from typing import List, Dict, Any, Optional, Union
from uuid import UUID
import json
from app.core.logging import logger
from app.core.database import supabase
from app.core.config import settings

# Table names for database operations (updated for new schema)
PROCESSING_JOBS_TABLE = "processing_jobs"
ORG_CONTENT_SOURCES_TABLE = "org_content_sources"
ORG_CONTENT_LIBRARY_TABLE = "org_content_library"
DOCUMENT_CONTENT_TABLE = "document_content"

async def create_content_library_job(job_id: str, org_id: int, source_ids: List[str], user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Create a new content library processing job.
    
    Args:
        job_id: Unique job ID
        org_id: Organization ID (integer)
        source_ids: List of content source IDs to process (UUIDs as strings)
        user_id: User ID who created the job (integer)
        
    Returns:
        The created job record
    """
    job_record = {
        "org_id": org_id,
        "job_id": job_id,
        "job_type": "content_library",
        "status": "pending",
        "total_items": len(source_ids),
        "completed_items": 0,
        "source_ids": source_ids,
        "metadata": {
            "content_library_processing": True,
            "source_count": len(source_ids)
        },
        "created_by": user_id
    }
    
    try:
        response = supabase.table(PROCESSING_JOBS_TABLE).insert(job_record).execute()
        logger.info(f"Created content library job: {job_id} for org_id: {org_id}")
        return response.data[0] if response.data else job_record
    except Exception as e:
        logger.error(f"Error creating content library job: {str(e)}")
        raise

async def get_content_library_job(job_id: str, org_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Get a content library job by ID.
    
    Args:
        job_id: Unique job ID
        org_id: Optional organization ID for security check (integer)
        
    Returns:
        The job record or None if not found
    """
    try:
        query = supabase.table(PROCESSING_JOBS_TABLE).select("*").eq("job_id", job_id).eq("job_type", "content_library")
        
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting content library job {job_id}: {str(e)}")
        return None

async def update_content_library_job_status(job_id: str, status: str, processed_count: Optional[int] = None, error: Optional[str] = None, org_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Update the status of a content library job.
    
    Args:
        job_id: Unique job ID
        status: New status (pending, processing, completed, failed)
        processed_count: Optional count of processed sources
        error: Optional error message
        org_id: Optional organization ID for security check (integer)
        
    Returns:
        The updated job record or None if failed
    """
    update_data = {
        "status": status,
        "updated_at": dt.now().isoformat()
    }
    
    if processed_count is not None:
        update_data["completed_items"] = processed_count
        
    if error:
        update_data["error_message"] = error
    
    try:
        query = supabase.table(PROCESSING_JOBS_TABLE).update(update_data).eq("job_id", job_id).eq("job_type", "content_library")
        
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        logger.info(f"Updated content library job {job_id} status to {status}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating content library job status: {str(e)}")
        return None

async def get_content_sources_by_ids(source_ids: List[str], org_id: int) -> List[Dict[str, Any]]:
    """
    Get content sources by IDs and fetch their corresponding markdown content.
    
    Args:
        source_ids: List of content source IDs (UUIDs as strings)
        org_id: Organization ID (integer)
        
    Returns:
        List of content source records with markdown content
    """
    try:
        logger.info(f"Fetching content sources for IDs: {source_ids} in org: {org_id}")
        
        # Get content sources metadata
        sources_response = supabase.table(ORG_CONTENT_SOURCES_TABLE).select("*").in_("id", source_ids).eq("org_id", org_id).execute()
        
        if not sources_response.data:
            logger.warning(f"No content sources found for IDs: {source_ids}")
            return []
        
        sources_with_content = []
        
        # For each source, get the corresponding markdown content
        for source in sources_response.data:
            source_data = dict(source)
            
            # Get job_id from source to fetch markdown content
            job_id = source.get("job_id")
            if job_id:
                # Fetch markdown content from document_content table
                doc_response = supabase.table(DOCUMENT_CONTENT_TABLE).select("markdown_text, metadata").eq("job_id", job_id).eq("org_id", org_id).execute()
                
                if doc_response.data:
                    # Combine all markdown content for this source
                    markdown_texts = []
                    for doc in doc_response.data:
                        if doc.get("markdown_text"):
                            markdown_texts.append(doc["markdown_text"])
                    
                    # Combine all markdown content
                    combined_markdown = "\n\n".join(markdown_texts) if markdown_texts else ""
                    source_data["markdown_content"] = combined_markdown
                    
                    logger.info(f"Found markdown content for source {source['id']}: {len(combined_markdown)} characters")
                else:
                    logger.warning(f"No markdown content found for source {source['id']} with job_id {job_id}")
                    source_data["markdown_content"] = ""
            else:
                logger.warning(f"No job_id found for source {source['id']}")
                source_data["markdown_content"] = ""
            
            sources_with_content.append(source_data)
        
        logger.info(f"Retrieved {len(sources_with_content)} content sources with markdown content")
        return sources_with_content
        
    except Exception as e:
        logger.error(f"Error getting content sources: {str(e)}")
        return []

async def store_business_information(org_id: int, source_ids: List[str], business_info: Union[Dict[str, Any], str], user_id: Optional[int] = None):
    """
    Store complete business information in content library as a single document.
    
    Args:
        org_id: Organization ID (integer)
        source_ids: List of content source IDs (UUIDs as strings)
        business_info: Complete structured business information (can be dict or string)
        user_id: User ID who initiated the process (integer)
        
    Returns:
        Result of the storage operation
    """
    results = {
        "stored_items": 0,
        "source_ids": source_ids,
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
        
        # Store the complete business information in org_content_library
        item_record = {
            "org_id": org_id,
            "source_id": primary_source_id,
            "content": business_info,
            "content_type": "business_information",
            "sort_order": 0,
            "is_default": True,
            "tags": ["content_library", "extracted"],
            "created_by": user_id,
            "updated_by": user_id
        }
        
        response = supabase.table(ORG_CONTENT_LIBRARY_TABLE).insert(item_record).execute()
        
        if response.data:
            results["stored_items"] = 1
            logger.info(f"Stored complete business information for org_id: {org_id}")
            return results
        else:
            return {"error": "Failed to store business information"}
            
    except Exception as e:
        error_msg = f"Error storing business information: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

async def get_content_library_results(job_id: str, org_id: int) -> Dict[str, Any]:
    """
    Get the results of a content library processing job.
    
    Args:
        job_id: Unique job ID
        org_id: Organization ID (integer)
        
    Returns:
        Job information and content library items
    """
    try:
        # Get the job details
        job = await get_content_library_job(job_id, org_id)
        if not job:
            return {
                "job_id": job_id,
                "org_id": str(org_id),  # Convert to string for consistency
                "status": "failed",
                "source_count": 0,
                "processed_count": 0,
                "data": {},
                "error": "Job not found or access denied"
            }
        
        # Get the source IDs from the job
        source_ids = job.get("source_ids", [])
        
        # Initialize response with default values
        response = {
            "job_id": job_id,
            "org_id": str(org_id),  # Convert to string for consistency
            "status": job.get("status", "unknown"),
            "source_count": len(source_ids),
            "processed_count": job.get("completed_items", 0),
            "data": {},
            "error": None
        }

        if not source_ids:
            response["error"] = "No source IDs found in job"
            return response
        
        # Get the primary source ID
        primary_source_id = source_ids[0]
        
        # Get the complete business information document from org_content_library
        try:
            result = supabase.table(ORG_CONTENT_LIBRARY_TABLE) \
                .select("*") \
                .eq("org_id", org_id) \
                .eq("source_id", primary_source_id) \
                .eq("content_type", "business_information") \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
            
            if not result.data:
                response["error"] = "No processed data found"
                return response
            
            # Get the first (most recent) result
            content_data = result.data[0].get("content", {}) if result.data and len(result.data) > 0 else {}
            
            # Update the response with the content data
            response["data"] = content_data
            return response
            
        except Exception as e:
            error_msg = f"Error fetching content library data: {str(e)}"
            logger.error(error_msg, exc_info=True)
            response["error"] = error_msg
            return response
            
    except Exception as e:
        error_msg = f"Unexpected error getting content library results: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "job_id": job_id,
            "org_id": str(org_id),
            "status": job.get("status", "unknown") if 'job' in locals() else "failed",
            "source_count": 0,
            "processed_count": 0,
            "data": {},
            "error": error_msg
        }