"""
API endpoints for markdown extraction using Hyperbrowser.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Path, Depends
import uuid
from uuid import UUID
from app.core.logging import logger
from app.core.database import (
    create_markdown_extraction_job,
    get_markdown_extraction_job,
    get_markdown_content,
    update_markdown_extraction_status,
    get_default_org_id
)
from app.schemas.markdown_extraction import (
    MarkdownExtractionRequest,
    MarkdownExtractionResponse,
    MarkdownStatusResponse,
    MarkdownResultResponse,
    MarkdownContent
)
from app.utils.url_markdown_extraction import start_batch_scrape
from app.api.deps import get_current_user_id

router = APIRouter()

@router.post("/getmd", response_model=MarkdownExtractionResponse, status_code=202)
async def extract_markdown(
    request: MarkdownExtractionRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id)
):
    """
    Extract markdown content from a list of URLs.
    
    This endpoint initiates an asynchronous batch scraping process using Hyperbrowser.
    It returns a job ID that can be used to check the status and retrieve results.
    """
    urls = request.urls
    
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    
    logger.info(f"Received markdown extraction request for {len(urls)} URLs")
    
    # Get organization ID (use provided or default)
    org_id = request.org_id
    if not org_id:
        org_id = await get_default_org_id(user_id)
        if not org_id:
            raise HTTPException(status_code=400, detail="No organization ID provided and no default organization found")
    
    # Generate a job ID
    job_id = str(uuid.uuid4())
    
    try:
        # Create job in database with organization ID
        job_record = await create_markdown_extraction_job(job_id, urls, str(org_id), user_id)
        
        if not job_record:
            raise HTTPException(status_code=500, detail="Failed to create extraction job")
        
        # Start batch scraping in the background
        background_tasks.add_task(start_batch_scrape, job_id, urls, str(org_id))
        
        return MarkdownExtractionResponse(
            job_id=job_id,
            org_id=org_id,
            status="pending",
            message="Markdown extraction job started successfully",
            total_urls=len(urls)
        )
        
    except Exception as e:
        logger.error(f"Error starting markdown extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting extraction: {str(e)}")


@router.get("/getmd/{job_id}/status", response_model=MarkdownStatusResponse)
async def get_markdown_status(
    job_id: str = Path(..., description="Extraction job ID"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Check the status of a markdown extraction job.
    
    This endpoint returns the current status of the job, including how many URLs
    have been processed out of the total.
    """
    logger.info(f"Checking status for markdown job: {job_id}")
    
    try:
        # Get job from database
        job = await get_markdown_extraction_job(job_id)
        
        if not job:
            # For debugging, log what we got back
            logger.error(f"Job not found in database: {job_id}")
            # Return a default response instead of 404 for easier debugging
            return MarkdownStatusResponse(
                job_id=job_id,
                status="not_found",
                total_urls=0,
                completed_urls=0,
                message=f"Job {job_id} not found in database"
            )
        
        # Get organization ID from the job record
        org_id = job.get("org_id")
        if not org_id:
            raise HTTPException(status_code=500, detail="Job record missing organization ID")
        
        logger.info(f"Found job in database: {job_id} with status {job.get('status', 'unknown')}")
        
        return MarkdownStatusResponse(
            job_id=job_id,
            org_id=UUID(org_id),
            status=job.get("status", "unknown"),
            total_urls=job.get("total_urls", 0),
            completed_urls=job.get("completed_urls", 0),
            message=f"Job status: {job.get('status', 'unknown')}"
        )
        
    except Exception as e:
        logger.error(f"Error checking markdown job status: {str(e)}")
        # Return a response with error details instead of throwing an exception
        return MarkdownStatusResponse(
            job_id=job_id,
            status="error",
            total_urls=0,
            completed_urls=0,
            message=f"Error checking job status: {str(e)}"
        )


@router.get("/getmd/{job_id}", response_model=MarkdownResultResponse)
async def get_markdown_results(
    job_id: str = Path(..., description="Extraction job ID"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Get the results of a markdown extraction job.
    
    This endpoint returns the markdown content extracted from each URL,
    along with any links found on the pages.
    """
    logger.info(f"Getting results for markdown job: {job_id}")
    
    try:
        # Get job data from database
        data = await get_markdown_content(job_id)
        
        if not data:
            logger.error(f"Results not found for job: {job_id}")
            # Return a response with error details instead of 404
            return MarkdownResultResponse(
                job_id=job_id,
                status="not_found",
                total_urls=0,
                completed_urls=0,
                error=f"Job {job_id} not found or has no results"
            )
        
        job = data.get("job", {})
        content_data = data.get("content", [])
        
        # Get organization ID from the job record
        org_id = job.get("org_id")
        if not org_id:
            raise HTTPException(status_code=500, detail="Job record missing organization ID")
        
        # Process status based on job status
        status = job.get("status", "unknown")
        logger.info(f"Found job {job_id} with status {status} and {len(content_data)} content items")
        
        if status != "completed" and status != "failed":
            return MarkdownResultResponse(
                job_id=job_id,
                org_id=UUID(org_id),
                status=status,
                total_urls=job.get("total_urls", 0),
                completed_urls=job.get("completed_urls", 0),
                error=f"Job is still {status}. Try again later."
            )
        
        # Convert content data to Pydantic models
        results = []
        for content in content_data:
            results.append(MarkdownContent(
                url=content.get("url", ""),
                status=content.get("status", "unknown"),
                markdown_text=content.get("markdown_text"),
                error=content.get("error"),
                metadata=content.get("metadata"),
                links=content.get("links", []),
                org_id=UUID(org_id)
            ))
        
        return MarkdownResultResponse(
            job_id=job_id,
            org_id=UUID(org_id),
            status=status,
            total_urls=job.get("total_urls", 0),
            completed_urls=job.get("completed_urls", 0),
            results=results
        )
        
    except Exception as e:
        logger.error(f"Error retrieving markdown results: {str(e)}")
        # Return a response with error details instead of throwing an exception
        return MarkdownResultResponse(
            job_id=job_id,
            status="error",
            total_urls=0,
            completed_urls=0,
            error=f"Error retrieving results: {str(e)}"
        )