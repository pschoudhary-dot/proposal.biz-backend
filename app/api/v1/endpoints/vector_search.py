"""
API endpoints for vector search and document processing.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import Optional
import uuid

from app.core.logging import logger
from app.api.deps import get_current_user_id
from app.utils.convert_to_vector import process_document, similarity_search
from app.schemas.vector_search import (
    VectorSearchRequest,
    VectorSearchResponse,
    ProcessDocumentResponse
)
from app.core.database import (
    create_org_content_source_record,
    get_user_organizations
)

router = APIRouter()


@router.post("/process-document", response_model=ProcessDocumentResponse)
async def convert_document_to_vectors(
    file: UploadFile = File(...),
    source_id: Optional[str] = Form(None),
    org_id: Optional[int] = Form(None),
    use_semantic_chunking: bool = Form(True),
    user_id: int = Depends(get_current_user_id)
):
    """
    Process a document by chunking it semantically and creating vector embeddings.
    
    This endpoint accepts a document file, chunks it based on semantic similarity,
    creates embeddings for each chunk, and stores them in the database.
    
    Returns a list of chunk IDs that were created.
    """
    try:
        # Get org_id if not provided
        if not org_id:
            orgs = await get_user_organizations(user_id)
            if not orgs:
                raise HTTPException(status_code=400, detail="User is not a member of any organization")
            org_id = orgs[0]["org_id"]
        
        # Generate a source ID if not provided
        if not source_id:
            # Create a content source record first
            source_id = await create_org_content_source_record(
                job_id=str(uuid.uuid4()),
                filename=file.filename,
                org_id=org_id,
                user_id=user_id
            )
            
            if not source_id:
                raise HTTPException(status_code=500, detail="Failed to create content source record")
        
        logger.info(f"Processing document {file.filename} with source ID {source_id}")
        
        # Read file content
        content = await file.read()
        text = content.decode("utf-8")
        
        # Create metadata
        metadata = {
            "filename": file.filename,
            "content_type": file.content_type
        }
        
        # Process the document
        chunk_ids = await process_document(
            source_id=source_id,     # UUID string
            org_id=org_id,           # Integer
            user_id=user_id,         # Integer
            text=text,
            metadata=metadata,
            use_semantic_chunking=use_semantic_chunking
        )
        
        if not chunk_ids:
            raise HTTPException(status_code=500, detail="Failed to process document")
        
        return ProcessDocumentResponse(
            document_id=source_id,
            chunk_count=len(chunk_ids),
            chunk_ids=chunk_ids,
            message="Document processed successfully"
        )
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


@router.post("/search", response_model=VectorSearchResponse)
async def search_documents(
    request: VectorSearchRequest,
    user_id: int = Depends(get_current_user_id)
):
    """
    Search for documents similar to the query text.
    
    This endpoint creates an embedding for the query text and searches for
    similar document chunks in the database.
    
    Returns a list of matching chunks with similarity scores.
    """
    try:
        logger.info(f"Searching for documents similar to query: {request.query[:50]}...")
        
        # Convert org_id from string to integer if needed
        org_id = int(request.org_id) if isinstance(request.org_id, str) else request.org_id
        
        # Perform similarity search
        results = await similarity_search(
            query=request.query,
            org_id=org_id,           # Integer
            limit=request.limit,
            threshold=request.threshold
        )
        
        if not results:
            return VectorSearchResponse(
                query=request.query,
                results=[],
                message="No matching documents found"
            )
        
        return VectorSearchResponse(
            query=request.query,
            results=results,
            message=f"Found {len(results)} matching documents"
        )
        
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching documents: {str(e)}")