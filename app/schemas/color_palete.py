"""
Schema definitions for color palette extraction.
"""
from typing import List
from pydantic import BaseModel, Field

class ColorPaletteRequest(BaseModel):
    """Request schema for color palette extraction"""
    image_source: str = Field(..., description="URL or file path of the image")
    palette_size: int = Field(5, description="Number of colors to extract", ge=3, le=10)

class ColorPaletteResponse(BaseModel):
    """Response schema for color palette extraction"""
    colors: List[List[int]] = Field(..., description="List of RGB color values")


"""
class ColorJobResponse(BaseModel):
    job_id: str
    status: str
    message: str

class ColorJobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int = 0
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    error: Optional[str] = None

class ColorJobResultResponse(BaseModel):
    job_id: str
    status: str
    colors: Optional[list] = None
    error: Optional[str] = None

"""