"""
Simple API endpoints for website data extraction.
"""
from fastapi import APIRouter, HTTPException, Path, Depends
from hyperbrowser import Hyperbrowser
from hyperbrowser.models import StartExtractJobParams
from uuid import UUID

from app.core.config import settings
from app.core.logging import logger
from app.core.database import (
    create_extraction_job, 
    get_extraction_job, 
    update_extraction_job_status, 
    get_default_org_id,
    store_extraction_content,
)
from app.schemas.extraction import (
    ExtractionRequest, 
    ExtractionResponse, 
    ExtractionStatusResponse, 
    ExtractionResultResponse,
    WebsiteExtraction
)
from app.utils.prompts import METADATA_AND_LINKS_EXTRACTION_PROMPT
from app.api.deps import get_current_user_id

router = APIRouter()

@router.post("/extract", response_model=ExtractionResponse, status_code=202)
async def start_extraction(request: ExtractionRequest, user_id: str = Depends(get_current_user_id)):
    """
    Start a website data extraction job.
    
    This endpoint initiates an asynchronous extraction process using Hyperbrowser.
    """
    url = str(request.url)
    logger.info(f"Received extraction request for URL: {url}")

    # Get organization ID (use provided or default)
    org_id = request.org_id
    if not org_id:
        org_id = await get_default_org_id(user_id)
        if not org_id:
            raise HTTPException(status_code=400, detail="No organization ID provided and no default organization found")

    # Initialize Hyperbrowser client
    client = Hyperbrowser(api_key=settings.HYPERBROWSER_API_KEY)
    
    try:
        # Start the extraction job with Hyperbrowser
        job_response = client.extract.start(
            params=StartExtractJobParams(
                urls=[url],
                prompt=METADATA_AND_LINKS_EXTRACTION_PROMPT.format(TARGET_URL=url),
                schema=WebsiteExtraction,
            )
        )
        
        if not job_response or not hasattr(job_response, "job_id"):
            raise HTTPException(status_code=500, detail="Failed to start extraction job")
        
        job_id = job_response.job_id
        logger.info(f"Started extraction job {job_id} for URL: {url}")
        
        # Store job in database with organization ID
        job_record = await create_extraction_job(job_id, url, str(org_id), user_id)
        
        # Return job info to client
        return ExtractionResponse(
            job_id=job_id,
            org_id=org_id,
            status="pending",
            message="Extraction job started successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting extraction: {str(e)}")
        raise HTTPException(status_code=500, detail="Error starting extraction")

@router.get("/extract/{job_id}/status", response_model=ExtractionStatusResponse)
async def get_extraction_status(job_id: str = Path(..., description="Hyperbrowser job ID"), user_id: str = Depends(get_current_user_id)):
    """
    Check the status of an extraction job.
    
    This endpoint queries Hyperbrowser for the current status of a job.
    """
    logger.info(f"Checking status for job: {job_id}")
    
    # Get job record from database first to verify ownership
    job_record = await get_extraction_job(job_id)
    if not job_record:
        raise HTTPException(status_code=404, detail="Extraction job not found")
    
    # Get organization ID from the job record
    org_id = job_record.get("org_id")
    if not org_id:
        raise HTTPException(status_code=500, detail="Job record missing organization ID")
    
    # Initialize Hyperbrowser client
    client = Hyperbrowser(api_key=settings.HYPERBROWSER_API_KEY)
    
    try:
        # Check status with Hyperbrowser
        status_response = client.extract.get_status(job_id)
        
        if not status_response or not hasattr(status_response, "status"):
            # Use database status as fallback
            return ExtractionStatusResponse(
                job_id=job_id,
                org_id=UUID(org_id),
                status=job_record.get("status", "unknown")
            )
        
        # Update our database with the latest status
        await update_extraction_job_status(job_id, status_response.status, None, org_id)
        
        return ExtractionStatusResponse(
            job_id=job_id,
            org_id=UUID(org_id),
            status=status_response.status,
            message=f"Job status: {status_response.status}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking status: {str(e)}")
        raise HTTPException(status_code=500, detail="Error checking job status")

@router.get("/extract/{job_id}", response_model=ExtractionResultResponse)
async def get_extraction_result(job_id: str = Path(..., description="Hyperbrowser job ID"), user_id: str = Depends(get_current_user_id)):
    """
    Get the result of a completed extraction job.
    
    This endpoint retrieves the full data from a completed extraction job.
    """
    logger.info(f"Getting results for job: {job_id}")
    
    # Get job record from database first to verify ownership
    job_record = await get_extraction_job(job_id)
    if not job_record:
        raise HTTPException(status_code=404, detail="Extraction job not found")
    
    # Get organization ID from the job record
    org_id = job_record.get("org_id")
    if not org_id:
        raise HTTPException(status_code=500, detail="Job record missing organization ID")
    
    # Initialize Hyperbrowser client
    client = Hyperbrowser(api_key=settings.HYPERBROWSER_API_KEY)
    
    try:
        # Get full job result from Hyperbrowser
        result = client.extract.get(job_id)
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to get extraction result")
        
        # Process result based on job status
        if result.status != "completed":
            # Update status and return early if job is not complete
            await update_extraction_job_status(job_id, result.status, None, org_id)
            return ExtractionResultResponse(
                job_id=job_id,
                org_id=UUID(org_id),
                status=result.status,
                message=f"Job is still {result.status}. Try again later."
            )
        
        # For completed jobs, check if we have data
        if not hasattr(result, "data") or not result.data:
            await update_extraction_job_status(job_id, result.status, None, org_id)
            return ExtractionResultResponse(
                job_id=job_id,
                org_id=UUID(org_id),
                status="completed",
                error="No data returned from extraction"
            )
        
        try:
            # Validate data and create response object
            extracted_data = WebsiteExtraction(**result.data)
            
            # Update database with status and process images
            await update_extraction_job_status(job_id, result.status, result.data, org_id)
            await store_extraction_content(job_id, result.data, org_id, user_id)

            return ExtractionResultResponse(
                job_id=job_id,
                org_id=UUID(org_id),
                status="completed",
                data=extracted_data
            )
            
        except Exception as validation_error:
            logger.error(f"Data validation error: {str(validation_error)}")
            
            # Try with partial data
            try:
                valid_fields = {k: v for k, v in result.data.items() 
                               if k in WebsiteExtraction.__annotations__}
                
                if valid_fields:
                    # Process with partial data
                    await update_extraction_job_status(job_id, result.status, valid_fields, org_id)
                    
                    partial_data = WebsiteExtraction(**valid_fields)
                    return ExtractionResultResponse(
                        job_id=job_id,
                        org_id=UUID(org_id),
                        status="completed",
                        data=partial_data,
                        error="Partial data returned due to validation errors"
                    )
            except:
                pass
                
            # Just update status if all else fails
            await update_extraction_job_status(job_id, result.status, None, org_id)
            return ExtractionResultResponse(
                job_id=job_id,
                org_id=UUID(org_id),
                status="completed",
                error="Failed to process extracted data"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving result: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving extraction result")