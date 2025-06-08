"""
API endpoints for content library operations - Updated for new schema.
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Path, Query
from app.core.logging import logger
from app.core.database_content_lib import (
    create_content_library_job,
    get_content_library_job,
    update_content_library_job_status,
    get_content_sources_by_ids,
    store_business_information,
    get_content_library_results
)
from app.schemas.content_library import (
    ContentLibraryRequest,
    ContentLibraryStatusResponse,
    ContentLibraryResultResponse
)
from app.utils.md_to_contentlib import extract_structured_data
from app.api.deps import get_current_user_id
from langfuse.decorators import observe

router = APIRouter()

@observe(name="process_content_library_job")
async def process_content_library_job(job_id: str, org_id: int, source_ids: List[str], user_id: Optional[int] = None):
    """
    Background task to process content library job.
    
    Args:
        job_id: Unique job ID
        org_id: Organization ID (integer)
        source_ids: List of content source IDs (UUIDs as strings)
        user_id: Optional user ID (integer)
    """
    logger.info(f"Starting content library job {job_id} for org_id: {org_id}")
    
    try:
        # Update job status to processing
        await update_content_library_job_status(job_id, "processing", org_id=org_id)
        
        # Get content sources with markdown content
        logger.info(f"Fetching content sources for job {job_id} with source IDs: {source_ids}")
        sources = await get_content_sources_by_ids(source_ids, org_id)
        
        # Log detailed information about the sources
        logger.info(f"Retrieved {len(sources)} out of {len(source_ids)} requested sources for job {job_id}")
        
        # Log each source's details for debugging
        for i, source in enumerate(sources, 1):
            source_id = source.get('id', 'unknown')
            content_length = len(source.get('markdown_content', ''))
            source_type = source.get('source_type', 'unknown')
            name = source.get('name', 'unnamed')
            logger.info(
                f"Source {i}: ID={source_id}, "
                f"Name='{name}', "
                f"Type={source_type}, "
                f"Markdown Content Length={content_length} chars"
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

        # Extract markdown content from all sources
        content_texts = []
        empty_sources = []
        
        for source in sources:
            source_id = source.get('id', 'unknown')
            markdown_content = source.get("markdown_content", "")
            
            # Log the content preview for debugging (first 200 chars)
            content_preview = (markdown_content[:200] + '...') if len(markdown_content) > 200 else markdown_content
            logger.info(f"Source {source_id} markdown preview: {content_preview}")
            
            if markdown_content and markdown_content.strip():
                content_texts.append(markdown_content)
                logger.info(f"Successfully added markdown content from source {source_id}")
            else:
                logger.warning(f"No markdown content found in source {source_id}")
                empty_sources.append((source_id, "No markdown content found"))
        
        # Check if we found any content
        if not content_texts:
            error_msg = (
                f"No valid markdown content found in any of the {len(sources)} sources. "
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
            
        logger.info(f"Successfully extracted markdown content from {len(content_texts)} out of {len(sources)} sources for job {job_id}")
        
        # Calculate total content length for logging
        total_content_length = sum(len(text) for text in content_texts)
        logger.info(f"Total content length: {total_content_length} characters")

        # Extract structured data using OpenRouter
        logger.info(f"Extracting structured data for job_id: {job_id}")
        try:
            # Directly call extract_structured_data with the markdown content texts
            business_info = await extract_structured_data(content_texts, org_id)
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
                processed_count=storage_result.get("stored_items", 1),
                org_id=org_id
            )
            logger.info(f"Content library job {job_id} completed successfully")
            
        except ValueError as ve:
            # Handle content length or model context errors
            error_msg = f"Content processing error: {str(ve)}"
            logger.error(f"{error_msg} for job_id: {job_id}")
            await update_content_library_job_status(
                job_id, 
                "failed", 
                error=error_msg,
                org_id=org_id
            )
            return
            
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
        logger.error(error_msg, exc_info=True)
        await update_content_library_job_status(
            job_id, 
            "failed", 
            error=error_msg,
            org_id=org_id
        )
        raise

@router.post("/process", response_model=ContentLibraryStatusResponse)
@observe(name="content_library_process_endpoint")
async def process_content_library(
    request: ContentLibraryRequest,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id)
):
    """
    Process content sources and extract structured data.
    
    Args:
        request: Content library request with org_id and source_ids
        background_tasks: FastAPI background tasks
        user_id: Current authenticated user (integer)
        
    Returns:
        Job status information
    """
    try:
        # Convert org_id from string to integer
        org_id = int(request.org_id)
        
        # Generate a unique job ID
        job_id = str(uuid.uuid4())
        
        logger.info(f"Creating content library job {job_id} for org_id: {org_id} with {len(request.source_ids)} sources")
        
        # Validate source_ids format
        if not request.source_ids:
            raise HTTPException(status_code=400, detail="No source IDs provided")
        
        # Create content library job
        job = await create_content_library_job(
            job_id=job_id,
            org_id=org_id,
            source_ids=request.source_ids,
            user_id=user_id
        )
        
        # Start background task to process the job
        background_tasks.add_task(
            process_content_library_job,
            job_id=job_id,
            org_id=org_id,
            source_ids=request.source_ids,
            user_id=user_id
        )
        
        # Return job status
        return ContentLibraryStatusResponse(
            job_id=job_id,
            org_id=str(org_id),
            status="pending",
            source_count=len(request.source_ids),
            processed_count=0
        )
        
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error initiating content library process: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}", response_model=ContentLibraryStatusResponse)
@observe(name="content_library_status_endpoint")
async def get_content_library_status(
    job_id: str = Path(..., description="Unique job ID"),
    org_id: int = Query(..., description="Organization ID"),
    user_id: int = Depends(get_current_user_id)
):
    """
    Get the status of a content library processing job.
    
    Args:
        job_id: Unique job ID
        org_id: Organization ID (integer)
        user_id: Current authenticated user (integer)
        
    Returns:
        Job status information
    """
    try:
        logger.info(f"Getting status for job {job_id} in org {org_id}")
        
        # Get job information
        job = await get_content_library_job(job_id, org_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Return job status
        return ContentLibraryStatusResponse(
            job_id=job_id,
            org_id=str(org_id),
            status=job.get("status", "unknown"),
            source_count=job.get("total_items", 0),
            processed_count=job.get("completed_items", 0),
            error=job.get("error_message")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting content library status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/{job_id}", response_model=ContentLibraryResultResponse)
@observe(name="content_library_results_endpoint")
async def get_content_library_result(
    job_id: str = Path(..., description="Unique job ID"),
    org_id: int = Query(..., description="Organization ID"),
    user_id: int = Depends(get_current_user_id)
):
    """
    Get the results of a content library processing job.
    
    Args:
        job_id: Unique job ID
        org_id: Organization ID (integer)
        user_id: Current authenticated user (integer)
        
    Returns:
        Job information and complete business information document
    """
    try:
        logger.info(f"Getting results for job {job_id} in org {org_id}")
        
        # Get the complete business information document
        result = await get_content_library_results(job_id, org_id)
        
        # If there was an error in getting results, return it with appropriate status
        if result.get("error"):
            return ContentLibraryResultResponse(
                job_id=job_id,
                org_id=str(org_id),
                status=result.get("status", "failed"),
                source_count=result.get("source_count", 0),
                processed_count=result.get("processed_count", 0),
                data=result.get("data", {}),
                error=result.get("error")
            )
        
        # Return the successful response with the business information
        return ContentLibraryResultResponse(
            job_id=job_id,
            org_id=str(org_id),
            status=result.get("status", "completed"),
            source_count=result.get("source_count", 0),
            processed_count=result.get("processed_count", 0),
            data=result.get("data", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting content library results: {str(e)}", exc_info=True)
        return ContentLibraryResultResponse(
            job_id=job_id,
            org_id=str(org_id),
            status="failed",
            source_count=0,
            processed_count=0,
            data={},
            error=f"Failed to retrieve results: {str(e)}"
        )
