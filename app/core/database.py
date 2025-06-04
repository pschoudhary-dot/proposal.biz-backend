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
logger.info(f"Supabase client initialized successfully - URL: {settings.SUPABASE_URL}")

# Create a service role client for operations that need elevated permissions
supabase_admin = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
) if hasattr(settings, 'SUPABASE_SERVICE_ROLE_KEY') else supabase
logger.info("Service role client initialized successfully")

# Table names for database operations (Updated to match new schema)
ORGANIZATIONS_TABLE = "organizations"
ORG_USERS_TABLE = "organization_users"  # Updated from "orgusers"
ORG_CONTACTS_TABLE = "contacts"  # TODO: Update to "contacts" when needed
ORG_CONTENT_SOURCES_TABLE = "org_content_sources"  # Updated from "orgcontentsources"
ORG_CONTENT_LIBRARY_TABLE = "org_content_library"  # Updated from "orgcontentlibrary"
CONTENT_CHUNKS_TABLE = "content_chunks"  # Updated from "contentchunks"

# Unified job processing table (replaces separate job tables)
PROCESSING_JOBS_TABLE = "processing_jobs"

# Legacy job tables (will be migrated to processing_jobs)
EXTRACTION_JOBS_TABLE = "extractionjobs"  # LEGACY - use PROCESSING_JOBS_TABLE
MARKDOWN_JOBS_TABLE = "markdownextractionjobs"  # LEGACY - use PROCESSING_JOBS_TABLE
DOCUMENT_JOBS_TABLE = "documentconversionjobs"  # LEGACY - use PROCESSING_JOBS_TABLE

# Result tables (updated naming)
MARKDOWN_CONTENT_TABLE = "markdown_content"  # Updated from "markdowncontent"
EXTRACTED_LINKS_TABLE = "extracted_links"  # Updated from "extractedlinks"
DOCUMENT_CONTENT_TABLE = "document_content"  # Updated from "documentcontent"
DOCUMENTS_TABLE = "documents"

# New result tables for structured storage
EXTRACTION_CONTENT_TABLE = "extraction_content"  # NEW - for website extraction results
CONTENT_LIBRARY_RESULTS_TABLE = "content_library_results"  # NEW - for business data results

# Chat system tables (updated naming)
CHAT_SESSIONS_TABLE = "chat_sessions"  # Updated from "chatsessions"
CHAT_MESSAGES_TABLE = "chat_messages"  # Updated from "chatmessages"

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

# =============================================
# UNIFIED JOB PROCESSING SYSTEM
# =============================================

def _convert_org_id(org_id):
    """Helper function to convert org_id to integer, handling UUIDs and strings."""
    if org_id is None:
        return None

    # If it's already an integer, return it
    if isinstance(org_id, int):
        return org_id

    # Convert to string first
    org_id_str = str(org_id)

    # If it looks like a UUID, extract a numeric representation or use a hash
    if len(org_id_str) > 10 and '-' in org_id_str:
        # For UUIDs, we'll use a hash to get a consistent integer
        import hashlib
        return abs(hash(org_id_str)) % (10**9)  # Keep it within reasonable integer range

    # Try to convert directly to int
    try:
        return int(org_id_str)
    except ValueError:
        # If conversion fails, use hash
        import hashlib
        return abs(hash(org_id_str)) % (10**9)

async def create_processing_job(
    job_id: str,
    job_type: str,
    org_id: str,
    user_id: Optional[str] = None,
    source_url: Optional[str] = None,
    source_files: Optional[List[str]] = None,
    source_ids: Optional[List[str]] = None,
    total_items: int = 0,
    metadata: Optional[dict] = None
) -> Optional[dict]:
    """
    Create a new processing job in the unified job system.

    Args:
        job_id: Unique job identifier
        job_type: Type of job ('website_extraction', 'markdown_extraction', 'document_conversion', 'content_library', 'vector_processing')
        org_id: Organization ID (string, UUID, or integer)
        user_id: User ID who created the job
        source_url: Source URL for web operations
        source_files: List of filenames for document operations
        source_ids: List of content source IDs for content library operations
        total_items: Total number of items to process
        metadata: Additional job-specific metadata

    Returns:
        The created job record or None if failed
    """
    job_record = {
        "job_id": job_id,
        "job_type": job_type,
        "org_id": _convert_org_id(org_id),
        "status": "pending",
        "total_items": total_items,
        "completed_items": 0,
        "created_by": int(user_id) if user_id and user_id.isdigit() else None,
        "metadata": metadata or {}
    }

    # Add type-specific fields
    if source_url:
        job_record["source_url"] = source_url
    if source_files:
        job_record["source_files"] = source_files
    if source_ids:
        job_record["source_ids"] = source_ids

    try:
        response = supabase.table(PROCESSING_JOBS_TABLE).insert(job_record).execute()
        logger.info(f"Created processing job {job_id} of type {job_type} for org {org_id}")
        return response.data[0] if response.data else job_record
    except Exception as e:
        # Enhanced error logging to capture detailed Supabase errors
        error_details = str(e)
        if hasattr(e, 'message'):
            error_details = f"Code: {getattr(e, 'code', 'N/A')}, Message: {e.message}, Details: {getattr(e, 'details', 'N/A')}"
        elif hasattr(e, 'args') and len(e.args) > 0:
            error_details = str(e.args[0])

        logger.error(f"Error creating processing job {job_id}: {error_details}", exc_info=True)
        return None

async def get_processing_job(job_id: str, org_id: Optional[str] = None) -> Optional[dict]:
    """
    Get a processing job by its ID.

    Args:
        job_id: Unique job identifier
        org_id: Optional organization ID for security check

    Returns:
        The job record or None if not found
    """
    try:
        query = supabase.table(PROCESSING_JOBS_TABLE).select("*").eq("job_id", job_id)

        if org_id:
            query = query.eq("org_id", _convert_org_id(org_id))

        response = query.execute()

        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        # Enhanced error logging to capture detailed Supabase errors
        error_details = str(e)
        if hasattr(e, 'message'):
            error_details = f"Code: {getattr(e, 'code', 'N/A')}, Message: {e.message}, Details: {getattr(e, 'details', 'N/A')}"
        elif hasattr(e, 'args') and len(e.args) > 0:
            error_details = str(e.args[0])

        logger.error(f"Error getting processing job {job_id}: {error_details}", exc_info=True)
        return None

async def update_processing_job(
    job_id: str,
    status: Optional[str] = None,
    completed_items: Optional[int] = None,
    error_message: Optional[str] = None,
    metadata: Optional[dict] = None,
    org_id: Optional[str] = None
) -> Optional[dict]:
    """
    Update a processing job.

    Args:
        job_id: Unique job identifier
        status: New status ('pending', 'processing', 'completed', 'failed')
        completed_items: Number of completed items
        error_message: Error message if job failed
        metadata: Updated metadata
        org_id: Optional organization ID for security check

    Returns:
        The updated job record or None if failed
    """
    update_data = {"updated_at": dt.now().isoformat()}

    if status is not None:
        update_data["status"] = status
    if completed_items is not None:
        update_data["completed_items"] = completed_items
    if error_message is not None:
        update_data["error_message"] = error_message
    if metadata is not None:
        update_data["metadata"] = metadata

    try:
        query = supabase.table(PROCESSING_JOBS_TABLE).update(update_data).eq("job_id", job_id)

        if org_id:
            query = query.eq("org_id", _convert_org_id(org_id))

        response = query.execute()
        logger.info(f"Updated processing job {job_id}")
        return response.data[0] if response.data else None
    except Exception as e:
        # Enhanced error logging to capture detailed Supabase errors
        error_details = str(e)
        if hasattr(e, 'message'):
            error_details = f"Code: {getattr(e, 'code', 'N/A')}, Message: {e.message}, Details: {getattr(e, 'details', 'N/A')}"
        elif hasattr(e, 'args') and len(e.args) > 0:
            error_details = str(e.args[0])

        logger.error(f"Error updating processing job {job_id}: {error_details}", exc_info=True)
        return None

# =============================================
# RESULT STORAGE FUNCTIONS
# =============================================

async def store_extraction_result(
    job_id: str,
    url: str,
    org_id: str,
    extraction_data: dict,
    status: str = "completed",
    logo_file_path: Optional[str] = None,
    favicon_file_path: Optional[str] = None,
    color_palette: Optional[dict] = None,
    error_message: Optional[str] = None
) -> Optional[dict]:
    """
    Store website extraction results in the extraction_content table.

    Args:
        job_id: Processing job ID
        url: Source URL
        org_id: Organization ID
        extraction_data: Complete extraction data (WebsiteExtraction schema)
        status: Result status
        logo_file_path: Path to stored logo file
        favicon_file_path: Path to stored favicon file
        color_palette: Extracted color palette
        error_message: Error message if extraction failed

    Returns:
        The created result record or None if failed
    """
    result_record = {
        "job_id": job_id,
        "url": url,
        "org_id": _convert_org_id(org_id),
        "status": status,
        "extraction_data": extraction_data,
        "logo_file_path": logo_file_path,
        "favicon_file_path": favicon_file_path,
        "color_palette": color_palette,
        "error_message": error_message
    }

    try:
        response = supabase.table(EXTRACTION_CONTENT_TABLE).insert(result_record).execute()
        logger.info(f"Stored extraction result for job {job_id}, URL: {url}")
        return response.data[0] if response.data else result_record
    except Exception as e:
        # Enhanced error logging to capture detailed Supabase errors
        error_details = str(e)
        if hasattr(e, 'message'):
            error_details = f"Code: {getattr(e, 'code', 'N/A')}, Message: {e.message}, Details: {getattr(e, 'details', 'N/A')}"
        elif hasattr(e, 'args') and len(e.args) > 0:
            error_details = str(e.args[0])

        logger.error(f"Error storing extraction result for job {job_id}: {error_details}", exc_info=True)
        return None

async def get_extraction_results(job_id: str, org_id: Optional[str] = None) -> Optional[List[dict]]:
    """
    Get extraction results for a job.

    Args:
        job_id: Processing job ID
        org_id: Optional organization ID for security check

    Returns:
        List of extraction result records or None if not found
    """
    try:
        query = supabase.table(EXTRACTION_CONTENT_TABLE).select("*").eq("job_id", job_id)

        if org_id:
            query = query.eq("org_id", _convert_org_id(org_id))

        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error getting extraction results for job {job_id}: {str(e)}")
        return None

async def store_content_library_result(
    job_id: str,
    org_id: str,
    business_data: dict,
    source_count: int = 0,
    processing_metadata: Optional[dict] = None
) -> Optional[dict]:
    """
    Store content library processing results.

    Args:
        job_id: Processing job ID
        org_id: Organization ID
        business_data: Complete BusinessInformationSchema data
        source_count: Number of sources processed
        processing_metadata: Processing statistics and metadata

    Returns:
        The created result record or None if failed
    """
    result_record = {
        "job_id": job_id,
        "org_id": _convert_org_id(org_id),
        "business_data": business_data,
        "source_count": source_count,
        "processing_metadata": processing_metadata or {}
    }

    try:
        response = supabase.table(CONTENT_LIBRARY_RESULTS_TABLE).insert(result_record).execute()
        logger.info(f"Stored content library result for job {job_id}")
        return response.data[0] if response.data else result_record
    except Exception as e:
        logger.error(f"Error storing content library result: {str(e)}")
        return None

async def get_content_library_results(job_id: str, org_id: Optional[str] = None) -> Optional[dict]:
    """
    Get content library results for a job.

    Args:
        job_id: Processing job ID
        org_id: Optional organization ID for security check

    Returns:
        Content library result record or None if not found
    """
    try:
        query = supabase.table(CONTENT_LIBRARY_RESULTS_TABLE).select("*").eq("job_id", job_id)

        if org_id:
            query = query.eq("org_id", _convert_org_id(org_id))

        response = query.execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error getting content library results for job {job_id}: {str(e)}")
        return None

# =============================================
# LEGACY JOB FUNCTIONS (for backward compatibility)
# =============================================

# Extraction jobs functions
async def create_extraction_job(job_id: str, url: str, org_id: str, user_id: Optional[str] = None):
    """
    Create a new extraction job record in the database.
    UPDATED: Now uses unified processing_jobs table.

    Args:
        job_id: Hyperbrowser job ID
        url: The URL being extracted
        org_id: Organization ID
        user_id: User ID who created the job

    Returns:
        The created record
    """
    # Use the new unified job processing system
    job_record = await create_processing_job(
        job_id=job_id,
        job_type="website_extraction",
        org_id=org_id,
        user_id=user_id,
        source_url=url,
        total_items=1,
        metadata={"url": url}
    )

    if job_record:
        # Save to local cache for backward compatibility
        local_job_cache[job_id] = {
            "job_id": job_id,
            "url": url,
            "status": job_record.get("status", "pending"),
            "org_id": org_id,
            "created_by": user_id
        }
        logger.info(f"Created extraction job record for job_id: {job_id}")
        return job_record
    else:
        # Fallback to cache if unified system fails
        fallback_record = {
            "job_id": job_id,
            "url": url,
            "status": "pending",
            "org_id": org_id,
            "created_by": user_id
        }
        local_job_cache[job_id] = fallback_record
        logger.warning(f"Using local cache for job {job_id}")
        return fallback_record

async def get_extraction_job(job_id: str, org_id: Optional[str] = None):
    """
    Get an extraction job by its ID.
    UPDATED: Now uses unified processing_jobs table with fallback to cache.

    Args:
        job_id: Hyperbrowser job ID
        org_id: Optional organization ID for security check

    Returns:
        The job record or None if not found
    """
    # Try unified processing jobs table first
    job_record = await get_processing_job(job_id, org_id)

    if job_record and job_record.get("job_type") == "website_extraction":
        # Convert to legacy format for backward compatibility
        legacy_format = {
            "job_id": job_record["job_id"],
            "url": job_record.get("source_url", ""),
            "status": job_record["status"],
            "org_id": job_record["org_id"],
            "created_by": job_record.get("created_by"),
            "created_at": job_record.get("created_at"),
            "updated_at": job_record.get("updated_at")
        }

        # Update local cache
        local_job_cache[job_id] = legacy_format
        return legacy_format

    # Fallback to local cache
    if job_id in local_job_cache:
        cached_job = local_job_cache[job_id]
        # If org_id is provided, check that it matches
        if org_id and str(cached_job.get("org_id")) != str(org_id):
            return None
        return cached_job

    # No job found
    return None

async def update_extraction_job_status(job_id: str, status: str, extraction_data=None, org_id: Optional[str] = None):
    """
    Update the status of an extraction job and process images if complete.
    UPDATED: Now uses unified processing_jobs table and stores results in extraction_content.

    Args:
        job_id: Hyperbrowser job ID
        status: New status (pending, processing, completed, failed)
        extraction_data: Optional data from completed extraction
        org_id: Optional organization ID for security check

    Returns:
        The updated record or None if failed
    """
    # Update the unified processing job
    completed_items = 1 if status == "completed" else 0
    error_message = None

    if status == "failed" and extraction_data and isinstance(extraction_data, dict):
        error_message = extraction_data.get("error", "Extraction failed")

    # Update processing job status
    job_record = await update_processing_job(
        job_id=job_id,
        status=status,
        completed_items=completed_items,
        error_message=error_message,
        org_id=org_id
    )

    # If job is completed and we have data, store the extraction results
    if status == "completed" and extraction_data and org_id:
        try:
            # Get the source URL from the job record
            job_info = await get_processing_job(job_id, org_id)
            source_url = job_info.get("source_url", "") if job_info else ""

            # Process and store logo and favicon images
            image_data = await process_website_images(supabase, extraction_data, job_id)

            # Store extraction results in the new extraction_content table
            await store_extraction_result(
                job_id=job_id,
                url=source_url,
                org_id=org_id,
                extraction_data=extraction_data,
                status="completed",
                logo_file_path=image_data.get("logo_file_path"),
                favicon_file_path=image_data.get("favicon_file_path"),
                color_palette=image_data.get("color_palette")
            )

            # Also store in org_content_sources for backward compatibility
            await store_extraction_content(job_id, extraction_data, org_id)

        except Exception as e:
            logger.error(f"Error processing extraction results: {str(e)}")

    # Update local cache for backward compatibility
    if job_id in local_job_cache:
        local_job_cache[job_id].update({
            "status": status,
            "updated_at": dt.now().isoformat()
        })

    # Return job record in legacy format
    if job_record:
        legacy_format = {
            "job_id": job_record["job_id"],
            "status": job_record["status"],
            "org_id": job_record["org_id"],
            "updated_at": job_record.get("updated_at")
        }
        return legacy_format
    else:
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
    UPDATED: Now uses unified processing_jobs table.

    Args:
        job_id: Hyperbrowser job ID
        urls: List of URLs to extract markdown from
        org_id: Organization ID
        user_id: User ID who created the job

    Returns:
        The created record
    """
    # Use the new unified job processing system
    job_record = await create_processing_job(
        job_id=job_id,
        job_type="markdown_extraction",
        org_id=org_id,
        user_id=user_id,
        total_items=len(urls),
        metadata={"urls": urls, "total_urls": len(urls)}
    )

    if job_record:
        try:
            # Create records for each URL in the markdown_content table
            url_records = [{
                "job_id": job_id,
                "url": url,
                "status": "pending",
                "org_id": _convert_org_id(org_id)
            } for url in urls]

            # Save URL records to database
            if url_records:
                supabase.table(MARKDOWN_CONTENT_TABLE).insert(url_records).execute()
                logger.info(f"Created {len(url_records)} URL records for job_id: {job_id}")

            logger.info(f"Created markdown extraction job record for job_id: {job_id}")
            return job_record
        except Exception as e:
            logger.error(f"Error creating URL records: {str(e)}")
            return job_record
    else:
        # Fallback record for backward compatibility
        fallback_record = {
            "job_id": job_id,
            "status": "pending",
            "total_urls": len(urls),
            "completed_urls": 0,
            "org_id": org_id,
            "created_by": user_id
        }
        logger.warning(f"Using fallback record for markdown job {job_id}")
        return fallback_record

async def get_markdown_extraction_job(job_id: str, org_id: Optional[str] = None):
    """
    Get a markdown extraction job by its ID.
    UPDATED: Now uses unified processing_jobs table.

    Args:
        job_id: Hyperbrowser job ID
        org_id: Optional organization ID for security check

    Returns:
        The job record or None if not found
    """
    # Try unified processing jobs table first
    job_record = await get_processing_job(job_id, org_id)

    if job_record and job_record.get("job_type") == "markdown_extraction":
        # Convert to legacy format for backward compatibility
        metadata = job_record.get("metadata", {})
        legacy_format = {
            "job_id": job_record["job_id"],
            "status": job_record["status"],
            "total_urls": metadata.get("total_urls", job_record.get("total_items", 0)),
            "completed_urls": job_record.get("completed_items", 0),
            "org_id": job_record["org_id"],
            "created_by": job_record.get("created_by"),
            "created_at": job_record.get("created_at"),
            "updated_at": job_record.get("updated_at")
        }
        return legacy_format

    # No job found
    return None

async def update_markdown_extraction_status(job_id: str, status: str, org_id: Optional[str] = None):
    """
    Update the status of a markdown extraction job.
    UPDATED: Now uses unified processing_jobs table.

    Args:
        job_id: Hyperbrowser job ID
        status: New status (pending, processing, completed, failed)
        org_id: Optional organization ID for security check

    Returns:
        The updated record or None if failed
    """
    # Update the unified processing job
    job_record = await update_processing_job(
        job_id=job_id,
        status=status,
        org_id=org_id
    )

    if job_record:
        logger.info(f"Updated markdown extraction job {job_id} status to {status}")
        # Return in legacy format for backward compatibility
        metadata = job_record.get("metadata", {})
        legacy_format = {
            "job_id": job_record["job_id"],
            "status": job_record["status"],
            "total_urls": metadata.get("total_urls", job_record.get("total_items", 0)),
            "completed_urls": job_record.get("completed_items", 0),
            "org_id": job_record["org_id"],
            "updated_at": job_record.get("updated_at")
        }
        return legacy_format
    else:
        logger.error(f"Error updating markdown job status for {job_id}")
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
    UPDATED: Now uses unified processing_jobs table.

    Args:
        job_id: Unique job ID
        org_id: Organization ID
        user_id: User ID who created the job

    Returns:
        The created record
    """
    # Use the new unified job processing system
    job_record = await create_processing_job(
        job_id=job_id,
        job_type="document_conversion",
        org_id=org_id,
        user_id=user_id,
        total_items=0,  # Will be updated when files are added
        metadata={"total_files": 0, "completed_files": 0}
    )

    if job_record:
        logger.info(f"Created document conversion job record for job_id: {job_id}")
        return job_record
    else:
        # Fallback record for backward compatibility
        fallback_record = {
            "job_id": job_id,
            "status": "pending",
            "total_files": 0,
            "completed_files": 0,
            "org_id": org_id,
            "created_by": user_id
        }
        logger.warning(f"Using fallback record for document job {job_id}")
        return fallback_record

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

async def update_document_content_task_id(job_id: str, filename: str, task_id: str, org_id: Optional[str] = None):
    """
    Update the Docling task ID for a document.
    
    Args:
        job_id: Job ID
        filename: Filename
        task_id: Docling server task ID
        org_id: Organization ID
    """
    try:
        update_data = {
            "docling_task_id": task_id,
            "updated_at": dt.now().isoformat()
        }
        
        query = supabase.table(DOCUMENT_CONTENT_TABLE).update(update_data).eq("job_id", job_id).eq("filename", filename)
        
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        logger.info(f"Updated Docling task_id for file {filename} in job {job_id}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating document task_id: {str(e)}")
        return None