"""
API endpoints for color palette extraction.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from app.schemas.color_palete import ColorPaletteResponse
from app.utils.color_extraction import extract_color_palette
from app.core.logging import logger
from app.core.database import update_extraction_job_color_palette
from typing import Optional
import uuid
from app.api.deps import get_current_user_id
from fastapi import Depends

router = APIRouter()

@router.get("/extract", response_model=ColorPaletteResponse)
async def extract_colors(
    image_source: str = Query(..., description="URL or path of the image to extract colors from"),
    org_id: str = Query(..., description="Organization ID to associate with this extraction"),
    background_tasks: BackgroundTasks = None,
    palette_size: Optional[int] = Query(5, ge=3, le=10, description="Number of colors to extract (between 3-10)"),
    user_id: str = Depends(get_current_user_id)
) -> ColorPaletteResponse:
    """
    Extract color palette from an image.
    
    Args:
        image_source: URL or path of the image to extract colors from
        org_id: Organization ID to associate with this extraction
        palette_size: Number of colors to extract (between 3-10)
        user_id: Authenticated user ID
        
    Returns:
        ColorPaletteResponse: The extracted color palette information
    """
    try:
        # Validate palette size
        if palette_size < 3 or palette_size > 10:
            palette_size = 5  # Reset to default if invalid
        
        # Generate a job ID for this extraction
        job_id = str(uuid.uuid4())
        logger.info(f"Starting color extraction job {job_id} for {image_source}")
        
        # Extract colors
        colors = extract_color_palette(
            image_source=image_source,
            palette_size=palette_size
        )

        # Convert colors to int
        colors = [[int(c) for c in color] for color in colors]
        
        # Schedule saving results to database as a background task
        if background_tasks:
            background_tasks.add_task(
                update_extraction_job_color_palette,
                job_id=job_id,
                image_source=image_source,
                colors=colors,
                org_id=org_id  # Use the org_id from query parameters
            )
        
        # Return the colors immediately
        return ColorPaletteResponse(colors=colors)
    
    except Exception as e:
        logger.error(f"Error in color extraction API: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error extracting color palette: {str(e)}")