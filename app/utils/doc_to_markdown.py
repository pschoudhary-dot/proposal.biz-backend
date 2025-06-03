"""
Utility functions for document to markdown conversion using Docling.
"""
from typing import List, Optional
import asyncio
import os
import tempfile
from datetime import datetime
from docling.document_converter import DocumentConverter
from app.core.config import settings
from app.core.logging import logger
from app.core.database import (
    update_document_content,
    update_document_conversion_status,
    update_document_file_count,
    create_document_record,
    create_org_content_source_record,
    update_content_source_with_chunks
)
from app.utils.convert_to_vector import process_document


async def process_documents(
    job_id: str, 
    files: List[tempfile._TemporaryFileWrapper], 
    original_filenames: List[str] = None, 
    org_id: str = None,
    user_id: str = None
) -> None:
    """
    Process multiple documents for conversion to markdown.
    
    Args:
        job_id: The unique job identifier
        files: List of temporary file objects
        original_filenames: List of original filenames (optional)
    """
    logger.info(f"Starting document conversion for job {job_id} with {len(files)} files")
    
    try:
        # Update job status to running
        try:
            await update_document_conversion_status(job_id, "running", org_id)
            logger.info(f"Updated job {job_id} status to running")
        except Exception as e:
            logger.error(f"Failed to update job {job_id} status to running: {str(e)}")
            # Continue processing despite this error
        
        # Update the total file count
        try:
            await update_document_file_count(job_id, len(files), org_id)
            logger.info(f"Updated job {job_id} with {len(files)} total files")
        except Exception as e:
            logger.error(f"Failed to update file count for job {job_id}: {str(e)}")
            # Continue processing despite this error
        
        # If no original filenames provided, use the temp file names
        if not original_filenames:
            original_filenames = [os.path.basename(f.name) for f in files]
        
        # Process each file individually
        tasks = []
        for i, temp_file in enumerate(files):
            # Get the original filename for this file
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
            # Add a small delay between tasks to avoid resource contention
            await asyncio.sleep(0.5)
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        
        # Update job status to completed
        try:
            await update_document_conversion_status(job_id, "completed", org_id)
            logger.info(f"Completed processing all documents for job {job_id}")
        except Exception as e:
            logger.error(f"Failed to update job {job_id} status to completed: {str(e)}")
            # Log completion anyway
            logger.info(f"Document processing completed for job {job_id} but status update failed")
        
    except Exception as e:
        logger.error(f"Error in processing documents for job {job_id}: {str(e)}")
        # Try to update status to failed
        try:
            await update_document_conversion_status(job_id, "failed", org_id)
            logger.info(f"Updated job {job_id} status to failed")
        except Exception as status_error:
            logger.error(f"Failed to update job {job_id} status to failed: {str(status_error)}")
        # Log detailed error information
        logger.error(f"Document processing failed for job {job_id}. Error details: {str(e)}")


async def process_single_document(
    job_id: str, 
    temp_file: tempfile._TemporaryFileWrapper, 
    original_filename: str = None, 
    org_id: str = None,
    user_id: str = None
) -> None:
    """
    Process a single document for conversion to markdown.
    
    Args:
        job_id: The unique job identifier
        temp_file: Temporary file object
        original_filename: The original filename as uploaded by the user
    """
    # Use the original filename if provided, otherwise use the temp file name
    filename = original_filename if original_filename else os.path.basename(temp_file.name)
    
    logger.info(f"Processing document with original filename: {filename} for job {job_id}")
    
    # Create document and content source records
    document_id = None
    content_source_id = None
    
    if user_id and org_id:
        try:
            # Create document record
            document_id = await create_document_record(job_id, filename, org_id, user_id)
            logger.info(f"Created document record {document_id} for file {filename}")
            
            # Create content source record
            content_source_id = await create_org_content_source_record(
                job_id, filename, org_id, user_id, document_id
            )
            logger.info(f"Created content source record {content_source_id} for file {filename}")
        except Exception as e:
            logger.error(f"Error creating document/content source records for {filename}: {str(e)}")
            # Continue processing even if record creation fails
    
    try:
        logger.info(f"Processing document {filename} for job {job_id}")
        
        # Initialize Docling converter
        converter = DocumentConverter()
        
        # Convert the document to markdown
        result = converter.convert(temp_file.name)
        
        if result and hasattr(result, "document"):
            # Extract markdown
            markdown_text = result.document.export_to_markdown()
            
            # Extract metadata
            metadata = {
                "format": str(result.input.format) if hasattr(result.input, "format") else "unknown",
                "pages": result.document.num_pages() if hasattr(result.document, "num_pages") else 0
            }
            
            # Log success
            logger.info(f"Successfully converted document {filename} for job {job_id}")
            logger.info(f"Generated {len(markdown_text)} characters of markdown")
            
            # Save to database
            await update_document_content(
                job_id=job_id,
                filename=filename,
                markdown_text=markdown_text,
                status="completed",
                metadata=metadata,
                org_id=org_id
            )
            
            logger.info(f"Successfully saved data for document {filename} in job {job_id}")
            
            # Process document for chunking and embedding if we have the required data
            if content_source_id and org_id and user_id and markdown_text.strip():
                try:
                    logger.info(f"Starting chunking and embedding for document {filename}")
                    
                    # Create metadata for the document processing
                    doc_metadata = {
                        "filename": filename,
                        "document_id": document_id,
                        "content_source_id": content_source_id,
                        "job_id": job_id,
                        "processing_date": datetime.now().isoformat()
                    }
                    doc_metadata.update(metadata)  # Add conversion metadata
                    
                    # Process the document for chunking and embedding
                    chunk_ids = await process_document(
                        document_id=content_source_id,  # Use content source ID as document ID
                        org_id=org_id,
                        user_id=user_id,
                        text=markdown_text,
                        metadata=doc_metadata,
                        use_semantic_chunking=True
                    )
                    
                    if chunk_ids:
                        logger.info(f"Successfully created {len(chunk_ids)} chunks for document {filename}")
                        
                        # Update content source with chunk information
                        await update_content_source_with_chunks(content_source_id, chunk_ids)
                    else:
                        logger.warning(f"No chunks created for document {filename}")
                        
                except Exception as e:
                    logger.error(f"Error processing document {filename} for chunking/embedding: {str(e)}")
                    # Continue without failing the whole process
            else:
                logger.warning(f"Skipping chunking/embedding for {filename} - missing required data")
                logger.debug(f"Debug info - content_source_id: {content_source_id}, org_id: {org_id}, user_id: {user_id}, markdown_length: {len(markdown_text) if markdown_text else 0}")
        else:
            logger.error(f"No data returned from Docling for document {filename}")
            await update_document_content(
                job_id=job_id,
                filename=filename,
                markdown_text="",
                status="failed",
                metadata={"error": "No data returned from conversion"},
                org_id=org_id
            )
            
    except Exception as e:
        logger.error(f"Error processing document {filename}: {str(e)}")
        # Save the error to the database
        await update_document_content(
            job_id=job_id,
            filename=filename,
            markdown_text="",
            status="failed",
            metadata={"error": str(e)},
            org_id=org_id
        )
    finally:
        # Close and remove the temporary file
        try:
            temp_file.close()
        except Exception as e:
            logger.error(f"Error closing temporary file {filename}: {str(e)}")
