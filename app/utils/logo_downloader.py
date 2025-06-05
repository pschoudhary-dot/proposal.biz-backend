"""
Utility functions for downloading and storing website images.
"""
import requests
from io import BytesIO
from PIL import Image
from urllib.parse import urlparse
import os
from app.core.logging import logger
from app.core.database import supabase

# Name of the Supabase storage bucket
BUCKET_NAME = "websiteassets"

async def download_image(image_url: str) -> tuple:
    """
    Download an image from a URL.
    
    Args:
        image_url: URL of the image to download
        
    Returns:
        tuple: (image_data, content_type, file_extension)
    """
    if not image_url:
        return None, None, None
    
    try:
        # Get the file extension from the URL
        path = urlparse(image_url).path
        file_extension = os.path.splitext(path)[1].lower() or ".png"
        
        # Download the image
        logger.info(f"Downloading image from {image_url}")
        response = requests.get(image_url, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        # Get content type from headers if available
        content_type = response.headers.get("content-type", "image/png")
        
        # Validate image data for non-SVG images
        if "svg" not in content_type:
            Image.open(BytesIO(response.content)).verify()
            
        return response.content, content_type, file_extension
            
    except Exception as e:
        logger.warning(f"Error downloading image: {str(e)}")
        return None, None, None

async def store_image_in_supabase(image_data, content_type, file_extension, job_id: str, image_type: str) -> str:
    """
    Store an image in Supabase storage.
    
    Args:
        image_data: Raw image data
        content_type: MIME type of the image
        file_extension: File extension (including .)
        job_id: The job ID (UUID string)
        image_type: Type of image ('logo' or 'favicon')
        
    Returns:
        str: Public URL of the stored image or None if failed
    """
    if not image_data:
        return None
        
    try:
        # Create path for storing the image
        file_name = f"{job_id}_{image_type}{file_extension}"
        file_path = f"jobs/{job_id}/{file_name}"
        
        # Upload to Supabase storage
        logger.info(f"Uploading {image_type} to storage: {file_path}")
        
        # Upload the file
        supabase.storage.from_(BUCKET_NAME).upload(
            file_path,
            image_data,
            {"content-type": content_type}
        )
        
        # Get the public URL
        file_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_path)
        logger.info(f"Uploaded {image_type} successfully")
        return file_url
        
    except Exception as e:
        logger.error(f"Error storing {image_type}: {str(e)}")
        return None

async def process_website_images(logo_url: str, job_id: str, org_id: int) -> dict:
    """
    Process and store logo from extraction data.
    
    Args:
        logo_url: URL of the logo to download
        job_id: The job ID (UUID string)
        org_id: Organization ID (integer)
        
    Returns:
        dict: Result of image processing
    """
    result = {
        "logo_file_path": None,
        "error": None
    }
    
    if not logo_url:
        result["error"] = "No logo URL provided"
        return result
    
    try:
        # Download logo
        logo_data, logo_type, logo_ext = await download_image(logo_url)
        
        if logo_data:
            logo_path = await store_image_in_supabase(
                logo_data, logo_type, logo_ext, job_id, "logo"
            )
            
            if logo_path:
                result["logo_file_path"] = logo_path
                
                # Update extraction content record with logo path
                try:
                    from app.core.database import supabase
                    supabase.table("extraction_content").update({
                        "logo_file_path": logo_path
                    }).eq("job_id", job_id).eq("org_id", org_id).execute()
                    
                    logger.info(f"Updated extraction content with logo path for job {job_id}")
                except Exception as e:
                    logger.error(f"Error updating extraction content with logo path: {str(e)}")
            else:
                result["error"] = "Failed to store logo in Supabase"
        else:
            result["error"] = "Failed to download logo"
            
    except Exception as e:
        logger.error(f"Error processing logo: {str(e)}")
        result["error"] = str(e)
            
    return result

async def process_favicon(favicon_url: str, job_id: str, org_id: int) -> dict:
    """
    Process and store favicon from extraction data.
    
    Args:
        favicon_url: URL of the favicon to download
        job_id: The job ID (UUID string)
        org_id: Organization ID (integer)
        
    Returns:
        dict: Result of favicon processing
    """
    result = {
        "favicon_file_path": None,
        "error": None
    }
    
    if not favicon_url:
        result["error"] = "No favicon URL provided"
        return result
    
    try:
        # Download favicon
        favicon_data, favicon_type, favicon_ext = await download_image(favicon_url)
        
        if favicon_data:
            favicon_path = await store_image_in_supabase(
                favicon_data, favicon_type, favicon_ext, job_id, "favicon"
            )
            
            if favicon_path:
                result["favicon_file_path"] = favicon_path
                
                # Update extraction content record with favicon path
                try:
                    from app.core.database import supabase
                    supabase.table("extraction_content").update({
                        "favicon_file_path": favicon_path
                    }).eq("job_id", job_id).eq("org_id", org_id).execute()
                    
                    logger.info(f"Updated extraction content with favicon path for job {job_id}")
                except Exception as e:
                    logger.error(f"Error updating extraction content with favicon path: {str(e)}")
            else:
                result["error"] = "Failed to store favicon in Supabase"
        else:
            result["error"] = "Failed to download favicon"
            
    except Exception as e:
        logger.error(f"Error processing favicon: {str(e)}")
        result["error"] = str(e)
            
    return result