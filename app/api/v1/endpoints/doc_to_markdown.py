"""
API endpoints for document to markdown conversion using Apify Docling.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Path, UploadFile, File, Form, Depends
from typing import List, Optional
import uuid

from app.core.logging import logger
from app.api.deps import get_current_user_id
from app.core.database import (
    create_processing_job,
    get_processing_job,
    get_document_content,
    get_user_organizations
)
from app.schemas.doc_to_markdown import (
    DocToMarkdownResponse,
    DocToMarkdownStatusResponse,
    DocToMarkdownResultResponse,
    DocToMarkdownContent
)
from app.utils.doc_to_markdown import process_documents
from app.utils.storage_utils import storage_client, ensure_storage_bucket_exists

router = APIRouter()


@router.post("/doc2md", response_model=DocToMarkdownResponse, status_code=202)
async def convert_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    job_id: Optional[str] = Form(None),
    org_id: Optional[int] = Form(None),
    user_id: int = Depends(get_current_user_id)
):
    """
    Convert documents to markdown format using Apify Docling.
    
    This endpoint accepts multiple document files, uploads them to Supabase storage,
    and converts them to markdown format using Apify Docling. It returns a job ID 
    that can be used to check the status and retrieve results.
    
    Supported formats include PDF, DOCX, PPTX, HTML, Markdown, AsciiDoc, and more.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    logger.info(f"Received document conversion request for {len(files)} files")
    
    # Generate a job ID if not provided
    if not job_id:
        job_id = str(uuid.uuid4())
    
    try:
        # If org_id is not provided in the form, get it from the user's organizations
        if not org_id:
            orgs = await get_user_organizations(user_id)
            if not orgs:
                raise HTTPException(status_code=400, detail="User is not a member of any organization")
            
            # Use the first organization ID (it's already an integer)
            org_id = orgs[0]["org_id"]
            logger.info(f"Using organization ID from user profile: {org_id}")
        else:
            logger.info(f"Using organization ID from form data: {org_id}")
        
        # Ensure storage bucket exists
        if not ensure_storage_bucket_exists(storage_client):
            raise HTTPException(
                status_code=500, 
                detail="Failed to initialize storage bucket. Please check Supabase configuration."
            )
        
        # Read file contents before starting background task
        file_data = []
        for file in files:
            try:
                # Read file content
                content = await file.read()
                if not content:
                    logger.warning(f"File {file.filename} is empty, skipping")
                    continue
                
                file_info = {
                    "content": content,
                    "filename": file.filename,
                    "content_type": file.content_type or "application/octet-stream"
                }
                file_data.append(file_info)
                logger.info(f"Read {len(content)} bytes from {file.filename}")
            
            except Exception as e:
                logger.error(f"Error reading file {file.filename}: {str(e)}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Error reading file {file.filename}: {str(e)}"
                )
        
        if not file_data:
            raise HTTPException(status_code=400, detail="No valid files provided")
        
        # Create processing job in database
        job_record = await create_processing_job(
            org_id=org_id,
            job_type="document_conversion",
            user_id=user_id,
            source_files=[file_info["filename"] for file_info in file_data],
            metadata={"original_job_id": job_id}
        )
        
        if not job_record:
            raise HTTPException(status_code=500, detail="Failed to create conversion job")
            
        # Use the generated job_id from the database
        db_job_id = job_record["job_id"]
        logger.info(f"Created document conversion job record with ID: {db_job_id}, org_id: {org_id}")
        
        # Start background task to process documents with file data
        background_tasks.add_task(process_documents, db_job_id, file_data, org_id, user_id)
        
        return DocToMarkdownResponse(
            job_id=db_job_id,
            org_id=org_id, # org_id is now an int, matching the schema
            status="pending",
            message="Document conversion job started successfully"
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error starting document conversion: {str(e)}", exc_info=True)
        # Check for specific database errors
        error_str = str(e)
        if "violates foreign key constraint" in error_str and "org_id" in error_str:
            logger.error(f"Organization ID {org_id} does not exist in the organizations table.")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid organization ID: {org_id}. Organization does not exist."
            )
        raise HTTPException(status_code=500, detail=f"Error starting conversion: {str(e)}")


@router.get("/doc2md/{job_id}/status", response_model=DocToMarkdownStatusResponse)
async def get_document_conversion_status(
    job_id: str = Path(..., description="Conversion job ID"),
    org_id: Optional[int] = None,
    user_id: int = Depends(get_current_user_id)
):
    """
    Check the status of a document conversion job.
    
    This endpoint returns the current status of the job, including how many files
    have been processed out of the total.
    """
    logger.info(f"Checking status for document conversion job: {job_id}")
    
    try:
        if not org_id:
            orgs = await get_user_organizations(user_id)
            if not orgs:
                raise HTTPException(status_code=400, detail="User is not a member of any organization")
            org_id = orgs[0]["org_id"]
        
        job = await get_processing_job(job_id, org_id)
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found for organization {org_id}"
            )
        
        logger.info(f"Found job in database: {job_id} with status {job.get('status', 'unknown')}")
        
        error_message = job.get("error_message") if job.get("status") == "failed" else None
        
        return DocToMarkdownStatusResponse(
            job_id=job_id,
            org_id=org_id,
            status=job.get("status", "unknown"),
            total_files=job.get("total_items", 0),
            completed_files=job.get("completed_items", 0),
            message=error_message or f"Job status: {job.get('status', 'unknown')}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking document conversion job status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error checking job status: {str(e)}"
        )


@router.get("/doc2md/{job_id}", response_model=DocToMarkdownResultResponse)
async def get_document_conversion_results(
    job_id: str = Path(..., description="Conversion job ID"),
    org_id: Optional[int] = None,
    user_id: int = Depends(get_current_user_id)
):
    """
    Get the results of a document conversion job.
    
    This endpoint returns the markdown content extracted from each document.
    """
    logger.info(f"Getting results for document conversion job: {job_id}")
    
    try:
        if not org_id:
            orgs = await get_user_organizations(user_id)
            if not orgs:
                raise HTTPException(status_code=400, detail="User is not a member of any organization")
            org_id = orgs[0]["org_id"]
        
        data = await get_document_content(job_id, org_id)
        
        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found for organization {org_id} or has no results"
            )
        
        job = data.get("job", {})
        content_data = data.get("content", [])
        
        status = job.get("status", "unknown")
        error_message = job.get("error_message") if status == "failed" else None
        
        logger.info(f"Found job {job_id} with status {status} and {len(content_data)} content items")
        
        results = []
        for content in content_data:
            content_metadata = content.get("metadata", {})
            content_error = content_metadata.get("error") if content.get("status") == "failed" else None
            
            results.append(DocToMarkdownContent(
                filename=content.get("filename", ""),
                status=content.get("status", "unknown"),
                markdown_text=content.get("markdown_text"),
                error=content_error,
                metadata=content_metadata,
                org_id=org_id
            ))
        
        return DocToMarkdownResultResponse(
            job_id=job_id,
            org_id=org_id,
            status=status,
            total_files=job.get("total_items", 0),
            completed_files=job.get("completed_items", 0),
            results=results,
            error=error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document conversion results: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving results: {str(e)}"
        )

