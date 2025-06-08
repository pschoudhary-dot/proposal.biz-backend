"""
Pydantic models for markdown extraction API - Updated for new schema.
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator


class MarkdownExtractionRequest(BaseModel):
    """Request model for markdown extraction."""
    urls: List[str] = Field(..., description="List of URLs to extract markdown from")
    org_id: Optional[int] = Field(None, description="Organization ID. If not provided, user's default organization will be used.")
    
    @validator('urls')
    def validate_urls(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one URL must be provided')
        if len(v) > 1000:
            raise ValueError('Maximum 1000 URLs allowed per batch')
        return v


class MarkdownExtractionResponse(BaseModel):
    """Response model for markdown extraction job creation."""
    job_id: str = Field(..., description="Unique identifier for the extraction job")
    org_id: int = Field(..., description="Organization ID that owns this job")
    status: str = Field(..., description="Current status of the extraction job")
    message: Optional[str] = Field(None, description="Additional information about the job")
    total_urls: int = Field(..., description="Total number of URLs in the job")


class MarkdownStatusResponse(BaseModel):
    """Response model for checking markdown extraction job status."""
    job_id: str = Field(..., description="Unique identifier for the extraction job")
    org_id: int = Field(..., description="Organization ID that owns this job")
    status: str = Field(..., description="Current status of the extraction job")
    message: Optional[str] = Field(None, description="Additional information about the job")
    completed_urls: int = Field(0, description="Number of URLs that have been processed")
    total_urls: int = Field(0, description="Total number of URLs in the job")


class ExtractedLink(BaseModel):
    """Model for a single extracted link."""
    url: str = Field(..., description="The extracted link URL")


class MarkdownContent(BaseModel):
    """Model for markdown content extracted from a URL."""
    url: str = Field(..., description="URL that was processed")
    status: str = Field(..., description="Status of this specific URL extraction")
    markdown_text: Optional[str] = Field(None, description="Extracted markdown content")
    error: Optional[str] = Field(None, description="Error message if extraction failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata about the page")
    links: Optional[List[str]] = Field(None, description="Links found on the page")
    org_id: Optional[int] = Field(None, description="Organization ID that owns this content")


class MarkdownResultResponse(BaseModel):
    """Response model for getting markdown extraction results."""
    job_id: str = Field(..., description="Unique identifier for the extraction job")
    org_id: int = Field(..., description="Organization ID that owns this job")
    status: str = Field(..., description="Overall status of the extraction job")
    completed_urls: int = Field(0, description="Number of URLs that have been processed")
    total_urls: int = Field(0, description="Total number of URLs in the job")
    results: Optional[List[MarkdownContent]] = Field(None, description="Extracted markdown content for each URL")
    error: Optional[str] = Field(None, description="Error message if job failed")