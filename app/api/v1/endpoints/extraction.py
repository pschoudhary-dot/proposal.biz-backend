"""
API endpoints for website data extraction - FIXED VERSION
"""
from fastapi import APIRouter, HTTPException, Path, Depends
from hyperbrowser import Hyperbrowser
from hyperbrowser.models import StartExtractJobParams

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
async def start_extraction(request: ExtractionRequest, user_id: int = Depends(get_current_user_id)):
    """
    Start a website data extraction job with structured schema.
    """
    url = str(request.url)
    logger.info(f"Received extraction request for URL: {url}")

    # Get organization ID
    org_id = request.org_id
    if org_id is None:
        org_id = await get_default_org_id(user_id)
        if not org_id:
            raise HTTPException(status_code=400, detail="No organization ID provided and no default organization found")
    
    # Ensure org_id is an integer
    if not isinstance(org_id, int):
        try:
            org_id = int(org_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid organization ID format")

    # Initialize Hyperbrowser client
    client = Hyperbrowser(api_key=settings.HYPERBROWSER_API_KEY)
    
    try:
        # Create the extraction parameters
        extraction_prompt = METADATA_AND_LINKS_EXTRACTION_PROMPT.format(TARGET_URL=url)
        
        # Generate schema and log it ONCE
        schema_json = WebsiteExtraction.model_json_schema()
        logger.info(f"Schema properties count: {len(schema_json.get('properties', {}))}")
        logger.info(f"Using structured schema with proper field definitions")
        
        # Start the extraction job
        job_response = client.extract.start(
            params=StartExtractJobParams(
                urls=[url],
                prompt=extraction_prompt,
                schema=WebsiteExtraction,
                waitFor=2000,  # Wait for page load
                maxLinks=15,   # Limit for free tier
            )
        )
        
        if not job_response or not hasattr(job_response, "job_id"):
            logger.error(f"Invalid job response from Hyperbrowser")
            raise HTTPException(status_code=500, detail="Failed to start extraction job")
        
        hyperbrowser_job_id = job_response.job_id
        logger.info(f"Started extraction job {hyperbrowser_job_id} for URL: {url}")
        
        # Store job in database
        job_record = await create_extraction_job(hyperbrowser_job_id, url, org_id, user_id)
        
        if not job_record:
            raise HTTPException(status_code=500, detail="Failed to create job record")
        
        return ExtractionResponse(
            job_id=hyperbrowser_job_id,
            org_id=str(org_id),
            status="pending",
            message="Extraction job started successfully with structured schema"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting extraction: {str(e)}")

@router.get("/extract/{job_id}/status", response_model=ExtractionStatusResponse)
async def get_extraction_status(job_id: str = Path(..., description="Hyperbrowser job ID"), user_id: int = Depends(get_current_user_id)):
    """
    Check the status of an extraction job.
    """
    logger.info(f"Checking status for job: {job_id}")
    
    # Get job record from database
    job_record = await get_extraction_job(job_id)
    if not job_record:
        raise HTTPException(status_code=404, detail="Extraction job not found")
    
    org_id = job_record.get("org_id")
    if not org_id:
        raise HTTPException(status_code=500, detail="Job record missing organization ID")
    
    # Initialize Hyperbrowser client
    client = Hyperbrowser(api_key=settings.HYPERBROWSER_API_KEY)
    
    try:
        # Check status with Hyperbrowser
        status_response = client.extract.get_status(job_id)
        
        if not status_response or not hasattr(status_response, "status"):
            return ExtractionStatusResponse(
                job_id=job_id,
                org_id=str(org_id),
                status=job_record.get("status", "unknown")
            )
        
        # Update database with latest status
        await update_extraction_job_status(job_id, status_response.status, None, org_id)
        
        return ExtractionStatusResponse(
            job_id=job_id,
            org_id=str(org_id),
            status=status_response.status,
            message=f"Job status: {status_response.status}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking status: {str(e)}")
        raise HTTPException(status_code=500, detail="Error checking job status")

@router.get("/extract/{job_id}", response_model=ExtractionResultResponse)
async def get_extraction_result(job_id: str = Path(..., description="Hyperbrowser job ID"), user_id: int = Depends(get_current_user_id)):
    """
    Get the result of a completed extraction job.
    """
    logger.info(f"Getting results for job: {job_id}")
    
    # Get job record from database
    job_record = await get_extraction_job(job_id)
    if not job_record:
        raise HTTPException(status_code=404, detail="Extraction job not found")
    
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
        
        logger.info(f"Job {job_id} result status: {result.status}")
        
        # Process result based on job status
        if result.status != "completed":
            await update_extraction_job_status(job_id, result.status, None, org_id)
            return ExtractionResultResponse(
                job_id=job_id,
                org_id=str(org_id),
                status=result.status,
                message=f"Job is still {result.status}. Try again later."
            )
        
        # For completed jobs, check if we have data
        if not hasattr(result, "data") or not result.data:
            logger.warning(f"Job {job_id} completed but no data returned")
            await update_extraction_job_status(job_id, result.status, None, org_id)
            return ExtractionResultResponse(
                job_id=job_id,
                org_id=str(org_id),
                status="completed",
                error="No data returned from extraction"
            )
        
        # Log raw data for debugging (but don't spam)
        if isinstance(result.data, dict):
            logger.info(f"Extracted data has {len(result.data)} fields")
            non_empty_fields = [k for k, v in result.data.items() if v not in [None, {}, []]]
            logger.info(f"Non-empty fields: {non_empty_fields}")
        
        try:
            # Validate data and create response object
            extracted_data = WebsiteExtraction(**result.data)
            
            # Update database
            await update_extraction_job_status(job_id, result.status, result.data, org_id)
            await store_extraction_content(job_id, result.data, org_id, user_id)

            logger.info(f"Successfully processed extraction data for job {job_id}")
            return ExtractionResultResponse(
                job_id=job_id,
                org_id=str(org_id),
                status="completed",
                data=extracted_data
            )
            
        except Exception as validation_error:
            logger.error(f"Data validation error for job {job_id}: {str(validation_error)}")
            
            # Update status and return error
            await update_extraction_job_status(job_id, result.status, None, org_id)
            return ExtractionResultResponse(
                job_id=job_id,
                org_id=str(org_id),
                status="completed",
                error=f"Schema validation failed: {str(validation_error)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving result for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving extraction result")

# Test endpoints
@router.get("/schema", response_model=dict)
async def get_extraction_schema():
    """Get the JSON schema being sent to Hyperbrowser."""
    try:
        schema = WebsiteExtraction.model_json_schema()
        return {
            "schema": schema,
            "properties_count": len(schema.get("properties", {})),
            "required_fields": schema.get("required", []),
            "property_names": list(schema.get("properties", {}).keys())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating schema: {str(e)}")

@router.post("/test-schema", response_model=WebsiteExtraction)
async def test_schema_validation(data: dict):
    """Test schema validation with sample data."""
    try:
        validated_data = WebsiteExtraction(**data)
        return validated_data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Schema validation failed: {str(e)}")