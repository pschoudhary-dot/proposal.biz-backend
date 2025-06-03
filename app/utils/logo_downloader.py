"""
Simple utility functions for downloading and storing website images.
"""
import requests
import json
from io import BytesIO
from PIL import Image
from urllib.parse import urlparse
import os
from app.core.logging import logger

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

async def store_image_in_supabase(supabase_client, image_data, content_type, file_extension, job_id: str, image_type: str) -> str:
    """
    Store an image in Supabase storage.
    
    Args:
        supabase_client: Initialized Supabase client
        image_data: Raw image data
        content_type: MIME type of the image
        file_extension: File extension (including .)
        job_id: The job ID 
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
        supabase_client.storage.from_(BUCKET_NAME).upload(
            file_path,
            image_data,
            {"content-type": content_type}
        )
        
        # Get the public URL
        file_url = supabase_client.storage.from_(BUCKET_NAME).get_public_url(file_path)
        logger.info(f"Uploaded {image_type} successfully")
        return file_url
        
    except Exception as e:
        logger.error(f"Error storing {image_type}: {str(e)}")
        return None

async def process_website_images(supabase_client, extraction_data: dict, job_id: str) -> dict:
    """
    Process and store logo and favicon from extraction data.
    
    Args:
        supabase_client: Initialized Supabase client
        extraction_data: The extraction result data
        job_id: The job ID
        
    Returns:
        dict: Paths to stored images and color palette
    """
    result = {
        "logo_file_path": None,
        "favicon_file_path": None,
        "color_palette": None
    }
    
    # 1. Store color palette if available
    if extraction_data and "color_palette" in extraction_data:
        result["color_palette"] = extraction_data["color_palette"]
    
    # 2. Process favicon
    if extraction_data and extraction_data.get("favicon"):
        favicon_url = extraction_data["favicon"]
        favicon_data, favicon_type, favicon_ext = await download_image(favicon_url)
        
        if favicon_data:
            favicon_path = await store_image_in_supabase(
                supabase_client, favicon_data, favicon_type, favicon_ext, job_id, "favicon"
            )
            result["favicon_file_path"] = favicon_path
    
    # 3. Process logo
    if extraction_data and extraction_data.get("logo") and extraction_data["logo"].get("url"):
        logo_url = extraction_data["logo"]["url"]
        logo_data, logo_type, logo_ext = await download_image(logo_url)
        
        if logo_data:
            logo_path = await store_image_in_supabase(
                supabase_client, logo_data, logo_type, logo_ext, job_id, "logo"
            )
            result["logo_file_path"] = logo_path
            
    return result