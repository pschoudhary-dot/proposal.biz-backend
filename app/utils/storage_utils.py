"""
Utility functions for Supabase storage operations.
"""
import uuid
import os
from typing import Optional, Dict, Any
from fastapi import UploadFile
import asyncio
from app.core.config import settings
from app.core.logging import logger
from supabase import create_client


def is_upload_successful(upload_result) -> bool:
    """
    Check if Supabase upload was successful by examining the result object.
    Different versions of Supabase client may return different formats.
    """
    if not upload_result:
        return False
    
    # Check for common success indicators
    success_indicators = [
        hasattr(upload_result, 'path'),
        hasattr(upload_result, 'id'), 
        hasattr(upload_result, 'fullPath'),
        hasattr(upload_result, 'Key'),
        hasattr(upload_result, 'name')
    ]
    
    return any(success_indicators)


class SupabaseStorageClient:
    """Client for managing Supabase storage operations."""
    
    def __init__(self):
        """Initialize Supabase storage client."""
        self.supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        self.bucket_name = settings.STORAGE_BUCKET_NAME  # Use configurable bucket name
    
    async def upload_document(
        self, 
        file: UploadFile, 
        org_id: int,
        folder: str = "documents"
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a document to Supabase storage.
        
        Args:
            file: The uploaded file
            org_id: Organization ID
            folder: Folder in storage bucket
            
        Returns:
            Dictionary with upload results including public URL
        """
        try:
            # Generate unique filename
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = f"{folder}/{org_id}/{unique_filename}"
            
            # Read file content
            file_content = await file.read()
            
            # Upload to Supabase storage
            upload_result = self.supabase.storage.from_(self.bucket_name).upload(
                file_path,
                file_content,
                {
                    "content-type": file.content_type,
                    "x-upsert": "true"  # Allow overwrite if file exists
                }
            )
            
            # Check if upload was successful using robust checking
            if is_upload_successful(upload_result):
                # Get public URL
                public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)
                
                logger.info(f"Successfully uploaded {file.filename} to {file_path}")
                
                return {
                    "success": True,
                    "file_path": file_path,
                    "public_url": public_url,
                    "original_filename": file.filename,
                    "content_type": file.content_type,
                    "size": len(file_content)
                }
            else:
                logger.error(f"Failed to upload file: {upload_result}")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading file to storage: {str(e)}")
            return None
    
    def upload_file_data(
        self, 
        file_data: Dict[str, Any], 
        org_id: int,
        folder: str = "documents"
    ) -> Optional[Dict[str, Any]]:
        """
        Upload file data to Supabase storage.
        
        Args:
            file_data: Dictionary containing filename, content, content_type, size
            org_id: Organization ID
            folder: Folder in storage bucket
            
        Returns:
            Dictionary with upload results including public URL
        """
        try:
            filename = file_data["filename"]
            content = file_data["content"]
            content_type = file_data["content_type"]
            
            # Generate unique filename
            file_extension = os.path.splitext(filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = f"{folder}/{org_id}/{unique_filename}"
            
            # Upload to Supabase storage
            upload_result = self.supabase.storage.from_(self.bucket_name).upload(
                file_path,
                content,
                {
                    "content-type": content_type,
                    "x-upsert": "true"  # Allow overwrite if file exists
                }
            )
            
            # Check if upload was successful using robust checking
            if is_upload_successful(upload_result):
                # Get public URL
                public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)
                
                logger.info(f"Successfully uploaded {filename} to {file_path}")
                
                return {
                    "success": True,
                    "file_path": file_path,
                    "public_url": public_url,
                    "original_filename": filename,
                    "content_type": content_type,
                    "size": len(content)
                }
            else:
                logger.error(f"Failed to upload file {filename}: {upload_result}")
                return {
                    "success": False,
                    "original_filename": filename,
                    "error": f"Upload failed: {upload_result}"
                }
                
        except Exception as e:
            logger.error(f"Error uploading file data to storage: {str(e)}")
            return {
                "success": False,
                "original_filename": file_data.get("filename", "unknown"),
                "error": str(e)
            }
    
    def upload_multiple_file_data(
        self, 
        files_data: list[Dict[str, Any]], 
        org_id: int,
        folder: str = "documents"
    ) -> list[Dict[str, Any]]:
        """
        Upload multiple file data objects to Supabase storage.
        
        Args:
            files_data: List of file data dictionaries
            org_id: Organization ID
            folder: Folder in storage bucket
            
        Returns:
            List of upload results
        """
        results = []
        
        for file_data in files_data:
            result = self.upload_file_data(file_data, org_id, folder)
            results.append(result)
        
        return results
    
    def delete_document(self, file_path: str) -> bool:
        """
        Delete a document from Supabase storage.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.supabase.storage.from_(self.bucket_name).remove([file_path])
            
            if response:
                logger.info(f"Successfully deleted {file_path}")
                return True
            else:
                logger.error(f"Failed to delete {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False
    
    def get_public_url(self, file_path: str) -> Optional[str]:
        """
        Get public URL for a file in storage.
        
        Args:
            file_path: Path to the file in storage
            
        Returns:
            Public URL or None if error
        """
        try:
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)
            return public_url
        except Exception as e:
            logger.error(f"Error getting public URL: {str(e)}")
            return None


def ensure_storage_bucket_exists(storage_client: SupabaseStorageClient) -> bool:
    """
    Ensure the storage bucket exists in Supabase.
    
    Returns:
        bool: True if the bucket exists or was created successfully, False otherwise
    """
    try:
        # Check if bucket exists
        bucket_response = storage_client.supabase.storage.get_bucket(storage_client.bucket_name)
        if bucket_response and hasattr(bucket_response, 'name'):
            logger.info(f"Storage bucket '{storage_client.bucket_name}' exists")
            return True
            
    except Exception as e:
        logger.warning(f"Storage bucket check failed, attempting to create: {str(e)}")
        try:
            # Try to create the bucket if it doesn't exist
            create_response = storage_client.supabase.storage.create_bucket(
                storage_client.bucket_name,
                public=True,  # Make bucket publicly accessible
                file_size_limit=1024 * 1024 * 50,  # 50MB file size limit
                allowed_mime_types=["*/*"]  # Allow all file types
            )
            logger.info(f"Created storage bucket: {storage_client.bucket_name}")
            return True
        except Exception as create_error:
            logger.error(f"Failed to create storage bucket: {str(create_error)}")
            return False
    
    return False


# Create singleton instance
storage_client = SupabaseStorageClient()
ensure_storage_bucket_exists(storage_client)


# Convenience functions
async def upload_document_to_storage(
    file: UploadFile, 
    org_id: int,
    folder: str = "documents"
) -> Optional[Dict[str, Any]]:
    """Upload a single document to storage."""
    return await storage_client.upload_document(file, org_id, folder)


async def upload_single_file_data_to_storage(
    file_data: Dict[str, Any], 
    org_id: int,
    folder: str = "documents"
) -> Optional[Dict[str, Any]]:
    """Upload a single file data object to storage."""
    return storage_client.upload_file_data(file_data, org_id, folder)


async def upload_files_data_to_storage(
    files_data: list[Dict[str, Any]], 
    org_id: int,
    folder: str = "documents"
) -> list[Dict[str, Any]]:
    """
    Upload multiple file data objects to storage asynchronously.
    
    Args:
        files_data: List of file data dictionaries
        org_id: Organization ID
        folder: Folder in storage bucket
        
    Returns:
        List of upload results
    """
    tasks = []
    for file_data in files_data:
        tasks.append(upload_single_file_data_to_storage(file_data, org_id, folder))
    
    # Run uploads concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    processed_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Error during file upload: {str(result)}")
            processed_results.append({
                "success": False,
                "error": str(result),
                "original_filename": "unknown"
            })
        else:
            processed_results.append(result)
    
    return processed_results


async def upload_documents_to_storage(
    files: list[UploadFile], 
    org_id: int,
    folder: str = "documents"
) -> list[Dict[str, Any]]:
    """Upload multiple documents to storage."""
    results = []
    
    for file in files:
        result = await storage_client.upload_document(file, org_id, folder)
        if result:
            results.append(result)
        else:
            results.append({
                "success": False,
                "original_filename": file.filename,
                "error": "Upload failed"
            })
    
    return results


def delete_document_from_storage(file_path: str) -> bool:
    """Delete a document from storage."""
    return storage_client.delete_document(file_path)


def get_document_public_url(file_path: str) -> Optional[str]:
    """Get public URL for a document."""
    return storage_client.get_public_url(file_path)