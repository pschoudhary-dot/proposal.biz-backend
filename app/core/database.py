"""
Database integration with Supabase for Proposal Biz application - Updated for new schema.
"""
import json
import uuid
from datetime import datetime as dt
from typing import List, Optional, Dict, Any
from supabase import create_client
from app.core.config import settings
from app.core.logging import logger

# Local cache for faster lookups and database fallback
local_job_cache = {}

# Initialize Supabase client
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
logger.info("Supabase client initialized successfully")

# Create a service role client for operations that need elevated permissions
supabase_admin = create_client(
    settings.SUPABASE_URL, 
    settings.SUPABASE_SERVICE_ROLE_KEY
) if hasattr(settings, 'SUPABASE_SERVICE_ROLE_KEY') else supabase
logger.info("Service role client initialized successfully")

# Table names for database operations (updated for new schema)
ORGANIZATIONS_TABLE = "organizations"
ORGANIZATION_USERS_TABLE = "organization_users"
CONTACTS_TABLE = "contacts"
ORG_CONTENT_SOURCES_TABLE = "org_content_sources"
ORG_CONTENT_LIBRARY_TABLE = "org_content_library"
CONTENT_CHUNKS_TABLE = "content_chunks"
PROCESSING_JOBS_TABLE = "processing_jobs"
EXTRACTION_CONTENT_TABLE = "extraction_content"
MARKDOWN_CONTENT_TABLE = "markdown_content"
EXTRACTED_LINKS_TABLE = "extracted_links"
DOCUMENT_CONTENT_TABLE = "document_content"
DOCUMENTS_TABLE = "documents"
CHAT_SESSIONS_TABLE = "chat_sessions"
CHAT_MESSAGES_TABLE = "chat_messages"
CONTENT_LIBRARY_RESULTS_TABLE = "content_library_results"

# Helper function to get current user's organization IDs
async def get_user_organizations(user_id: int) -> List[Dict[str, Any]]:
    """
    Get the list of organizations for the current user.
    
    Args:
        user_id: The user ID to check (integer)
        
    Returns:
        List of organization dictionaries with org_id, name, and role
    """
    try:
        response = supabase.table(ORGANIZATION_USERS_TABLE).select(
            "org_id, organizations!inner(name), role_id"
        ).eq("user_id", user_id).is_("deleted_at", None).execute()
        
        if response.data:
            return [
                {
                    "org_id": org["org_id"],
                    "org_name": org["organizations"]["name"],
                    "role_id": org["role_id"]
                }
                for org in response.data
            ]
        return []
    except Exception as e:
        logger.error(f"Error getting user organizations: {str(e)}")
        return []

# Helper function to get default organization ID for a user
async def get_default_org_id(user_id: int) -> Optional[int]:
    """
    Get the default organization ID for a user.
    If the user belongs to only one organization, return that.
    Otherwise, return the first organization in the list.
    
    Args:
        user_id: The user ID to check (integer)
        
    Returns:
        Default organization ID or None if user has no organizations
    """
    orgs = await get_user_organizations(user_id)
    return orgs[0]["org_id"] if orgs else None

# =============================================
# UNIFIED JOB PROCESSING FUNCTIONS
# =============================================

async def create_processing_job(
    org_id: int, 
    job_type: str, 
    user_id: Optional[int] = None,
    source_url: Optional[str] = None,
    source_files: Optional[List[str]] = None,
    source_ids: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Create a new processing job record.
    
    Args:
        org_id: Organization ID (integer)
        job_type: Type of job ('website_extraction', 'markdown_extraction', etc.)
        user_id: User ID who created the job
        source_url: Source URL for web-based jobs
        source_files: List of filenames for file-based jobs
        source_ids: List of source IDs for content library jobs
        metadata: Additional metadata
        
    Returns:
        The created job record
    """
    try:
        job_id = str(uuid.uuid4())
        
        job_record = {
            "org_id": org_id,
            "job_id": job_id,
            "job_type": job_type,
            "status": "pending",
            "total_items": 0,
            "completed_items": 0,
            "source_url": source_url,
            "source_files": source_files,
            "source_ids": source_ids,
            "metadata": metadata or {},
            "created_by": user_id
        }
        
        # Insert into database
        result = supabase.table(PROCESSING_JOBS_TABLE).insert(job_record).execute()
        
        if not result.data:
            logger.error(f"Failed to create processing job: {result}")
            return None
            
        # Update local cache
        local_job_cache[job_id] = result.data[0]
        return result.data[0]
        
    except Exception as e:
        logger.error(f"Error creating processing job: {str(e)}")
        return None

async def get_processing_job(job_id: str, org_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Get a processing job by its ID.
    
    Args:
        job_id: Job ID (UUID string)
        org_id: Optional organization ID for security check
        
    Returns:
        The job record or None if not found
    """
    # Try local cache first
    if job_id in local_job_cache:
        cached_job = local_job_cache[job_id]
        if org_id and cached_job.get("org_id") != org_id:
            return None
        return cached_job
        
    try:
        query = supabase.table(PROCESSING_JOBS_TABLE).select("*").eq("job_id", job_id)
        
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        
        if response.data:
            local_job_cache[job_id] = response.data[0]
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Database error when getting job {job_id}: {str(e)}")
        return None

async def update_processing_job_status(
    job_id: str, 
    status: str, 
    completed_items: Optional[int] = None,
    error_message: Optional[str] = None,
    org_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Update the status of a processing job.
    
    Args:
        job_id: Job ID (UUID string)
        status: New status
        completed_items: Number of completed items
        error_message: Error message if failed
        org_id: Optional organization ID for security check
        
    Returns:
        The updated record or None if failed
    """
    try:
        update_data = {
            "status": status,
            "updated_at": dt.now().isoformat()
        }
        
        if completed_items is not None:
            update_data["completed_items"] = completed_items
            
        if error_message:
            update_data["error_message"] = error_message
            
        query = supabase.table(PROCESSING_JOBS_TABLE).update(update_data).eq("job_id", job_id)
        
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        
        if response.data:
            # Update local cache
            if job_id in local_job_cache:
                local_job_cache[job_id].update(update_data)
            return response.data[0]
        return None
        
    except Exception as e:
        logger.error(f"Error updating job {job_id} status: {str(e)}")
        return None

async def update_processing_job_total_items(job_id: str, total_items: int, org_id: Optional[int] = None):
    """Update the total items count for a processing job."""
    try:
        update_data = {
            "total_items": total_items,
            "updated_at": dt.now().isoformat()
        }
        
        query = supabase.table(PROCESSING_JOBS_TABLE).update(update_data).eq("job_id", job_id)
        
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        
        if job_id in local_job_cache:
            local_job_cache[job_id].update(update_data)
            
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating job {job_id} total items: {str(e)}")
        return None

# =============================================
# WEBSITE EXTRACTION FUNCTIONS
# =============================================

async def create_extraction_job(hyperbrowser_job_id: str, url: str, org_id: int, user_id: Optional[int] = None):
    """
    Create a new website extraction job.
    
    Args:
        hyperbrowser_job_id: The Hyperbrowser job ID
        url: The URL being extracted
        org_id: Organization ID (integer)
        user_id: User ID who created the job
        
    Returns:
        The created job record
    """
    # Create processing job
    job_record = await create_processing_job(
        org_id=org_id,
        job_type="website_extraction",
        user_id=user_id,
        source_url=url,
        metadata={"hyperbrowser_job_id": hyperbrowser_job_id}
    )
    
    if not job_record:
        return None
    
    job_id = job_record["job_id"]
    
    try:
        # Create extraction content record
        extraction_record = {
            "org_id": org_id,
            "job_id": job_id,
            "url": url,
            "status": "pending"
        }
        
        supabase.table(EXTRACTION_CONTENT_TABLE).insert(extraction_record).execute()
        logger.info(f"Created extraction content record for job {job_id}")
        
        return job_record
        
    except Exception as e:
        logger.error(f"Error creating extraction content record: {str(e)}")
        return job_record

async def get_extraction_job(hyperbrowser_job_id: str, org_id: Optional[int] = None):
    """
    Get an extraction job by Hyperbrowser job ID.
    
    Args:
        hyperbrowser_job_id: Hyperbrowser job ID
        org_id: Optional organization ID for security check
        
    Returns:
        The job record or None if not found
    """
    try:
        # Find the processing job by hyperbrowser job ID in metadata
        query = supabase.table(PROCESSING_JOBS_TABLE).select("*").eq("job_type", "website_extraction")
        
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        
        if response.data:
            for job in response.data:
                metadata = job.get("metadata", {})
                if metadata.get("hyperbrowser_job_id") == hyperbrowser_job_id:
                    return job
        return None
    except Exception as e:
        logger.error(f"Error getting extraction job: {str(e)}")
        return None

async def update_extraction_job_status(hyperbrowser_job_id: str, status: str, extraction_data=None, org_id: Optional[int] = None):
    """
    Update the status of an extraction job and store extraction data.
    
    Args:
        hyperbrowser_job_id: Hyperbrowser job ID
        status: New status
        extraction_data: Optional extraction data
        org_id: Optional organization ID for security check
        
    Returns:
        The updated record or None if failed
    """
    try:
        # First find the job
        job = await get_extraction_job(hyperbrowser_job_id, org_id)
        if not job:
            logger.error(f"Job not found for hyperbrowser job ID: {hyperbrowser_job_id}")
            return None
            
        job_id = job["job_id"]
        
        # Update processing job status
        await update_processing_job_status(job_id, status, org_id=org_id)
        
        # Update extraction content
        update_data = {
            "status": status,
            "updated_at": dt.now().isoformat()
        }
        
        if extraction_data:
            update_data["extraction_data"] = extraction_data
            
        query = supabase.table(EXTRACTION_CONTENT_TABLE).update(update_data).eq("job_id", job_id)
        
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        
        # Process images if job completed successfully
        if status == "completed" and extraction_data:
            try:
                from app.utils.logo_downloader import process_website_images
                await process_website_images(extraction_data.get("logo", {}).get("url"), job_id, org_id)
            except Exception as e:
                logger.error(f"Error processing images for job {job_id}: {str(e)}")
        
        return response.data[0] if response.data else None
        
    except Exception as e:
        logger.error(f"Error updating extraction job status: {str(e)}")
        return None

async def store_extraction_content(hyperbrowser_job_id: str, extraction_data: dict, org_id: int, user_id: int = None):
    """Store complete extraction data in OrgContentSources."""
    try:
        job = await get_extraction_job(hyperbrowser_job_id, org_id)
        if not job:
            return None
            
        job_id = job["job_id"]
        
        content_record = {
            "org_id": org_id,
            "name": extraction_data.get("company", {}).get("name", "Website Extraction"),
            "source_type": "url",
            "source_metadata": {"extraction_date": dt.now().isoformat()},
            "parsed_content": json.dumps(extraction_data),
            "job_id": job_id,
            "status": "completed",
            "created_by": user_id
        }
        
        return supabase.table(ORG_CONTENT_SOURCES_TABLE).insert(content_record).execute()
    except Exception as e:
        logger.error(f"Error storing extraction content: {str(e)}")
        return None

async def update_extraction_job_color_palette(job_id: str, image_source: str, colors: List[List[int]], org_id: int):
    """
    Update an extraction job with color palette data.
    
    Args:
        job_id: The unique job identifier (UUID string)
        image_source: The image URL or path that was processed
        colors: The extracted RGB colors
        org_id: Organization ID (integer)
    """
    logger.info(f"Saving color palette for job_id {job_id}")
    
    try:
        # Check if there's an existing extraction content record
        response = supabase.table(EXTRACTION_CONTENT_TABLE).select("id").eq("job_id", job_id).eq("org_id", org_id).execute()
        
        if response.data:
            # Update existing record
            supabase.table(EXTRACTION_CONTENT_TABLE).update({
                "color_palette": colors,
                "updated_at": dt.now().isoformat()
            }).eq("job_id", job_id).eq("org_id", org_id).execute()
        else:
            # Create a new processing job for color extraction
            color_job = await create_processing_job(
                org_id=org_id,
                job_type="color_extraction",
                source_url=image_source,
                metadata={"color_extraction": True}
            )
            
            if color_job:
                # Create extraction content record
                supabase.table(EXTRACTION_CONTENT_TABLE).insert({
                    "org_id": org_id,
                    "job_id": color_job["job_id"],
                    "url": image_source,
                    "color_palette": colors,
                    "status": "completed"
                }).execute()
        
        logger.info(f"Color palette saved successfully for job_id {job_id}")
        
    except Exception as e:
        logger.error(f"Error saving color palette for job_id {job_id}: {str(e)}")

# =============================================
# MARKDOWN EXTRACTION FUNCTIONS
# =============================================

async def create_markdown_extraction_job(job_id: str, urls: List[str], org_id: int, user_id: Optional[int] = None):
    """
    Create a new markdown extraction job.
    
    Args:
        job_id: Hyperbrowser job ID
        urls: List of URLs to extract markdown from
        org_id: Organization ID (integer)
        user_id: User ID who created the job
        
    Returns:
        The created job record
    """
    # Create processing job
    job_record = await create_processing_job(
        org_id=org_id,
        job_type="markdown_extraction",
        user_id=user_id,
        metadata={"hyperbrowser_job_id": job_id}
    )
    
    if not job_record:
        return None
    
    processing_job_id = job_record["job_id"]
    
    try:
        # Update total items
        await update_processing_job_total_items(processing_job_id, len(urls), org_id)
        
        # Create markdown content records for each URL
        url_records = [{
            "org_id": org_id,
            "job_id": processing_job_id,
            "url": url,
            "status": "pending"
        } for url in urls]
        
        if url_records:
            supabase.table(MARKDOWN_CONTENT_TABLE).insert(url_records).execute()
            logger.info(f"Created {len(url_records)} URL records for job_id: {processing_job_id}")
        
        return job_record
        
    except Exception as e:
        logger.error(f"Error creating markdown extraction job: {str(e)}")
        return job_record

async def get_markdown_extraction_job(hyperbrowser_job_id: str, org_id: Optional[int] = None):
    """
    Get a markdown extraction job by Hyperbrowser job ID.
    """
    try:
        query = supabase.table(PROCESSING_JOBS_TABLE).select("*").eq("job_type", "markdown_extraction")
        
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        
        if response.data:
            for job in response.data:
                metadata = job.get("metadata", {})
                if metadata.get("hyperbrowser_job_id") == hyperbrowser_job_id:
                    return job
        return None
    except Exception as e:
        logger.error(f"Error getting markdown extraction job: {str(e)}")
        return None

async def update_markdown_extraction_status(hyperbrowser_job_id: str, status: str, org_id: Optional[int] = None):
    """Update the status of a markdown extraction job."""
    try:
        job = await get_markdown_extraction_job(hyperbrowser_job_id, org_id)
        if not job:
            return None
            
        return await update_processing_job_status(job["job_id"], status, org_id=org_id)
    except Exception as e:
        logger.error(f"Error updating markdown job status: {str(e)}")
        return None

async def update_url_markdown_content(
    hyperbrowser_job_id: str, 
    url: str, 
    markdown_text: str, 
    status: str = "completed", 
    metadata=None, 
    links=None, 
    html=None, 
    screenshot=None, 
    org_id: Optional[int] = None
):
    """Update a URL record with extracted markdown content."""
    try:
        job = await get_markdown_extraction_job(hyperbrowser_job_id, org_id)
        if not job:
            return None
            
        job_id = job["job_id"]
        
        # Update markdown content
        update_data = {
            "markdown_text": markdown_text,
            "status": status,
            "updated_at": dt.now().isoformat()
        }
        
        if html:
            update_data["html"] = html
        if screenshot:
            update_data["screenshot"] = screenshot
        if metadata:
            update_data["metadata"] = metadata
        
        query = supabase.table(MARKDOWN_CONTENT_TABLE).update(update_data).eq("job_id", job_id).eq("url", url)
        
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        
        # Save links if provided
        if links and isinstance(links, list):
            link_records = [{
                "org_id": org_id,
                "job_id": job_id,
                "url": url,
                "link": link
            } for link in links if link]
            
            if link_records:
                supabase.table(EXTRACTED_LINKS_TABLE).insert(link_records).execute()
        
        # Update job completed count
        completed_items = job.get("completed_items", 0) + 1
        total_items = job.get("total_items", 1)
        
        if completed_items >= total_items:
            await update_processing_job_status(job_id, "completed", completed_items, org_id=org_id)
        else:
            await update_processing_job_status(job_id, "processing", completed_items, org_id=org_id)
        
        return response.data[0] if response.data else None
        
    except Exception as e:
        logger.error(f"Error updating markdown content: {str(e)}")
        return None

async def get_markdown_content(hyperbrowser_job_id: str, org_id: Optional[int] = None):
    """Get all markdown content for a job."""
    try:
        job = await get_markdown_extraction_job(hyperbrowser_job_id, org_id)
        if not job:
            return None
        
        job_id = job["job_id"]
        
        # Get content
        content_query = supabase.table(MARKDOWN_CONTENT_TABLE).select("*").eq("job_id", job_id)
        if org_id:
            content_query = content_query.eq("org_id", org_id)
        content_response = content_query.execute()
        
        # Get links
        links_query = supabase.table(EXTRACTED_LINKS_TABLE).select("*").eq("job_id", job_id)
        if org_id:
            links_query = links_query.eq("org_id", org_id)
        links_response = links_query.execute()
        
        # Organize links by URL
        url_links = {}
        for link_record in links_response.data or []:
            url = link_record.get("url")
            link = link_record.get("link")
            if url and link:
                if url not in url_links:
                    url_links[url] = []
                url_links[url].append(link)
        
        # Add links to content records
        content_data = content_response.data or []
        for content in content_data:
            url = content.get("url")
            if url and url in url_links:
                content["links"] = url_links[url]
        
        return {
            "job": job,
            "content": content_data
        }
    except Exception as e:
        logger.error(f"Error getting markdown content: {str(e)}")
        return None

# =============================================
# DOCUMENT CONVERSION FUNCTIONS
# =============================================

async def create_document_conversion_job(job_id: str, org_id: int, user_id: Optional[int] = None):
    """Create a new document conversion job."""
    return await create_processing_job(
        org_id=org_id,
        job_type="document_conversion",
        user_id=user_id,
        metadata={"original_job_id": job_id}
    )

async def get_document_conversion_job(job_id: str, org_id: Optional[int] = None):
    """Get a document conversion job."""
    return await get_processing_job(job_id, org_id)

async def update_document_conversion_status(job_id: str, status: str, org_id: Optional[int] = None):
    """Update document conversion job status."""
    return await update_processing_job_status(job_id, status, org_id=org_id)

async def update_document_file_count(job_id: str, total_files: int, org_id: Optional[int] = None):
    """Update total file count for document conversion job."""
    return await update_processing_job_total_items(job_id, total_files, org_id)

async def create_document_content_record(job_id: str, filename: str, org_id: Optional[int] = None):
    """Create a document content record."""
    try:
        if not org_id:
            job = await get_document_conversion_job(job_id)
            if job:
                org_id = job.get("org_id")
        
        content_record = {
            "org_id": org_id,
            "job_id": job_id,
            "filename": filename,
            "status": "pending"
        }
        
        response = supabase.table(DOCUMENT_CONTENT_TABLE).insert(content_record).execute()
        return response.data[0] if response.data else content_record
    except Exception as e:
        logger.error(f"Error creating document content record: {str(e)}")
        return None

async def update_document_content(
    job_id: str, 
    filename: str, 
    markdown_text: str, 
    status: str = "completed", 
    metadata=None, 
    org_id: Optional[int] = None
):
    """Update document content with extracted markdown."""
    try:
        update_data = {
            "markdown_text": markdown_text,
            "status": status,
            "updated_at": dt.now().isoformat(),
            "metadata": metadata or {}
        }
        
        query = supabase.table(DOCUMENT_CONTENT_TABLE).update(update_data).eq("job_id", job_id).eq("filename", filename)
        
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        
        # Update job completed count
        job = await get_document_conversion_job(job_id, org_id)
        if job:
            completed_files = job.get("completed_items", 0) + 1
            total_files = job.get("total_items", 0)
            
            if completed_files >= total_files:
                await update_processing_job_status(job_id, "completed", completed_files, org_id=org_id)
            else:
                await update_processing_job_status(job_id, "processing", completed_files, org_id=org_id)
        
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating document content: {str(e)}")
        return None

async def get_document_content(job_id: str, org_id: Optional[int] = None):
    """Get all document content for a job."""
    try:
        job = await get_document_conversion_job(job_id, org_id)
        if not job:
            return None
        
        content_query = supabase.table(DOCUMENT_CONTENT_TABLE).select("*").eq("job_id", job_id)
        if org_id:
            content_query = content_query.eq("org_id", org_id)
            
        content_response = content_query.execute()
        
        return {
            "job": job,
            "content": content_response.data or []
        }
    except Exception as e:
        logger.error(f"Error getting document content: {str(e)}")
        return None

# =============================================
# CONTENT MANAGEMENT FUNCTIONS  
# =============================================

async def create_document_record(job_id: str, filename: str, org_id: int, user_id: int, 
                               document_type: str = "uploaded_file") -> Optional[str]:
    """Create a document record."""
    try:
        document_record = {
            "org_id": org_id,
            "document_type": document_type,
            "title": filename,
            "content": {"job_id": job_id, "filename": filename, "status": "processing"},
            "status": "processing",
            "created_by": user_id,
            "updated_by": user_id
        }
        
        response = supabase.table(DOCUMENTS_TABLE).insert(document_record).execute()
        if response.data:
            return str(response.data[0]["id"])
        return None
    except Exception as e:
        logger.error(f"Error creating document record: {str(e)}")
        return None

async def create_org_content_source_record(job_id: str, filename: str, org_id: int, 
                                         user_id: int, document_id: Optional[str] = None) -> Optional[str]:
    """Create an org content source record."""
    try:
        content_source_record = {
            "org_id": org_id,
            "name": filename,
            "source_type": "file",
            "source_metadata": {
                "job_id": job_id,
                "filename": filename,
                "document_id": document_id,
                "upload_date": dt.now().isoformat()
            },
            "job_id": job_id,
            "status": "processing",
            "created_by": user_id
        }
        
        response = supabase.table(ORG_CONTENT_SOURCES_TABLE).insert(content_source_record).execute()
        if response.data:
            return str(response.data[0]["id"])
        return None
    except Exception as e:
        logger.error(f"Error creating content source record: {str(e)}")
        return None

async def update_document_status(document_id: str, status: str, content: dict = None):
    """Update document status and content."""
    try:
        update_data = {
            "status": status,
            "updated_at": dt.now().isoformat()
        }
        
        if content is not None:
            update_data["content"] = content
        
        response = supabase.table(DOCUMENTS_TABLE).update(update_data).eq("id", document_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating document status: {str(e)}")
        return None

async def update_content_source_with_chunks(content_source_id: str, chunk_ids: List[str]) -> Optional[dict]:
    """Update a content source with chunk IDs."""
    try:
        update_data = {
            "status": "completed",
            "source_metadata": {
                "chunk_count": len(chunk_ids),
                "chunk_ids": chunk_ids,
                "chunks_created_at": dt.now().isoformat()
            },
            "updated_at": dt.now().isoformat()
        }
        
        response = supabase.table(ORG_CONTENT_SOURCES_TABLE).update(update_data).eq("id", content_source_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating content source with chunks: {str(e)}")
        return None

# =============================================
# ORGANIZATION MANAGEMENT FUNCTIONS
# =============================================

async def create_organization(name: str, user_id: int, domain: str, settings=None, logo=None, website=None, plan_id=None):
    """Create a new organization and add the user as an admin."""
    try:
        org_record = {
            "name": name,
            "domain": domain,
            "website": website,
            "logo": logo
        }
        
        response = supabase.table(ORGANIZATIONS_TABLE).insert(org_record).execute()
        
        if response.data:
            org_id = response.data[0]["id"]
            
            # Add user as admin (assuming role_id 1 is admin)
            user_record = {
                "org_id": org_id,
                "user_id": user_id,
                "role_id": 1  # Admin role
            }
            
            supabase.table(ORGANIZATION_USERS_TABLE).insert(user_record).execute()
            logger.info(f"Added user {user_id} as admin to organization {org_id}")
            
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error creating organization: {str(e)}")
        return None

async def get_organization(org_id: int, user_id: Optional[int] = None):
    """Get organization details."""
    try:
        if user_id:
            # Check if user belongs to organization
            user_query = supabase.table(ORGANIZATION_USERS_TABLE).select("*").eq("org_id", org_id).eq("user_id", user_id).is_("deleted_at", None).execute()
            if not user_query.data:
                return None
        
        response = supabase.table(ORGANIZATIONS_TABLE).select("*").eq("id", org_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error getting organization: {str(e)}")
        return None