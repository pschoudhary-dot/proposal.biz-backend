# """
# Utility functions for document to markdown conversion using Apify Docling.
# """
# from typing import List, Optional, Dict, Any, Union
# import asyncio
# from datetime import datetime

# from app.core.config import settings
# from app.core.logging import logger
# from app.core.database import (
#     update_document_content,
#     update_processing_job_status,
#     update_processing_job_total_items,
#     create_document_record,
#     create_org_content_source_record,
#     update_content_source_with_chunks
# )
# from app.utils.convert_to_vector import process_document
# from app.utils.apify_client import process_documents_with_apify
# from app.utils.storage_utils import upload_files_data_to_storage


# async def process_documents(
#     job_id: str, 
#     file_data: List[Dict[str, Union[bytes, str]]], 
#     org_id: int,
#     user_id: int
# ) -> None:
#     """
#     Process multiple documents for conversion to markdown using Apify.
    
#     Args:
#         job_id: The unique job identifier
#         file_data: List of file data dictionaries with content, filename, content_type
#         org_id: Organization ID (integer)
#         user_id: User ID (integer)
#     """
#     logger.info(f"Starting document conversion for job {job_id} with {len(file_data)} files")
    
#     try:
#         # Update job status to running
#         try:
#             await update_processing_job_status(job_id, "processing", org_id=org_id)
#             logger.info(f"Updated job {job_id} status to processing")
#         except Exception as e:
#             logger.error(f"Failed to update job {job_id} status to processing: {str(e)}")
#             # Continue processing despite this error
        
#         # Update the total file count
#         try:
#             await update_processing_job_total_items(job_id, len(file_data), org_id)
#             logger.info(f"Updated job {job_id} with {len(file_data)} total files")
#         except Exception as e:
#             logger.error(f"Failed to update file count for job {job_id}: {str(e)}")
#             # Continue processing despite this error
        
#         # Upload files to Supabase storage first
#         logger.info(f"Uploading {len(file_data)} files to storage for job {job_id}")
        
#         # Convert file_data format for storage upload
#         storage_file_data = []
#         for file_info in file_data:
#             storage_file_data.append({
#                 "content": file_info["content"],
#                 "filename": file_info["filename"], 
#                 "content_type": file_info["content_type"]
#             })
        
#         upload_results = await upload_files_data_to_storage(storage_file_data, org_id, "documents")
        
#         # Filter successful uploads and get URLs
#         successful_uploads = [result for result in upload_results if result.get("success")]
#         if not successful_uploads:
#             failed_files = [result.get("original_filename", "unknown") for result in upload_results if not result.get("success")]
#             raise Exception(f"No files were successfully uploaded to storage. Failed files: {failed_files}")
        
#         document_urls = [result["public_url"] for result in successful_uploads]
#         logger.info(f"Successfully uploaded {len(document_urls)} files, processing with Apify")
        
#         # Process documents with Apify
#         logger.info(f"Document URLs for Apify: {document_urls}")
#         apify_results = await process_documents_with_apify(
#             urls=document_urls,
#             output_formats=["md"],
#             do_ocr=False
#         )
        
#         logger.info(f"Apify processing completed for job {job_id}")
        
#         # Process each document result
#         processed_count = 0
#         for upload_result, apify_doc in zip(successful_uploads, apify_results.get("documents", [])):
#             try:
#                 await process_single_document_result(
#                     job_id=job_id,
#                     org_id=org_id,
#                     user_id=user_id,
#                     upload_result=upload_result,
#                     apify_doc=apify_doc
#                 )
#                 processed_count += 1
                
#                 # Update job progress
#                 await update_processing_job_status(job_id=job_id, status="processing", processed_count=processed_count, org_id=org_id)
                
#             except Exception as e:
#                 logger.error(f"Error processing document {upload_result['original_filename']}: {str(e)}")
#                 # Continue with other documents
        
#         # Update job status to completed
#         try:
#             final_status = "completed" if processed_count > 0 else "failed"
#             await update_processing_job_status(job_id=job_id, status=final_status, processed_count=processed_count, org_id=org_id)
#             logger.info(f"Completed processing {processed_count} documents for job {job_id}")
#         except Exception as e:
#             logger.error(f"Failed to update job {job_id} status to completed: {str(e)}")
        
#     except Exception as e:
#         logger.error(f"Error in processing documents for job {job_id}: {str(e)}")
#         # Try to update status to failed
#         try:
#             await update_processing_job_status(job_id=job_id, status="failed", org_id=org_id, error_message=str(e))
#             logger.info(f"Updated job {job_id} status to failed")
#         except Exception as status_error:
#             logger.error(f"Failed to update job {job_id} status to failed: {str(status_error)}")


# async def process_single_document_result(
#     job_id: str,
#     org_id: int,
#     user_id: int,
#     upload_result: Dict[str, Any],
#     apify_doc: Dict[str, Any]
# ) -> None:
#     """
#     Process a single document result from Apify.
    
#     Args:
#         job_id: The unique job identifier
#         org_id: Organization ID (integer)
#         user_id: User ID (integer)
#         upload_result: Upload result from storage
#         apify_doc: Document result from Apify
#     """
#     filename = upload_result["original_filename"]
    
#     logger.info(f"Processing document result for {filename} in job {job_id}")
    
#     # Create document and content source records
#     document_id = None
#     content_source_id = None
    
#     try:
#         # Create document record
#         document_id = await create_document_record(job_id, filename, org_id, user_id)
#         logger.info(f"Created document record {document_id} for file {filename}")
        
#         # Create content source record
#         content_source_id = await create_org_content_source_record(
#             job_id, filename, org_id, user_id, document_id
#         )
#         logger.info(f"Created content source record {content_source_id} for file {filename}")
#     except Exception as e:
#         logger.error(f"Error creating document/content source records for {filename}: {str(e)}")
#         # Continue processing even if record creation fails
    
#     try:
#         # Extract markdown content from Apify result
#         markdown_text = ""
#         status = "failed"
#         metadata = {
#             "apify_status": apify_doc.get("status", "unknown"),
#             "file_url": upload_result["public_url"],
#             "file_path": upload_result["file_path"],
#             "content_type": upload_result["content_type"],
#             "file_size": upload_result["size"]
#         }
        
#         if apify_doc.get("status") == "completed" and apify_doc.get("content"):
#             markdown_text = apify_doc["content"]
#             status = "completed"
#             metadata.update(apify_doc.get("metadata", {}))
            
#             logger.info(f"Successfully extracted {len(markdown_text)} characters of markdown from {filename}")
#         else:
#             error_msg = f"Apify processing failed for {filename}: {apify_doc.get('status', 'unknown status')}"
#             logger.error(error_msg)
#             metadata["error"] = error_msg
        
#         # Save to database
#         await update_document_content(
#             job_id=job_id,
#             filename=filename,
#             markdown_text=markdown_text,
#             status=status,
#             metadata=metadata,
#             org_id=org_id
#         )
        
#         logger.info(f"Successfully saved data for document {filename} in job {job_id}")
        
#         # Process document for chunking and embedding if we have the required data
#         if content_source_id and markdown_text.strip() and status == "completed":
#             try:
#                 logger.info(f"Starting chunking and embedding for document {filename}")
                
#                 # Create metadata for the document processing
#                 doc_metadata = {
#                     "filename": filename,
#                     "document_id": document_id,
#                     "content_source_id": content_source_id,
#                     "job_id": job_id,
#                     "processing_date": datetime.now().isoformat(),
#                     "source_url": upload_result["public_url"]
#                 }
#                 doc_metadata.update(metadata)  # Add conversion metadata
                
#                 # Process the document for chunking and embedding
#                 chunk_ids = await process_document(
#                     source_id=content_source_id,  # Use content source ID as document ID
#                     org_id=org_id,
#                     user_id=user_id,
#                     text=markdown_text,
#                     metadata=doc_metadata,
#                     use_semantic_chunking=True
#                 )
                
#                 if chunk_ids:
#                     logger.info(f"Successfully created {len(chunk_ids)} chunks for document {filename}")
                    
#                     # Update content source with chunk information
#                     await update_content_source_with_chunks(content_source_id, chunk_ids)
#                 else:
#                     logger.warning(f"No chunks created for document {filename}")
                    
#             except Exception as e:
#                 logger.error(f"Error processing document {filename} for chunking/embedding: {str(e)}")
#                 # Continue without failing the whole process
#         else:
#             logger.warning(f"Skipping chunking/embedding for {filename} - missing required data or failed conversion")
#             logger.debug(f"Debug info - content_source_id: {content_source_id}, org_id: {org_id}, user_id: {user_id}, markdown_length: {len(markdown_text) if markdown_text else 0}, status: {status}")
            
#     except Exception as e:
#         logger.error(f"Error processing document {filename}: {str(e)}")
#         # Save the error to the database
#         await update_document_content(
#             job_id=job_id,
#             filename=filename,
#             markdown_text="",
#             status="failed",
#             metadata={"error": str(e)},
#             org_id=org_id
#         )

"""
Utility functions for document to markdown conversion using Apify Docling.
"""
from typing import List, Optional, Dict, Any, Union
import asyncio
from datetime import datetime
import os

from app.core.config import settings
from app.core.logging import logger
from app.core.database import (
    update_document_content,
    update_processing_job_status,
    update_processing_job_total_items,
    create_document_record,
    create_org_content_source_record,
    update_content_source_with_chunks
)
from app.utils.convert_to_vector import process_document
from app.utils.apify_client import process_documents_with_apify
from app.utils.storage_utils import upload_files_data_to_storage


async def process_documents(
    job_id: str,
    file_data: List[Dict[str, Union[bytes, str]]],
    org_id: int,
    user_id: int
) -> None:
    """
    Process multiple documents for conversion to markdown using Apify.
    
    Args:
        job_id: The unique job identifier
        file_data: List of file data dictionaries with content, filename, content_type
        org_id: Organization ID (integer)
        user_id: User ID (integer)
    """
    logger.info(f"Starting document conversion for job {job_id} with {len(file_data)} files")
    
    try:
        await update_processing_job_status(job_id, "processing", org_id=org_id)
        logger.info(f"Updated job {job_id} status to processing")

        await update_processing_job_total_items(job_id, len(file_data), org_id)
        logger.info(f"Updated job {job_id} with {len(file_data)} total files")

        logger.info(f"Uploading {len(file_data)} files to storage for job {job_id}")
        storage_file_data = [
            {
                "content": file_info["content"],
                "filename": file_info["filename"],
                "content_type": file_info["content_type"]
            } for file_info in file_data
        ]
        
        upload_results = await upload_files_data_to_storage(storage_file_data, org_id, "documents")
        
        successful_uploads = [result for result in upload_results if result.get("success")]
        if not successful_uploads:
            failed_files = [result.get("original_filename", "unknown") for result in upload_results if not result.get("success")]
            raise Exception(f"No files were successfully uploaded to storage. Failed files: {failed_files}")

        document_urls = [result["public_url"] for result in successful_uploads]
        logger.info(f"Successfully uploaded {len(document_urls)} files, processing with Apify")

        apify_results = await process_documents_with_apify(urls=document_urls, output_formats=["md"], do_ocr=True)
        
        logger.info(f"Apify processing completed for job {job_id}")
        
        processed_count = 0
        for upload_result in successful_uploads:
            try:
                storage_filename = os.path.basename(upload_result["file_path"])
                expected_zip_filename = os.path.splitext(storage_filename)[0] + ".md"

                markdown_text = apify_results.get("extracted_content", {}).get(expected_zip_filename)

                await process_single_document_result(
                    job_id=job_id,
                    org_id=org_id,
                    user_id=user_id,
                    upload_result=upload_result,
                    markdown_text=markdown_text,
                    apify_metadata=apify_results
                )
                if markdown_text:
                    processed_count += 1
                
                await update_processing_job_status(job_id=job_id, status="processing", completed_items=processed_count, org_id=org_id)

            except Exception as e:
                logger.error(f"Error processing document {upload_result['original_filename']}: {str(e)}", exc_info=True)

        final_status = "completed" if processed_count == len(successful_uploads) else "completed_with_errors"
        if processed_count == 0:
            final_status = "failed"
            
        await update_processing_job_status(job_id=job_id, status=final_status, completed_items=processed_count, org_id=org_id)
        logger.info(f"Completed processing {processed_count}/{len(successful_uploads)} documents for job {job_id}. Final status: {final_status}")
    
    except Exception as e:
        logger.error(f"Critical error in processing documents for job {job_id}: {str(e)}", exc_info=True)
        try:
            await update_processing_job_status(job_id=job_id, status="failed", org_id=org_id, error_message=str(e))
            logger.info(f"Updated job {job_id} status to failed due to critical error.")
        except Exception as status_error:
            logger.error(f"Failed to update job {job_id} status to failed: {str(status_error)}")

async def process_single_document_result(
    job_id: str,
    org_id: int,
    user_id: int,
    upload_result: Dict[str, Any],
    markdown_text: Optional[str],
    apify_metadata: Dict[str, Any]
) -> None:
    """
    Process a single document result from Apify.
    """
    filename = upload_result["original_filename"]
    logger.info(f"Processing document result for {filename} in job {job_id}")

    document_id = await create_document_record(job_id, filename, org_id, user_id)
    content_source_id = await create_org_content_source_record(job_id, filename, org_id, user_id, document_id)
    
    if not document_id or not content_source_id:
        logger.error(f"Failed to create database records for {filename}, aborting processing for this file.")
        return

    try:
        metadata = {
            "apify_run_id": apify_metadata.get("run_id"),
            "apify_status": apify_metadata.get("status"),
            "file_url": upload_result["public_url"],
            "file_path": upload_result["file_path"],
            "content_type": upload_result["content_type"],
            "file_size": upload_result["size"]
        }
        
        status = "completed" if markdown_text else "failed"
        if status == "completed":
            logger.info(f"Successfully extracted {len(markdown_text)} characters of markdown from {filename}")
        else:
            error_msg = f"Apify processing failed for {filename} or markdown not found in output ZIP."
            logger.error(error_msg)
            metadata["error"] = error_msg
        
        await update_document_content(
            job_id=job_id,
            filename=filename,
            markdown_text=markdown_text or "",
            status=status,
            metadata=metadata,
            org_id=org_id
        )
        logger.info(f"Successfully saved data for document {filename} in job {job_id} with status {status}")

        if content_source_id and markdown_text and status == "completed":
            try:
                logger.info(f"Starting chunking and embedding for document {filename}")
                doc_metadata = {
                    "filename": filename,
                    "document_id": str(document_id),
                    "content_source_id": str(content_source_id),
                    "job_id": job_id,
                    "processing_date": datetime.now().isoformat(),
                    "source_url": upload_result["public_url"]
                }
                doc_metadata.update(metadata)

                chunk_ids = await process_document(
                    source_id=str(content_source_id),
                    org_id=org_id,
                    user_id=user_id,
                    text=markdown_text,
                    metadata=doc_metadata,
                    use_semantic_chunking=True
                )
                
                if chunk_ids:
                    logger.info(f"Successfully created {len(chunk_ids)} chunks for document {filename}")
                    await update_content_source_with_chunks(str(content_source_id), [str(cid) for cid in chunk_ids])
                else:
                    logger.warning(f"No chunks created for document {filename}")
            except Exception as e:
                logger.error(f"Error during chunking for {filename}: {str(e)}", exc_info=True)
        else:
            logger.warning(f"Skipping chunking/embedding for {filename} - missing required data or failed conversion")

    except Exception as e:
        logger.error(f"Error during final processing of document {filename}: {str(e)}", exc_info=True)
        await update_document_content(
            job_id=job_id,
            filename=filename,
            markdown_text="",
            status="failed",
            metadata={"error": str(e)},
            org_id=org_id
        )
