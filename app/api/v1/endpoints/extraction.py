"""
Enhanced API endpoints for comprehensive website data extraction.
"""
from fastapi import APIRouter, HTTPException, Path, Depends
from hyperbrowser import Hyperbrowser
from hyperbrowser.models import StartExtractJobParams
import json

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
    Start a comprehensive website data extraction job.
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
        
        # Generate schema and log it
        schema_json = WebsiteExtraction.model_json_schema()
        logger.info(f"Enhanced schema with {len(schema_json.get('properties', {}))} top-level properties")
        logger.info(f"Schema includes: {list(schema_json.get('properties', {}).keys())}")
        
        # Start the extraction job with enhanced parameters
        job_response = client.extract.start(
            params=StartExtractJobParams(
                urls=[url],
                prompt=extraction_prompt,
                schema=WebsiteExtraction,
                waitFor=3000,  # Wait longer for complex sites
                maxLinks=25,   # More links for comprehensive analysis
            )
        )
        
        if not job_response or not hasattr(job_response, "job_id"):
            logger.error(f"Invalid job response from Hyperbrowser")
            raise HTTPException(status_code=500, detail="Failed to start extraction job")
        
        hyperbrowser_job_id = job_response.job_id
        logger.info(f"Started enhanced extraction job {hyperbrowser_job_id} for URL: {url}")
        
        # Store job in database
        job_record = await create_extraction_job(hyperbrowser_job_id, url, org_id, user_id)
        
        if not job_record:
            raise HTTPException(status_code=500, detail="Failed to create job record")
        
        return ExtractionResponse(
            job_id=hyperbrowser_job_id,
            org_id=str(org_id),
            status="pending",
            message="Enhanced extraction job started successfully"
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
        
        # Log comprehensive data analysis
        if isinstance(result.data, dict):
            total_fields = len(result.data)
            non_empty_fields = [k for k, v in result.data.items() if v not in [None, {}, []]]
            empty_fields = [k for k, v in result.data.items() if v in [None, {}, []]]
            
            logger.info(f"Extraction Analysis for {job_id}:")
            logger.info(f"  Total fields: {total_fields}")
            logger.info(f"  Non-empty fields ({len(non_empty_fields)}): {non_empty_fields}")
            logger.info(f"  Empty fields ({len(empty_fields)}): {empty_fields}")
            
            # Log specific content types
            if result.data.get("color_palette"):
                logger.info(f"  Color palette extracted: {result.data['color_palette']}")
            if result.data.get("brand_fonts"):
                logger.info(f"  Brand fonts extracted: {result.data['brand_fonts']}")
            if result.data.get("link_analysis") and result.data["link_analysis"].get("links"):
                link_count = len(result.data["link_analysis"]["links"])
                logger.info(f"  Links analyzed: {link_count}")
            if result.data.get("social_profiles"):
                active_socials = [k for k, v in result.data["social_profiles"].items() if v]
                logger.info(f"  Social profiles found: {active_socials}")
        
        try:
            # Validate data and create response object
            extracted_data = WebsiteExtraction(**result.data)
            
            # Update database
            await update_extraction_job_status(job_id, result.status, result.data, org_id)
            await store_extraction_content(job_id, result.data, org_id, user_id)

            # Process logo/favicon if present (with better error handling)
            if extracted_data.logo and extracted_data.logo.url:
                try:
                    from app.utils.logo_downloader import process_website_images
                    image_result = await process_website_images(extracted_data.logo.url, job_id, org_id)
                    if image_result.get("error"):
                        logger.warning(f"Logo processing warning: {image_result['error']}")
                    else:
                        logger.info(f"Logo processed successfully: {image_result.get('logo_file_path')}")
                except Exception as img_error:
                    logger.warning(f"Logo processing failed (non-critical): {str(img_error)}")

            logger.info(f"Successfully processed comprehensive extraction data for job {job_id}")
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
    """Get the enhanced JSON schema being sent to Hyperbrowser."""
    try:
        schema = WebsiteExtraction.model_json_schema()
        
        # Analyze schema structure
        properties = schema.get("properties", {})
        nested_models = []
        
        for prop_name, prop_def in properties.items():
            if "$ref" in str(prop_def):
                nested_models.append(prop_name)
        
        return {
            "schema": schema,
            "analysis": {
                "total_properties": len(properties),
                "required_fields": schema.get("required", []),
                "property_names": list(properties.keys()),
                "nested_models": nested_models,
                "definitions_count": len(schema.get("definitions", {}))
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating schema: {str(e)}")

@router.post("/test-schema", response_model=WebsiteExtraction)
async def test_schema_validation(data: dict):
    """Test enhanced schema validation with sample data."""
    try:
        validated_data = WebsiteExtraction(**data)
        return validated_data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Schema validation failed: {str(e)}")

@router.post("/test-extraction", response_model=dict)
async def test_sample_extraction():
    """Test with sample Apple-like data structure."""
    sample_data = {
        "url": "https://example.com",
        "favicon": "https://example.com/favicon.ico",
        "logo": {
            "url": "https://example.com/logo.png",
            "alt_text": "Example Company Logo"
        },
        "color_palette": ["#FF0000", "#00FF00", "#0000FF"],
        "brand_fonts": {
            "primary": "Helvetica Neue",
            "secondary": "Arial"
        },
        "company": {
            "name": "Example Corp",
            "description": "Leading example company",
            "industry": "Technology",
            "location": "San Francisco, CA"
        },
        "social_profiles": {
            "linkedin": "https://linkedin.com/company/example",
            "twitter": "https://twitter.com/example"
        },
        "legal_links": {
            "terms_of_service": "https://example.com/terms",
            "privacy_policy": "https://example.com/privacy"
        },
        "seo_data": {
            "meta_title": "Example Corp - Technology Leader",
            "meta_description": "Leading technology company",
            "h1": "Welcome to Example Corp"
        },
        "key_services": ["Software Development", "Consulting", "Support"]
    }
    
    try:
        validated = WebsiteExtraction(**sample_data)
        return {
            "status": "success",
            "message": "Enhanced schema validation successful",
            "validated_data": validated.dict()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Schema validation failed: {str(e)}"
        }