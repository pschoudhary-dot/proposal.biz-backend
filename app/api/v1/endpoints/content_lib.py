"""
API endpoints for content library operations.
"""
import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Path, Query
from pydantic import UUID4
from app.core.logging import logger
from app.core.database_content_lib import (
    create_content_library_job,
    get_content_library_job,
    update_content_library_job_status,
    get_content_sources,
    store_business_information,
    get_content_library_results
)
from app.schemas.content_library import (
    ContentLibraryRequest,
    ContentLibraryStatusResponse,
    ContentLibraryResultResponse,
    BusinessInformationSchema
)
from app.utils.md_to_contentlib import extract_structured_data, process_content_sources
from app.api.deps import get_current_user_id

router = APIRouter()

async def process_content_library_job(job_id: str, org_id: UUID4, source_ids: List[UUID4], user_id: Optional[str] = None):
    """
    Background task to process content library job.
    
    Args:
        job_id: Unique job ID
        org_id: Organization ID
        source_ids: List of content source IDs
        user_id: Optional user ID
    """
    logger.info(f"Starting content library job {job_id} for org_id: {org_id}")
    
    try:
        # Update job status to processing
        await update_content_library_job_status(job_id, "processing", org_id=org_id)
        
        # Get content sources
        logger.info(f"Fetching content sources for job {job_id} with source IDs: {source_ids}")
        sources = await get_content_sources(source_ids, org_id)
        
        # Log detailed information about the sources
        logger.info(f"Retrieved {len(sources)} out of {len(source_ids)} requested sources for job {job_id}")
        
        # Log each source's details for debugging
        for i, source in enumerate(sources, 1):
            source_id = source.get('id', 'unknown')
            content_length = len(str(source.get('content', '')))
            source_type = source.get('source_type', 'unknown')
            name = source.get('name', 'unnamed')
            logger.info(
                f"Source {i}: ID={source_id}, "
                f"Name='{name}', "
                f"Type={source_type}, "
                f"Content Length={content_length} chars"
            )

        # Check if we found any sources
        if not sources:
            error_msg = (
                f"No valid content sources found for the provided IDs. "
                f"Requested IDs: {source_ids}"
            )
            logger.error(f"{error_msg} for job_id: {job_id}")
            await update_content_library_job_status(
                job_id=job_id,
                status="failed",
                error=error_msg,
                org_id=org_id
            )
            return

        # Extract text content from all sources
        content_texts = []
        empty_sources = []
        
        for source in sources:
            source_id = source.get('id', 'unknown')
            # Get both parsed_content and content
            parsed_content = source.get("parsed_content")
            raw_content = source.get("content")
            
            # Log the raw content for debugging (first 200 chars)
            content_preview = str(parsed_content or raw_content or '')[200:] + '...' if (parsed_content or raw_content) else ''
            logger.info(f"Source {source_id} content preview: {content_preview}")
            
            # Use parsed_content if available, otherwise fall back to raw content
            content_to_use = None
            if parsed_content:
                try:
                    # If it's a string that looks like JSON, parse it
                    if isinstance(parsed_content, str) and parsed_content.strip().startswith('{'):
                        try:
                            parsed_json = json.loads(parsed_content)
                            content_to_use = parsed_json
                        except json.JSONDecodeError as je:
                            logger.warning(f"Failed to parse JSON content for source {source_id}: {str(je)}")
                            content_to_use = parsed_content
                    else:
                        content_to_use = parsed_content
                except Exception as e:
                    logger.error(f"Error processing parsed_content for source {source_id}: {str(e)}")
                    content_to_use = parsed_content  # Use as-is if parsing fails
            elif raw_content:
                content_to_use = raw_content
            
            if content_to_use is not None:
                content_texts.append(content_to_use)
                logger.info(f"Successfully added content from source {source_id}")
            else:
                logger.warning(f"No usable content found in source {source_id}")
                empty_sources.append((source_id, "No usable content found"))
        
        # Check if we found any content
        if not content_texts:
            error_msg = (
                f"No valid content found in any of the {len(sources)} sources. "
                f"Empty/Error sources: {empty_sources}"
            )
            logger.error(f"{error_msg} for job_id: {job_id}")
            await update_content_library_job_status(
                job_id=job_id,
                status="failed",
                error=error_msg,
                org_id=org_id
            )
            return
            
        logger.info(f"Successfully extracted content from {len(content_texts)} out of {len(sources)} sources for job {job_id}")
        logger.debug(f"Content samples: {[str(c)[:100] + '...' for c in content_texts[:2]]}")

        # Extract structured data
        logger.info(f"Extracting structured data for job_id: {job_id}")
        try:
            # Directly call extract_structured_data with the content texts
            business_info = await extract_structured_data([str(t) for t in content_texts], org_id)
            logger.info(f"Successfully extracted structured data for job {job_id}")
            
            # Store the complete business information as a single document
            storage_result = await store_business_information(
                org_id=org_id,
                source_ids=source_ids,
                business_info=business_info.dict() if hasattr(business_info, 'dict') else business_info,
                user_id=user_id
            )
            
            if "error" in storage_result:
                raise Exception(f"Storage error: {storage_result['error']}")
                
            # Update job status to completed
            await update_content_library_job_status(
                job_id, 
                "completed",
                processed_count=storage_result.get("stored_items", 1),  # We're storing one complete document now
                org_id=org_id
            )
            logger.info(f"Content library job {job_id} completed successfully")
            
        except Exception as e:
            error_msg = f"Error processing content: {str(e)}"
            logger.error(f"{error_msg} for job_id: {job_id}")
            await update_content_library_job_status(
                job_id, 
                "failed", 
                error=error_msg,
                org_id=org_id
            )
            return

    except Exception as e:
        error_msg = f"Unexpected error in content library job {job_id}: {str(e)}"
        logger.error(error_msg)
        await update_content_library_job_status(
            job_id, 
            "failed", 
            error=error_msg,
            org_id=org_id
        )
        raise

@router.post("/process", response_model=ContentLibraryStatusResponse)
async def process_content_library(
    request: ContentLibraryRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id)
):
    """
    Process content sources and extract structured data.
    
    Args:
        request: Content library request with org_id and source_ids
        background_tasks: FastAPI background tasks
        user_id: Current authenticated user
        
    Returns:
        Job status information
    """
    try:
        # Generate a unique job ID
        job_id = str(uuid.uuid4())
        
        # Create content library job
        job = await create_content_library_job(
            job_id=job_id,
            org_id=request.org_id,
            source_ids=request.source_ids,
            user_id=user_id
        )
        
        # Start background task to process the job
        background_tasks.add_task(
            process_content_library_job,
            job_id=job_id,
            org_id=request.org_id,
            source_ids=request.source_ids,
            user_id=user_id
        )
        
        # Return job status
        return ContentLibraryStatusResponse(
            job_id=job_id,
            org_id=request.org_id,
            status="pending",
            source_count=len(request.source_ids),
            processed_count=0
        )
        
    except Exception as e:
        logger.error(f"Error initiating content library process: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}", response_model=ContentLibraryStatusResponse)
async def get_content_library_status(
    job_id: str = Path(..., description="Unique job ID"),
    org_id: UUID4 = Query(..., description="Organization ID"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get the status of a content library processing job.
    
    Args:
        job_id: Unique job ID
        org_id: Organization ID
        user_id: Current authenticated user
        
    Returns:
        Job status information
    """
    try:
        # Get job information
        job = await get_content_library_job(job_id, org_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Convert UUID to string for response
        #job_org_id = str(job.get("org_id")) if job.get("org_id") else None
        
        # Return job status
        return ContentLibraryStatusResponse(
            job_id=job_id,
            org_id=str(org_id),
            status=job.get("status", "unknown"),
            source_count=job.get("source_count", 0),
            processed_count=job.get("processed_count", 0),
            error=job.get("error")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting content library status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/{job_id}", response_model=ContentLibraryResultResponse)
async def get_content_library_result(
    job_id: str = Path(..., description="Unique job ID"),
    org_id: UUID4 = Query(..., description="Organization ID"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get the results of a content library processing job.
    
    Args:
        job_id: Unique job ID
        org_id: Organization ID
        user_id: Current authenticated user
        
    Returns:
        Job information and complete business information document
    """
    try:
        # Get job information first to check status
        job = await get_content_library_job(job_id, org_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found or access denied")
        
        # If job is still processing, return current status
        if job.get("status") in ["pending", "processing"]:
            return ContentLibraryResultResponse(
                job_id=job_id,
                org_id=str(org_id),
                status=job.get("status", "unknown"),
                source_count=len(job.get("source_ids", [])),
                processed_count=job.get("processed_count", 0),
                data={},
                error="Job not completed yet"
            )
        
        # If job failed, return the error
        if job.get("status") == "failed":
            return ContentLibraryResultResponse(
                job_id=job_id,
                org_id=str(org_id),
                status="failed",
                source_count=len(job.get("source_ids", [])),
                processed_count=job.get("processed_count", 0),
                data={},
                error=job.get("error", "Unknown error occurred during processing")
            )
        
        # Get the complete business information document
        result = await get_content_library_results(job_id, org_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # The result already contains the complete business information
        # No need to reconstruct from multiple content types
        return ContentLibraryResultResponse(
            job_id=job_id,
            org_id=str(org_id),
            status=job.get("status", "unknown"),
            source_count=len(job.get("source_ids", [])),
            processed_count=job.get("processed_count", 0),
            data=result.get("data", {}),
            error=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting content library results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
