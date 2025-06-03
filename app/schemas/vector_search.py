"""
Pydantic models for vector search API.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class VectorSearchRequest(BaseModel):
    """Request model for vector search."""
    query: str = Field(..., description="The search query text")
    org_id: str = Field(..., description="Organization ID to filter results")
    limit: int = Field(5, description="Maximum number of results to return")
    threshold: float = Field(0.7, description="Similarity threshold (0-1)")


class VectorSearchResponse(BaseModel):
    """Response model for vector search."""
    query: str = Field(..., description="The original search query")
    results: List[Dict[str, Any]] = Field([], description="List of matching chunks with similarity scores")
    message: str = Field(..., description="Status message")


class ProcessDocumentResponse(BaseModel):
    """Response model for document processing."""
    document_id: str = Field(..., description="ID of the processed document")
    chunk_count: int = Field(..., description="Number of chunks created")
    chunk_ids: List[str] = Field(..., description="List of chunk IDs")
    message: str = Field(..., description="Status message")
