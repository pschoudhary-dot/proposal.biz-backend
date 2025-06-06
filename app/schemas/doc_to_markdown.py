"""
Pydantic models for document to markdown conversion API.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class DocToMarkdownRequest(BaseModel):
    """Request model for document to markdown conversion."""
    job_id: Optional[str] = Field(None, description="Optional job ID. If not provided, one will be generated.")
    org_id: Optional[int] = Field(None, description="Organization ID. If not provided, user's default organization will be used.")


class DocToMarkdownResponse(BaseModel):
    """Response model for document to markdown conversion job creation."""
    job_id: str = Field(..., description="Unique identifier for the conversion job")
    org_id: int = Field(..., description="Organization ID that owns this job")
    status: str = Field(..., description="Current status of the conversion job")
    message: Optional[str] = Field(None, description="Additional information about the job")


class DocToMarkdownStatusResponse(BaseModel):
    """Response model for checking document to markdown conversion job status."""
    job_id: str = Field(..., description="Unique identifier for the conversion job")
    org_id: int = Field(..., description="Organization ID that owns this job")
    status: str = Field(..., description="Current status of the conversion job")
    message: Optional[str] = Field(None, description="Additional information about the job")
    completed_files: int = Field(0, description="Number of files that have been processed")
    total_files: int = Field(0, description="Total number of files in the job")


class DocToMarkdownContent(BaseModel):
    """Model for markdown content extracted from a document."""
    filename: str = Field(..., description="Original filename that was converted")
    status: str = Field(..., description="Status of this specific file conversion")
    markdown_text: Optional[str] = Field(None, description="Extracted markdown content")
    error: Optional[str] = Field(None, description="Error message if conversion failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata about the document")
    org_id: Optional[int] = Field(None, description="Organization ID that owns this content")


class DocToMarkdownResultResponse(BaseModel):
    """Response model for getting document to markdown conversion results."""
    job_id: str = Field(..., description="Unique identifier for the conversion job")
    org_id: int = Field(..., description="Organization ID that owns this job")
    status: str = Field(..., description="Overall status of the conversion job")
    completed_files: int = Field(0, description="Number of files that have been processed")
    total_files: int = Field(0, description="Total number of files in the job")
    results: Optional[List[DocToMarkdownContent]] = Field(None, description="Extracted markdown content for each file")
    error: Optional[str] = Field(None, description="Error message if job failed")
