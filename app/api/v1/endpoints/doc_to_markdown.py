"""
API endpoints for document to markdown conversion using Docling.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Path, UploadFile, File, Form, Depends
from typing import List, Optional
from uuid import UUID
import uuid
import tempfile
import os
import shutil
from app.core.logging import logger
from app.api.deps import get_current_user_id
from app.core.database import (
    create_document_conversion_job,
    get_document_conversion_job,
    get_document_content,
    create_document_content_record,
    get_user_organizations
)
from app.schemas.doc_to_markdown import (
    DocToMarkdownResponse,
    DocToMarkdownStatusResponse,
    DocToMarkdownResultResponse,
    DocToMarkdownContent
)
from app.utils.doc_to_markdown import process_documents

router = APIRouter()


@router.post("/doc2md", response_model=DocToMarkdownResponse, status_code=202)
async def convert_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    job_id: Optional[str] = Form(None),
    org_id: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user_id)
):
    """
    Convert documents to markdown format.
    
    This endpoint accepts multiple document files and converts them to markdown format
    using Docling. It returns a job ID that can be used to check the status and retrieve results.
    
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
            
            # Use the first organization ID
            org_id = str(orgs[0])  # Ensure it's a string
            logger.info(f"Using organization ID from user profile: {org_id}")
        else:
            logger.info(f"Using organization ID from form data: {org_id}")
        
        # Create job in database
        try:
            job_record = await create_document_conversion_job(job_id, org_id, user_id)
            
            if not job_record:
                raise HTTPException(status_code=500, detail="Failed to create conversion job")
                
            # Log success with more details
            logger.info(f"Created document conversion job record with ID: {job_id}, org_id: {org_id}")
        except Exception as e:
            # Check for foreign key constraint error
            error_str = str(e)
            if "violates foreign key constraint" in error_str and "org_id" in error_str:
                logger.error(f"Organization ID {org_id} does not exist in the organizations table. Please use a valid organization ID.")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid organization ID: {org_id}. Organization does not exist in the database."
                )
            else:
                # Re-raise the original exception with more details
                logger.error(f"Error creating document conversion job: {error_str}")
                raise HTTPException(status_code=500, detail=f"Database error: {error_str}")
        
        # Save uploaded files to temporary files
        temp_files = []
        original_filenames = []
        for file in files:
            # Create a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1])
            
            # Save the uploaded file content to the temporary file
            try:
                # Copy content
                shutil.copyfileobj(file.file, temp_file)
                temp_file.flush()
                
                # Create content record in database
                try:
                    content_record = await create_document_content_record(job_id, file.filename, org_id)
                    if content_record:
                        logger.info(f"Created content record for file {file.filename} in job {job_id}")
                    else:
                        logger.warning(f"Failed to create content record for file {file.filename} in job {job_id}, but continuing processing")
                except Exception as e:
                    error_str = str(e)
                    logger.error(f"Error creating content record for file {file.filename}: {error_str}")
                    # We'll continue processing despite this error, but log it clearly
                
                # Add to list of files to process
                temp_files.append(temp_file)
                original_filenames.append(file.filename)
                
                logger.info(f"Saved file {file.filename} to temporary file {temp_file.name}")
            except Exception as e:
                # Close and remove the temporary file on error
                temp_file.close()
                os.unlink(temp_file.name)
                logger.error(f"Error saving uploaded file {file.filename}: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error saving uploaded file: {str(e)}")
        
        # Start background task to process documents
        background_tasks.add_task(process_documents, job_id, temp_files, original_filenames, org_id, user_id)
        
        return DocToMarkdownResponse(
            job_id=job_id,
            org_id=UUID(org_id),  # Convert string to UUID
            status="pending",
            message="Document conversion job started successfully"
        )
        
    except Exception as e:
        logger.error(f"Error starting document conversion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting conversion: {str(e)}")


@router.get("/doc2md/{job_id}/status", response_model=DocToMarkdownStatusResponse)
async def get_document_conversion_status(
    job_id: str = Path(..., description="Conversion job ID"),
    org_id: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    Check the status of a document conversion job.
    
    This endpoint returns the current status of the job, including how many files
    have been processed out of the total.
    """
    logger.info(f"Checking status for document conversion job: {job_id}")
    
    try:
        # If org_id is not provided, get it from user's organizations
        if not org_id:
            orgs = await get_user_organizations(user_id)
            if not orgs:
                raise HTTPException(status_code=400, detail="User is not a member of any organization")
            org_id = str(orgs[0])
        
        # Get job from database with organization ID for security
        job = await get_document_conversion_job(job_id, org_id)
        
        if not job:
            # Return a proper 404 error if job is not found
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found for organization {org_id}"
            )
        
        logger.info(f"Found job in database: {job_id} with status {job.get('status', 'unknown')}")
        
        # Get the org_id from the job record
        org_id = job.get("org_id")
        if not org_id:
            # If for some reason org_id is missing, use a default
            org_id = "00000000-0000-0000-0000-000000000000"
            logger.warning(f"Job {job_id} has no org_id, using default")
        
        return DocToMarkdownStatusResponse(
            job_id=job_id,
            org_id=UUID(org_id),
            status=job.get("status", "unknown"),
            total_files=job.get("total_files", 0),
            completed_files=job.get("completed_files", 0),
            message=f"Job status: {job.get('status', 'unknown')}"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404 Not Found)
        raise
    except Exception as e:
        logger.error(f"Error checking document conversion job status: {str(e)}")
        # Return a proper 500 error with details
        raise HTTPException(
            status_code=500,
            detail=f"Error checking job status: {str(e)}"
        )


@router.get("/doc2md/{job_id}", response_model=DocToMarkdownResultResponse)
async def get_document_conversion_results(
    job_id: str = Path(..., description="Conversion job ID"),
    org_id: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get the results of a document conversion job.
    
    This endpoint returns the markdown content extracted from each document.
    """
    logger.info(f"Getting results for document conversion job: {job_id}")
    
    try:
        # If org_id is not provided, get it from user's organizations
        if not org_id:
            orgs = await get_user_organizations(user_id)
            if not orgs:
                raise HTTPException(status_code=400, detail="User is not a member of any organization")
            org_id = str(orgs[0])
        
        # Get job data from database with organization ID for security
        data = await get_document_content(job_id, org_id)
        
        if not data:
            # Return a proper 404 error if job is not found
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found for organization {org_id} or has no results"
            )
        
        job = data.get("job", {})
        content_data = data.get("content", [])
        
        # Get the org_id from the job record
        org_id = job.get("org_id")
        if not org_id:
            # If for some reason org_id is missing, use a default
            org_id = "00000000-0000-0000-0000-000000000000"
            logger.warning(f"Job {job_id} has no org_id, using default")
        
        # Process status based on job status
        status = job.get("status", "unknown")
        logger.info(f"Found job {job_id} with status {status} and {len(content_data)} content items")
        
        if status != "completed" and status != "failed":
            return DocToMarkdownResultResponse(
                job_id=job_id,
                org_id=UUID(org_id),
                status=status,
                total_files=job.get("total_files", 0),
                completed_files=job.get("completed_files", 0),
                error=f"Job is still {status}. Try again later."
            )
        
        # Convert content data to Pydantic models
        results = []
        for content in content_data:
            results.append(DocToMarkdownContent(
                filename=content.get("filename", ""),
                status=content.get("status", "unknown"),
                markdown_text=content.get("markdown_text"),
                error=content.get("error"),
                metadata=content.get("metadata"),
                org_id=UUID(org_id)
            ))
        
        return DocToMarkdownResultResponse(
            job_id=job_id,
            org_id=UUID(org_id),
            status=status,
            total_files=job.get("total_files", 0),
            completed_files=job.get("completed_files", 0),
            results=results
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404 Not Found)
        raise
    except Exception as e:
        logger.error(f"Error retrieving document conversion results: {str(e)}")
        # Return a proper 500 error with details
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving results: {str(e)}"
        )
