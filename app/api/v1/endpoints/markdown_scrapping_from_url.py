"""
API endpoints for markdown extraction using Hyperbrowser - Improved with on-demand processing.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Path, Depends
import uuid
from app.core.logging import logger
from app.core.database import (
    create_markdown_extraction_job,
    get_markdown_content,
    get_user_organizations,
    get_processing_job
)
from app.schemas.markdown_extraction import (
    MarkdownExtractionRequest,
    MarkdownExtractionResponse,
    MarkdownStatusResponse,
    MarkdownResultResponse,
    MarkdownContent
)
from app.utils.markdown_extraction import start_batch_scrape, check_and_process_batch_job
from app.api.deps import get_current_user_id

router = APIRouter()


@router.post("/getmd", response_model=MarkdownExtractionResponse, status_code=202)
async def extract_markdown(
    request: MarkdownExtractionRequest,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id)
):
    """
    Extract markdown content from a list of URLs using Hyperbrowser batch scraping.
    
    This endpoint initiates an asynchronous batch scraping process that can handle
    up to 1,000 URLs at once. It returns a job ID for tracking progress.
    
    The job is submitted to Hyperbrowser and status is checked on-demand when
    users call the status or results endpoints.
    
    Args:
        request: MarkdownExtractionRequest containing URLs and optional org_id
        background_tasks: FastAPI background tasks for async job submission
        user_id: Current user ID from authentication
        
    Returns:
        MarkdownExtractionResponse with job details
    """
    urls = request.urls
    org_id = request.org_id
    
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    
    if len(urls) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 URLs allowed per batch")
    
    logger.info(f"Received markdown extraction request for {len(urls)} URLs from user {user_id}")
    
    try:
        # Get organization ID if not provided
        if not org_id:
            user_orgs = await get_user_organizations(user_id)
            if not user_orgs:
                raise HTTPException(status_code=400, detail="User is not a member of any organization")
            org_id = user_orgs[0]["org_id"]
            logger.info(f"Using default organization ID {org_id} for user {user_id}")
        else:
            # Validate user has access to the organization
            user_orgs = await get_user_organizations(user_id)
            user_org_ids = [org["org_id"] for org in user_orgs]
            if org_id not in user_org_ids:
                raise HTTPException(status_code=403, detail="User does not have access to this organization")
            logger.info(f"Using provided organization ID {org_id} for user {user_id}")
        
        # Generate a job ID for this batch
        hyperbrowser_job_id = str(uuid.uuid4())
        
        # Create job in database
        job_record = await create_markdown_extraction_job(
            hyperbrowser_job_id=hyperbrowser_job_id, 
            urls=urls, 
            org_id=org_id, 
            user_id=user_id
        )
        
        if not job_record:
            logger.error(f"Failed to create markdown extraction job for user {user_id}")
            raise HTTPException(status_code=500, detail="Failed to create extraction job")
        
        processing_job_id = job_record["job_id"]
        logger.info(f"Created markdown extraction job {processing_job_id} with hyperbrowser job {hyperbrowser_job_id}")
        
        # Submit batch scraping job (no polling, just submit)
        background_tasks.add_task(start_batch_scrape, hyperbrowser_job_id, urls, org_id)
        logger.info(f"Submitted batch scraping job {hyperbrowser_job_id} to background task")
        
        return MarkdownExtractionResponse(
            job_id=processing_job_id,
            org_id=org_id,
            status="pending",
            message="Markdown extraction job submitted successfully",
            total_urls=len(urls)
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error starting markdown extraction for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error starting extraction: {str(e)}")


@router.get("/getmd/{job_id}/status", response_model=MarkdownStatusResponse)
async def get_markdown_status(
    job_id: str = Path(..., description="Extraction job ID"),
    user_id: int = Depends(get_current_user_id)
):
    """
    Check the status of a markdown extraction job.
    
    This endpoint checks the Hyperbrowser status on-demand and returns the current
    status of the job, including how many URLs have been processed.
    
    Args:
        job_id: The processing job ID (not hyperbrowser job ID)
        user_id: Current user ID from authentication
        
    Returns:
        MarkdownStatusResponse with current job status
    """
    logger.info(f"Checking status for markdown job {job_id} by user {user_id}")
    
    try:
        # Get user organizations for security check
        user_orgs = await get_user_organizations(user_id)
        if not user_orgs:
            raise HTTPException(status_code=400, detail="User is not a member of any organization")
        
        user_org_ids = [org["org_id"] for org in user_orgs]
        
        # Try to get job for each organization the user belongs to
        job = None
        org_id = None
        for org_id_candidate in user_org_ids:
            job = await get_processing_job(job_id, org_id_candidate)
            if job:
                org_id = org_id_candidate
                break
        
        if not job:
            logger.warning(f"Job {job_id} not found for user {user_id}")
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        if org_id not in user_org_ids:
            logger.warning(f"User {user_id} attempted to access job {job_id} from unauthorized org {org_id}")
            raise HTTPException(status_code=403, detail="Access denied to this job")
        
        # Get the hyperbrowser job ID from metadata
        hyperbrowser_job_id = job.get("metadata", {}).get("hyperbrowser_job_id")
        if not hyperbrowser_job_id:
            logger.error(f"Job {job_id} missing hyperbrowser_job_id in metadata")
            raise HTTPException(status_code=500, detail="Job missing hyperbrowser job ID")
        
        # Check status with Hyperbrowser on-demand
        status_info = await check_and_process_batch_job(hyperbrowser_job_id, org_id)
        
        # Refresh job data after potential processing
        job = await get_processing_job(job_id, org_id)
        current_status = job.get("status", "unknown")
        
        # Handle different status scenarios
        if status_info.get("status") == "error":
            error_msg = status_info.get("error", "Unknown error")
            logger.error(f"Error checking job {job_id}: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Error checking job status: {error_msg}")
        
        logger.info(f"Found job {job_id} with status {current_status} in org {org_id}")
        
        return MarkdownStatusResponse(
            job_id=job_id,
            org_id=org_id,
            status=current_status,
            total_urls=job.get("total_items", 0),
            completed_urls=job.get("completed_items", 0),
            message=f"Job status: {current_status}"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error checking markdown job status for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error checking job status: {str(e)}")


@router.get("/getmd/{job_id}", response_model=MarkdownResultResponse)
async def get_markdown_results(
    job_id: str = Path(..., description="Extraction job ID"),
    user_id: int = Depends(get_current_user_id)
):
    """
    Get the results of a markdown extraction job.
    
    This endpoint checks the Hyperbrowser status on-demand, processes results if
    completed, and returns the markdown content extracted from each URL.
    
    Args:
        job_id: The processing job ID (not hyperbrowser job ID)
        user_id: Current user ID from authentication
        
    Returns:
        MarkdownResultResponse with extraction results
    """
    logger.info(f"Getting results for markdown job {job_id} by user {user_id}")
    
    try:
        # Get user organizations for security check
        user_orgs = await get_user_organizations(user_id)
        if not user_orgs:
            raise HTTPException(status_code=400, detail="User is not a member of any organization")
        
        user_org_ids = [org["org_id"] for org in user_orgs]
        
        # Try to get job for each organization the user belongs to
        job = None
        org_id = None
        for org_id_candidate in user_org_ids:
            job = await get_processing_job(job_id, org_id_candidate)
            if job:
                org_id = org_id_candidate
                break
        
        if not job:
            logger.warning(f"Job {job_id} not found for user {user_id}")
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Get the hyperbrowser job ID from metadata
        hyperbrowser_job_id = job.get("metadata", {}).get("hyperbrowser_job_id")
        if not hyperbrowser_job_id:
            logger.error(f"Job {job_id} missing hyperbrowser_job_id in metadata")
            raise HTTPException(status_code=500, detail="Job missing hyperbrowser job ID")
        
        # Check status and process results if needed (on-demand)
        status_info = await check_and_process_batch_job(hyperbrowser_job_id, org_id)
        
        # Handle different status scenarios
        if status_info.get("status") == "error":
            error_msg = status_info.get("error", "Unknown error")
            logger.error(f"Error processing job {job_id}: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Error processing job: {error_msg}")
        
        if status_info.get("status") == "processing":
            # Job still processing, return current status without results
            job = await get_processing_job(job_id, org_id)  # Refresh job data
            return MarkdownResultResponse(
                job_id=job_id,
                org_id=org_id,
                status="processing",
                total_urls=job.get("total_items", 0),
                completed_urls=job.get("completed_items", 0),
                results=[],
                error=None
            )
        
        # Get job data from database using hyperbrowser job ID
        data = await get_markdown_content(hyperbrowser_job_id, org_id)
        
        if not data:
            logger.warning(f"Results not found for hyperbrowser job {hyperbrowser_job_id}")
            raise HTTPException(status_code=404, detail=f"Results not found for job {job_id}")
        
        # Refresh job data after potential processing
        job = await get_processing_job(job_id, org_id)
        content_data = data.get("content", [])
        
        # Process status based on job status
        status = job.get("status", "unknown")
        total_urls = job.get("total_items", 0)
        completed_urls = job.get("completed_items", 0)
        
        logger.info(f"Found job {job_id} with status {status}, {completed_urls}/{total_urls} URLs completed, {len(content_data)} content items")
        
        # Convert content data to Pydantic models
        results = []
        for content in content_data:
            results.append(MarkdownContent(
                url=content.get("url", ""),
                status=content.get("status", "unknown"),
                markdown_text=content.get("markdown_text"),
                error=content.get("metadata", {}).get("error") if content.get("status") == "failed" else None,
                metadata=content.get("metadata"),
                links=content.get("links", []),
                org_id=org_id
            ))
        
        return MarkdownResultResponse(
            job_id=job_id,
            org_id=org_id,
            status=status,
            total_urls=total_urls,
            completed_urls=completed_urls,
            results=results,
            error=job.get("error_message") if status == "failed" else None
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving markdown results for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving results: {str(e)}")