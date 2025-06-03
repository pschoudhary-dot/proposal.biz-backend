"""
Utility functions for document to markdown conversion using Docling Server.
"""
from typing import List, Optional
import asyncio
import os
import tempfile
from datetime import datetime
from app.core.config import settings
from app.core.logging import logger
from app.core.database import (
    create_document_record,
    create_org_content_source_record,
    update_document_content,
    update_document_content_task_id,
    update_document_conversion_status,
    update_document_file_count,
    update_content_source_with_chunks
)
from app.utils.convert_to_vector import process_document
from app.utils.docling_client import docling_client

# Allowed file extensions for document conversion
ALLOWED_EXTENSIONS = {
    '.pdf', '.docx', '.pptx', '.html', '.md', 
    '.txt', '.rtf', '.odt', '.xml', '.csv', '.xlsx'
}


async def process_documents(
    job_id: str, 
    files: List[tempfile._TemporaryFileWrapper], 
    original_filenames: List[str] = None, 
    org_id: str = None,
    user_id: str = None
) -> None:
    """
    Process multiple documents for conversion to markdown using Docling server.
    
    Args:
        job_id: The unique job identifier (will be replaced by task_id for each file)
        files: List of temporary file objects
        original_filenames: List of original filenames
        org_id: Organization ID
        user_id: User ID
    """
    logger.info(f"Starting document conversion for job {job_id} with {len(files)} files")
    
    try:
        # Update job status to running
        await update_document_conversion_status(job_id, "running", org_id)
        await update_document_file_count(job_id, len(files), org_id)
        
        if not original_filenames:
            original_filenames = [os.path.basename(f.name) for f in files]
        
        # Process each file
        tasks = []
        for i, temp_file in enumerate(files):
            original_filename = original_filenames[i] if i < len(original_filenames) else os.path.basename(temp_file.name)
            
            # Create a task for each file
            task = asyncio.create_task(process_single_document(
                job_id=job_id,
                temp_file=temp_file,
                original_filename=original_filename,
                org_id=org_id,
                user_id=user_id
            ))
            tasks.append(task)
            await asyncio.sleep(0.1)  # Small delay between submissions
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        
        # Update job status to completed
        await update_document_conversion_status(job_id, "completed", org_id)
        logger.info(f"Completed processing all documents for job {job_id}")
        
    except Exception as e:
        logger.error(f"Error in processing documents for job {job_id}: {str(e)}")
        await update_document_conversion_status(job_id, "failed", org_id)


async def process_single_document(
    job_id: str, 
    temp_file: tempfile._TemporaryFileWrapper, 
    original_filename: str = None, 
    org_id: str = None,
    user_id: str = None
) -> None:
    """
    Process a single document for conversion to markdown using Docling server.
    """
    filename = original_filename if original_filename else os.path.basename(temp_file.name)
    logger.info(f"Processing document: {filename} for job {job_id}")
    
    # Validate file extension
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        error_msg = f"File type {file_ext} not supported. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        logger.error(error_msg)
        await update_document_content(
            job_id=job_id,
            filename=filename,
            markdown_text="",
            status="failed",
            metadata={"error": error_msg},
            org_id=org_id
        )
        return

    # Create document and content source records
    document_id = None
    content_source_id = None
    
    if user_id and org_id:
        try:
            document_id = await create_document_record(job_id, filename, org_id, user_id)
            content_source_id = await create_org_content_source_record(
                job_id, filename, org_id, user_id, document_id
            )
        except Exception as e:
            error_msg = f"Error creating document records for {filename}: {str(e)}"
            logger.error(error_msg)
            await update_document_content(
                job_id=job_id,
                filename=filename,
                markdown_text="",
                status="failed",
                metadata={"error": error_msg},
                org_id=org_id
            )
            return
    
    try:
        # Read file content
        with open(temp_file.name, 'rb') as f:
            file_content = f.read()
        
        # Check if file is already markdown
        if filename.lower().endswith('.md'):
            logger.info(f"File {filename} is already markdown, storing directly")
            
            # Decode content as UTF-8
            try:
                markdown_text = file_content.decode('utf-8')
            except UnicodeDecodeError:
                # Try with latin-1 if UTF-8 fails
                markdown_text = file_content.decode('latin-1')
            
            # Store directly without conversion
            metadata = {
                "format": "markdown",
                "original_format": "markdown",
                "direct_storage": True,
                "file_size": len(file_content)
            }
            
            await update_document_content(
                job_id=job_id,
                filename=filename,
                markdown_text=markdown_text,
                status="completed",
                metadata=metadata,
                org_id=org_id
            )
            
            logger.info(f"Stored markdown file {filename} directly without conversion")
            
        else:
            # Submit to Docling server for conversion with retry logic
            logger.info(f"Submitting {filename} to Docling server for conversion")
            
            try:
                # Submit file for async conversion with retry
                submit_response = await docling_client.convert_file_async_with_retry(
                    file_content=file_content,
                    filename=filename,
                    to_formats=["md"],
                    options={
                        "do_ocr": True,
                        "do_table_structure": True
                    },
                    max_retries=3
                )
                
                task_id = submit_response.get("task_id")
                if not task_id:
                    raise ValueError("No task_id received from Docling server")
                
                logger.info(f"Docling server task_id for {filename}: {task_id}")
                
                # Store the task_id in the database
                await update_document_content_task_id(job_id, filename, task_id, org_id)
                
            except Exception as e:
                error_msg = f"Failed to submit document for conversion: {str(e)}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # Wait for completion
            await docling_client.wait_for_completion(task_id)
            
            # Get results
            result = await docling_client.get_result(task_id)
            
            # Extract markdown content from result
            document_data = result.get("document", {})
            markdown_text = document_data.get("md_content", "")
            
            if not markdown_text:
                raise Exception("No markdown content in result")
            
            # Extract metadata
            metadata = {
                "format": document_data.get("filename", "").split('.')[-1] if document_data.get("filename") else "unknown",
                "task_id": task_id,
                "processing_time": result.get("processing_time", 0),
                "docling_metadata": result.get("timings", {})
            }
            
            logger.info(f"Successfully converted {filename} - {len(markdown_text)} characters")
            
            # Save to database
            await update_document_content(
                job_id=job_id,
                filename=filename,
                markdown_text=markdown_text,
                status="completed",
                metadata=metadata,
                org_id=org_id
            )
        
        # Process for chunking and embedding if we have the data
        if content_source_id and org_id and user_id and markdown_text.strip():
            try:
                logger.info(f"Starting chunking and embedding for document {filename}")
                
                doc_metadata = {
                    "filename": filename,
                    "document_id": document_id,
                    "content_source_id": content_source_id,
                    "job_id": job_id,
                    "processing_date": datetime.now().isoformat()
                }
                if 'metadata' in locals():
                    doc_metadata.update(metadata)
                
                chunk_ids = await process_document(
                    document_id=content_source_id,
                    org_id=org_id,
                    user_id=user_id,
                    text=markdown_text,
                    metadata=doc_metadata,
                    use_semantic_chunking=True
                )
                
                if chunk_ids:
                    logger.info(f"Created {len(chunk_ids)} chunks for {filename}")
                    await update_content_source_with_chunks(content_source_id, chunk_ids)
                    
            except Exception as e:
                logger.error(f"Error processing chunks for {filename}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error processing document {filename}: {str(e)}")
        await update_document_content(
            job_id=job_id,
            filename=filename,
            markdown_text="",
            status="failed",
            metadata={"error": str(e)},
            org_id=org_id
        )
    finally:
        try:
            temp_file.close()
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
        except Exception as e:
            logger.error(f"Error cleaning up temp file: {str(e)}")