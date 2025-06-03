"""
Simple database integration with Supabase for Proposal Biz application.
"""
import json
from datetime import datetime as dt
from typing import List, Optional
from supabase import create_client
from app.core.config import settings
from app.core.logging import logger
from app.utils.logo_downloader import process_website_images

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

# Table names for database operations
ORGANIZATIONS_TABLE = "organizations"
ORG_USERS_TABLE = "orgusers"
ORG_CONTACTS_TABLE = "orgcontacts"
ORG_CONTENT_SOURCES_TABLE = "orgcontentsources"
ORG_CONTENT_LIBRARY_TABLE = "orgcontentlibrary"
CONTENT_CHUNKS_TABLE = "contentchunks"
EXTRACTION_JOBS_TABLE = "extractionjobs"
MARKDOWN_JOBS_TABLE = "markdownextractionjobs"
MARKDOWN_CONTENT_TABLE = "markdowncontent"
EXTRACTED_LINKS_TABLE = "extractedlinks"
DOCUMENT_JOBS_TABLE = "documentconversionjobs"
DOCUMENT_CONTENT_TABLE = "documentcontent"
DOCUMENTS_TABLE = "documents"
CHAT_SESSIONS_TABLE = "chatsessions"
CHAT_MESSAGES_TABLE = "chatmessages"

# Helper function to get current user's organization IDs
async def get_user_organizations(user_id: str) -> List[str]:
    """
    Get the list of organization IDs for the current user.
    
    Args:
        user_id: The user ID to check
        
    Returns:
        List of organization IDs the user belongs to
    """
    try:
        response = supabase.table(ORG_USERS_TABLE).select("org_id").eq("user_id", user_id).is_("deleted_at", None).execute()
        if response.data:
            return [org["org_id"] for org in response.data]
        return []
    except Exception as e:
        logger.error(f"Error getting user organizations: {str(e)}")
        return []

# Helper function to get default organization ID for a user
async def get_default_org_id(user_id: str) -> Optional[str]:
    """
    Get the default organization ID for a user.
    If the user belongs to only one organization, return that.
    Otherwise, return the first organization in the list.
    
    Args:
        user_id: The user ID to check
        
    Returns:
        Default organization ID or None if user has no organizations
    """
    orgs = await get_user_organizations(user_id)
    return orgs[0] if orgs else None

# Extraction jobs functions
async def create_extraction_job(job_id: str, url: str, org_id: str, user_id: Optional[str] = None):
    """
    Create a new extraction job record in the database.
    
    Args:
        job_id: Hyperbrowser job ID
        url: The URL being extracted
        org_id: Organization ID
        user_id: User ID who created the job
        
    Returns:
        The created record
    """
    # Create job record
    job_record = {
        "job_id": job_id,
        "url": url,
        "status": "pending",
        "org_id": org_id,
        "created_by": user_id
    }
    
    # Save to local cache
    local_job_cache[job_id] = job_record
    
    try:
        # Save to database
        response = supabase.table(EXTRACTION_JOBS_TABLE).insert(job_record).execute()
        logger.info(f"Created extraction job record for job_id: {job_id}")
        return response.data[0] if response.data else job_record
    except Exception as e:
        logger.error(f"Error creating extraction job: {str(e)}")
        # Return from cache if database fails
        logger.warning(f"Using local cache for job {job_id}")
        return job_record

async def get_extraction_job(job_id: str, org_id: Optional[str] = None):
    """
    Get an extraction job by its ID.
    
    Args:
        job_id: Hyperbrowser job ID
        org_id: Optional organization ID for security check
        
    Returns:
        The job record or None if not found
    """
    # Try local cache first (faster)
    if job_id in local_job_cache:
        cached_job = local_job_cache[job_id]
        # If org_id is provided, check that it matches
        if org_id and cached_job.get("org_id") != org_id:
            return None
        return cached_job
        
    try:
        # Try database lookup
        query = supabase.table(EXTRACTION_JOBS_TABLE).select("*").eq("job_id", job_id)
        
        # If org_id is provided, add it to the query for security
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        
        if response.data:
            # Update local cache with database data
            local_job_cache[job_id] = response.data[0]
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Database error when getting job {job_id}: {str(e)}")
        return None

async def update_extraction_job_status(job_id: str, status: str, extraction_data=None, org_id: Optional[str] = None):
    """
    Update the status of an extraction job and process images if complete.
    
    Args:
        job_id: Hyperbrowser job ID
        status: New status (pending, running, completed, failed)
        extraction_data: Optional data from completed extraction
        org_id: Optional organization ID for security check
        
    Returns:
        The updated record or None if failed
    """
    # Start with basic status update
    update_data = {"status": status}
    
    # If job is completed and we have data, process images
    if status == "completed" and extraction_data:
        try:
            # Process and store logo and favicon images
            image_data = await process_website_images(supabase, extraction_data, job_id)
            
            # Add image paths and color data to update
            if image_data.get("logo_file_path"):
                update_data["logo_file_path"] = image_data["logo_file_path"]
            
            if image_data.get("favicon_file_path"):
                update_data["favicon_file_path"] = image_data["favicon_file_path"]
            
            if image_data.get("color_palette") is not None:
                update_data["color_palette"] = image_data["color_palette"]
        except Exception as e:
            logger.error(f"Error processing images: {str(e)}")
    
    # Update local cache
    if job_id in local_job_cache:
        local_job_cache[job_id].update(update_data)
    
    try:
        # Update database
        query = supabase.table(EXTRACTION_JOBS_TABLE).update(update_data).eq("job_id", job_id)
        
        # If org_id is provided, add it to the query for security
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        logger.info(f"Updated extraction job {job_id} status to {status}")
        return response.data[0] if response.data else local_job_cache.get(job_id)
    except Exception as e:
        logger.error(f"Database update failed: {str(e)}")
        logger.warning(f"Using local cache for job {job_id}")
        return local_job_cache.get(job_id)

async def store_extraction_content(job_id: str, extraction_data: dict, org_id: str, user_id: str = None):
    """Store complete extraction data in OrgContentSources."""
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
    
    # Store in database
    return await supabase.table(ORG_CONTENT_SOURCES_TABLE).insert(content_record).execute()

async def update_extraction_job_color_palette(job_id: str, image_source: str, colors: List[List[int]], org_id: str):
    """
    Update an extraction job with color palette data.
    
    Args:
        job_id: The unique job identifier
        image_source: The image URL or path that was processed
        colors: The extracted RGB colors
        org_id: Organization ID
    """
    logger.info(f"Saving color palette for job_id {job_id}")
    
    try:
        # Check if job exists
        response = supabase.table(EXTRACTION_JOBS_TABLE).select("job_id").eq("job_id", job_id).eq("org_id", org_id).execute()
        
        if not response.data:
            # Create a new job record
            logger.info(f"Creating new extraction job record for {job_id}")
            supabase.table(EXTRACTION_JOBS_TABLE).insert({
                "job_id": job_id,
                "org_id": org_id,
                "url": image_source,
                "color_palette": colors,
                "status": "completed",
                "created_at": dt.now().isoformat()
            }).execute()
        else:
            # Update existing job
            logger.info(f"Updating existing extraction job record {job_id}")
            supabase.table(EXTRACTION_JOBS_TABLE).update({
                "color_palette": colors,
                "updated_at": dt.now().isoformat()
            }).eq("job_id", job_id).eq("org_id", org_id).execute()
        
        logger.info(f"Color palette saved successfully for job_id {job_id}")
        
    except Exception as e:
        logger.error(f"Error saving color palette for job_id {job_id}: {str(e)}")


# Markdown extraction database functions
async def create_markdown_extraction_job(job_id: str, urls: List[str], org_id: str, user_id: Optional[str] = None):
    """
    Create a new markdown extraction job record in the database.
    
    Args:
        job_id: Hyperbrowser job ID
        urls: List of URLs to extract markdown from
        org_id: Organization ID
        user_id: User ID who created the job
        
    Returns:
        The created record
    """
    # Create job record
    job_record = {
        "job_id": job_id,
        "status": "pending",
        "total_urls": len(urls),
        "completed_urls": 0,
        "org_id": org_id,
        "created_by": user_id
    }
    
    try:
        # Save to database
        response = supabase.table(MARKDOWN_JOBS_TABLE).insert(job_record).execute()
        logger.info(f"Created markdown extraction job record for job_id: {job_id}")
        
        # Create records for each URL
        url_records = [{
            "job_id": job_id,
            "url": url,
            "status": "pending",
            "org_id": org_id
        } for url in urls]
        
        # Save URL records to database
        if url_records:
            supabase.table(MARKDOWN_CONTENT_TABLE).insert(url_records).execute()
            logger.info(f"Created {len(url_records)} URL records for job_id: {job_id}")
        
        return response.data[0] if response.data else job_record
    except Exception as e:
        logger.error(f"Error creating markdown extraction job: {str(e)}")
        return job_record

async def get_markdown_extraction_job(job_id: str, org_id: Optional[str] = None):
    """
    Get a markdown extraction job by its ID.
    
    Args:
        job_id: Hyperbrowser job ID
        org_id: Optional organization ID for security check
        
    Returns:
        The job record or None if not found
    """
    try:
        # Try database lookup
        query = supabase.table(MARKDOWN_JOBS_TABLE).select("*").eq("job_id", job_id)
        
        # If org_id is provided, add it to the query for security
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Database error when getting markdown job {job_id}: {str(e)}")
        return None

async def update_markdown_extraction_status(job_id: str, status: str, org_id: Optional[str] = None):
    """
    Update the status of a markdown extraction job.
    
    Args:
        job_id: Hyperbrowser job ID
        status: New status (pending, running, completed, failed)
        org_id: Optional organization ID for security check
        
    Returns:
        The updated record or None if failed
    """
    # Start with basic status update
    update_data = {
        "status": status,
        "updated_at": dt.now().isoformat()
    }
    
    try:
        # Update database
        query = supabase.table(MARKDOWN_JOBS_TABLE).update(update_data).eq("job_id", job_id)
        
        # If org_id is provided, add it to the query for security
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        logger.info(f"Updated markdown extraction job {job_id} status to {status}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating markdown job status: {str(e)}")
        return None

async def update_url_markdown_content(job_id: str, url: str, markdown_text: str, status: str = "completed", 
                                     metadata=None, links=None, html=None, screenshot=None, org_id: Optional[str] = None):
    """
    Update a URL record with extracted markdown content.
    
    Args:
        job_id: Hyperbrowser job ID
        url: The URL that was processed
        markdown_text: The extracted markdown content
        status: Status of this URL extraction (completed, failed)
        metadata: Optional metadata about the page
        links: Optional list of links found on the page
        html: Optional HTML content
        screenshot: Optional screenshot data
        org_id: Optional organization ID for security check
        
    Returns:
        The updated record or None if failed
    """
    # Update data for the URL record
    update_data = {
        "markdown_text": markdown_text,
        "status": status,
        "updated_at": dt.now().isoformat()
    }
    
    # Add optional fields if provided
    if html:
        update_data["html"] = html
    if screenshot:
        update_data["screenshot"] = screenshot
    if metadata:
        update_data["metadata"] = metadata
    
    try:
        # Update URL record
        query = supabase.table(MARKDOWN_CONTENT_TABLE).update(update_data).eq("job_id", job_id).eq("url", url)
        
        # If org_id is provided, add it to the query for security
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        logger.info(f"Updated markdown content for URL {url} in job {job_id}")
        
        # If we have links, save them
        if links and isinstance(links, list):
            link_records = [{
                "job_id": job_id,
                "url": url,
                "link": link,
                "org_id": org_id if org_id else response.data[0].get("org_id") if response.data else None
            } for link in links if link]
            
            if link_records:
                supabase.table(EXTRACTED_LINKS_TABLE).insert(link_records).execute()
                logger.info(f"Saved {len(link_records)} links for URL {url} in job {job_id}")
        
        # Update the job's completed_urls count
        job = await get_markdown_extraction_job(job_id, org_id)
        if job:
            completed_count = job.get("completed_urls", 0) + 1
            total_count = job.get("total_urls", 1)
            
            # Update job record with new completed count
            job_update = {"completed_urls": completed_count}
            
            # If all URLs are completed, update job status
            if completed_count >= total_count:
                job_update["status"] = "completed"
            
            query = supabase.table(MARKDOWN_JOBS_TABLE).update(job_update).eq("job_id", job_id)
            
            # If org_id is provided, add it to the query for security
            if org_id:
                query = query.eq("org_id", org_id)
                
            query.execute()
        
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating markdown content: {str(e)}")
        return None

async def get_markdown_content(job_id: str, org_id: Optional[str] = None):
    """
    Get all markdown content for a job.
    
    Args:
        job_id: Hyperbrowser job ID
        org_id: Optional organization ID for security check
        
    Returns:
        List of markdown content records
    """
    try:
        # Get job record
        job = await get_markdown_extraction_job(job_id, org_id)
        if not job:
            return None
        
        # Get all URL records for this job
        content_query = supabase.table(MARKDOWN_CONTENT_TABLE).select("*").eq("job_id", job_id)
        
        # If org_id is provided, add it to the query for security
        if org_id:
            content_query = content_query.eq("org_id", org_id)
            
        content_response = content_query.execute()
        content_data = content_response.data if content_response.data else []
        
        # Get all links for this job
        links_query = supabase.table(EXTRACTED_LINKS_TABLE).select("*").eq("job_id", job_id)
        
        # If org_id is provided, add it to the query for security
        if org_id:
            links_query = links_query.eq("org_id", org_id)
            
        links_response = links_query.execute()
        links_data = links_response.data if links_response.data else []
        
        # Organize links by URL
        url_links = {}
        for link_record in links_data:
            url = link_record.get("url")
            link = link_record.get("link")
            if url and link:
                if url not in url_links:
                    url_links[url] = []
                url_links[url].append(link)
        
        # Add links to content records
        for content in content_data:
            url = content.get("url")
            if url and url in url_links:
                content["links"] = url_links[url]
        
        return {
            "job": job,
            "content": content_data
        }
    except Exception as e:
        logger.error(f"Error getting markdown content for job {job_id}: {str(e)}")
        return None


# Document to Markdown conversion database functions
async def create_document_conversion_job(job_id: str, org_id: str, user_id: Optional[str] = None):
    """
    Create a new document conversion job record in the database.
    
    Args:
        job_id: Unique job ID
        org_id: Organization ID
        user_id: User ID who created the job
        
    Returns:
        The created record
    """
    # Create job record
    job_record = {
        "job_id": job_id,
        "status": "pending",
        "total_files": 0,
        "completed_files": 0,
        "org_id": org_id,
        "created_by": user_id
    }
    
    try:
        # Save to database
        response = supabase.table(DOCUMENT_JOBS_TABLE).insert(job_record).execute()
        logger.info(f"Created document conversion job record for job_id: {job_id}")
        
        return response.data[0] if response.data else job_record
    except Exception as e:
        logger.error(f"Error creating document conversion job: {str(e)}")
        return job_record

async def get_document_conversion_job(job_id: str, org_id: Optional[str] = None):
    """
    Get a document conversion job by its ID.
    
    Args:
        job_id: Unique job ID
        org_id: Optional organization ID for security check
        
    Returns:
        The job record or None if not found
    """
    try:
        # Try database lookup
        query = supabase.table(DOCUMENT_JOBS_TABLE).select("*").eq("job_id", job_id)
        
        # If org_id is provided, add it to the query for security
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Database error when getting document job {job_id}: {str(e)}")
        return None

async def update_document_conversion_status(job_id: str, status: str, org_id: Optional[str] = None):
    """
    Update the status of a document conversion job.
    
    Args:
        job_id: Unique job ID
        status: New status (pending, running, completed, failed)
        org_id: Optional organization ID for security check
        
    Returns:
        The updated record or None if failed
    """
    # Start with basic status update
    update_data = {
        "status": status,
        "updated_at": dt.now().isoformat()
    }
    
    try:
        # Update database
        query = supabase.table(DOCUMENT_JOBS_TABLE).update(update_data).eq("job_id", job_id)
        
        # If org_id is provided, add it to the query for security
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        logger.info(f"Updated document conversion job {job_id} status to {status}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating document job status: {str(e)}")
        return None

async def update_document_file_count(job_id: str, total_files: int, org_id: Optional[str] = None):
    """
    Update the total file count for a document conversion job.
    
    Args:
        job_id: Unique job ID
        total_files: Total number of files to process
        org_id: Optional organization ID for security check
        
    Returns:
        The updated record or None if failed
    """
    update_data = {
        "total_files": total_files,
        "updated_at": dt.now().isoformat()
    }
    
    try:
        # Update database
        query = supabase.table(DOCUMENT_JOBS_TABLE).update(update_data).eq("job_id", job_id)
        
        # If org_id is provided, add it to the query for security
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        logger.info(f"Updated document conversion job {job_id} with {total_files} total files")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating document job file count: {str(e)}")
        return None

async def create_document_content_record(job_id: str, filename: str, org_id: Optional[str] = None):
    """
    Create a document content record for a file.
    
    Args:
        job_id: Unique job ID
        filename: Name of the file to process
        org_id: Optional organization ID
        
    Returns:
        The created record or None if failed
    """
    # Get org_id from job if not provided
    if not org_id:
        job = await get_document_conversion_job(job_id)
        if job:
            org_id = job.get("org_id")
    
    content_record = {
        "job_id": job_id,
        "filename": filename,
        "status": "pending",
        "org_id": org_id
    }
    
    try:
        # Save to database
        response = supabase.table(DOCUMENT_CONTENT_TABLE).insert(content_record).execute()
        logger.info(f"Created document content record for file {filename} in job {job_id}")
        return response.data[0] if response.data else content_record
    except Exception as e:
        logger.error(f"Error creating document content record: {str(e)}")
        return None

async def update_document_content(job_id: str, filename: str, markdown_text: str, status: str = "completed", 
                                 metadata=None, org_id: Optional[str] = None):
    """
    Update a document content record with extracted markdown.
    
    Args:
        job_id: Unique job ID
        filename: Name of the file that was processed
        markdown_text: The extracted markdown content
        status: Status of this file conversion (completed, failed)
        metadata: Optional metadata about the document
        org_id: Optional organization ID for security check
        
    Returns:
        The updated record or None if failed
    """
    try:
        update_data = {
            "markdown_text": markdown_text,
            "status": status,
            "updated_at": dt.now().isoformat()
        }
        
        # Initialize metadata if not provided
        if not metadata:
            metadata = {}
            
        # Store error in metadata if status is failed and we have an error in metadata
        if status == "failed" and "error" in metadata:
            metadata["error"] = metadata["error"]
            
        update_data["metadata"] = metadata
            
        query = supabase.table(DOCUMENT_CONTENT_TABLE).update(update_data).eq("job_id", job_id).eq("filename", filename)
        
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        logger.info(f"Updated document content for file {filename} in job {job_id}")
        
        # Update associated document record if it exists
        try:
            # Find the document record associated with this file
            doc_query = supabase.table(DOCUMENTS_TABLE).select("id, content").eq("org_id", org_id)
            doc_response = doc_query.execute()
            
            if doc_response.data:
                for doc in doc_response.data:
                    doc_content = doc.get("content", {})
                    if (doc_content.get("job_id") == job_id and 
                        doc_content.get("filename") == filename):
                        # Update the document with the markdown content
                        updated_content = doc_content.copy()
                        updated_content.update({
                            "markdown_text": markdown_text,
                            "status": status,
                            "metadata": metadata,
                            "processed_at": dt.now().isoformat()
                        })
                        
                        await update_document_status(
                            doc["id"], 
                            "completed" if status == "completed" else "failed",
                            updated_content
                        )
                        logger.info(f"Updated document record for file {filename}")
                        break
        except Exception as e:
            logger.error(f"Error updating document record for file {filename}: {str(e)}")
            # Continue processing even if document update fails
        
        # Update content source status if it exists
        try:
            source_query = supabase.table(ORG_CONTENT_SOURCES_TABLE).select("id").eq("job_id", job_id)
            if org_id:
                source_query = source_query.eq("org_id", org_id)
            
            source_response = source_query.execute()
            if source_response.data:
                for source in source_response.data:
                    # Update content source with parsed content
                    source_update = {
                        "status": "completed" if status == "completed" else "failed",
                        "parsed_content": markdown_text if status == "completed" else None,
                        "status_metadata": {
                            "filename": filename,
                            "processing_completed_at": dt.now().isoformat(),
                            "error": metadata.get("error") if metadata and status == "failed" else None
                        },
                        "updated_at": dt.now().isoformat()
                    }
                    
                    supabase.table(ORG_CONTENT_SOURCES_TABLE).update(source_update).eq("id", source["id"]).execute()
                    logger.info(f"Updated content source for file {filename}")
        except Exception as e:
            logger.error(f"Error updating content source for file {filename}: {str(e)}")
            # Continue processing even if content source update fails
        
        # Update the job's completed_files count
        job = await get_document_conversion_job(job_id, org_id)
        if job:
            completed_files = job.get("completed_files", 0) + 1
            total_files = job.get("total_files", 0)
            
            # If all files are processed, update job status
            if completed_files >= total_files:
                await update_document_conversion_status(job_id, "completed", org_id)
            else:
                # Just update the completed files count
                await update_document_conversion_status(job_id, "processing", org_id, completed_files)
        
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating document content: {str(e)}")
        return None

async def get_document_content(job_id: str, org_id: Optional[str] = None):
    """
    Get all document content for a job.
    
    Args:
        job_id: Unique job ID
        org_id: Optional organization ID for security check
        
    Returns:
        Dictionary with job and content data
    """
    try:
        # Get job record
        job = await get_document_conversion_job(job_id, org_id)
        if not job:
            return None
        
        # Get all content records for this job
        content_query = supabase.table(DOCUMENT_CONTENT_TABLE).select("*").eq("job_id", job_id)
        
        # If org_id is provided, add it to the query for security
        if org_id:
            content_query = content_query.eq("org_id", org_id)
            
        content_response = content_query.execute()
        content_data = content_response.data if content_response.data else []
        
        return {
            "job": job,
            "content": content_data
        }
    except Exception as e:
        logger.error(f"Error getting document content for job {job_id}: {str(e)}")
        return None


async def create_document_record(job_id: str, filename: str, org_id: str, user_id: str, 
                               document_type: str = "uploaded_file") -> Optional[str]:
    """
    Create a document record in the documents table for an uploaded file.
    
    Args:
        job_id: Unique job ID
        filename: Name of the uploaded file
        org_id: Organization ID
        user_id: User ID who uploaded the file
        document_type: Type of document (default: "uploaded_file")
        
    Returns:
        Document ID if created successfully, None if failed
    """
    # Create document record
    document_record = {
        "org_id": org_id,
        "document_type": document_type,
        "title": filename,
        "content": {"job_id": job_id, "filename": filename, "status": "processing"},
        "status": "processing",
        "created_by": user_id,
        "updated_by": user_id
    }
    
    try:
        # Save to database
        response = supabase.table(DOCUMENTS_TABLE).insert(document_record).execute()
        if response.data:
            document_id = response.data[0]["id"]
            logger.info(f"Created document record {document_id} for file {filename} in job {job_id}")
            return str(document_id)
        return None
    except Exception as e:
        logger.error(f"Error creating document record: {str(e)}")
        return None


async def create_org_content_source_record(job_id: str, filename: str, org_id: str, 
                                         user_id: str, document_id: Optional[str] = None) -> Optional[str]:
    """
    Create an org content source record for an uploaded document.
    
    Args:
        job_id: Unique job ID
        filename: Name of the uploaded file
        org_id: Organization ID
        user_id: User ID who uploaded the file
        document_id: Optional document ID reference
        
    Returns:
        Content source ID if created successfully, None if failed
    """
    # Create content source record
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
        "created_by": user_id,
        "created_at": dt.now().isoformat(),
        "updated_at": dt.now().isoformat()
    }
    
    try:
        # Save to database
        response = supabase.table(ORG_CONTENT_SOURCES_TABLE).insert(content_source_record).execute()
        if response.data:
            content_source_id = response.data[0]["id"]
            logger.info(f"Created content source record {content_source_id} for file {filename} in job {job_id}")
            return str(content_source_id)
        return None
    except Exception as e:
        logger.error(f"Error creating content source record: {str(e)}")
        return None


async def update_document_status(document_id: str, status: str, content: dict = None):
    """
    Update document status and content.
    
    Args:
        document_id: ID of the document to update
        status: New status
        content: Optional content to update
        
    Returns:
        The updated document record or None if failed
    """
    update_data = {
        "status": status,
        "updated_at": dt.now().isoformat()
    }
    
    if content is not None:
        update_data["content"] = content
    
    try:
        response = supabase.table(DOCUMENTS_TABLE).update(update_data).eq("id", document_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating document {document_id} status: {str(e)}")
        return None


async def update_content_source_with_chunks(content_source_id: str, chunk_ids: List[str]) -> Optional[dict]:
    """
    Update a content source record with chunk IDs after processing.
    
    Args:
        content_source_id: ID of the content source
        chunk_ids: List of chunk IDs that were created
        
    Returns:
        The updated content source record or None if failed
    """
    try:
        # Update the content source with chunk information
        update_data = {
            "status": "completed",
            "status_metadata": {
                "chunk_count": len(chunk_ids),
                "chunk_ids": chunk_ids,
                "chunks_created_at": dt.now().isoformat()
            },
            "updated_at": dt.now().isoformat()
        }
        
        response = supabase.table(ORG_CONTENT_SOURCES_TABLE).update(update_data).eq("id", content_source_id).execute()
        logger.info(f"Updated content source {content_source_id} with {len(chunk_ids)} chunks")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating content source with chunks: {str(e)}")
        return None


# Organization management functions
async def create_organization(name: str, user_id: str, settings=None, logo=None, website=None, domain=None, plan_id=None):
    """
    Create a new organization and add the user as an admin.
    
    Args:
        name: Organization name
        user_id: User ID who is creating the organization
        settings: Optional organization settings
        logo: Optional logo URL
        website: Optional website URL
        domain: Optional domain
        plan_id: Optional plan ID
        
    Returns:
        The created organization record or None if failed
    """
    # Create organization record
    org_record = {
        "name": name,
        "settings": settings or {},
        "logo": logo,
        "website": website,
        "domain": domain,
        "plan_id": plan_id
    }
    
    try:
        # Save to database
        response = supabase.table(ORGANIZATIONS_TABLE).insert(org_record).execute()
        
        if response.data:
            org_id = response.data[0].get("id")
            logger.info(f"Created organization {name} with ID {org_id}")
            
            # Add user as admin
            user_record = {
                "org_id": org_id,
                "user_id": user_id,
                "role": "admin"
            }
            
            supabase.table(ORG_USERS_TABLE).insert(user_record).execute()
            logger.info(f"Added user {user_id} as admin to organization {org_id}")
            
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error creating organization: {str(e)}")
        return None

async def get_organization(org_id: str, user_id: Optional[str] = None):
    """
    Get organization details.
    
    Args:
        org_id: Organization ID
        user_id: Optional user ID for security check
        
    Returns:
        Organization record or None if not found
    """
    try:
        # If user_id is provided, check if user belongs to organization
        if user_id:
            user_query = supabase.table(ORG_USERS_TABLE).select("*").eq("org_id", org_id).eq("user_id", user_id).is_("deleted_at", None).execute()
            if not user_query.data:
                logger.warning(f"User {user_id} does not belong to organization {org_id}")
                return None
        
        # Get organization details
        response = supabase.table(ORGANIZATIONS_TABLE).select("*").eq("id", org_id).execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting organization {org_id}: {str(e)}")
        return None
