"""Utility for converting documents to vector embeddings.

This module provides functions for:
1. Semantically chunking documents using LangChain
2. Creating embeddings using OpenAI
3. Storing chunks and embeddings in the database
4. Retrieving chunks based on similarity search
"""

import uuid
from typing import List, Dict, Any, Tuple

# LangChain imports
from langchain_openai import OpenAIEmbeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Supabase imports for vector store
from supabase.client import create_client

# Local imports
from app.core.config import settings
from app.core.logging import logger


class DocumentVectorizer:
    """Class for converting documents to vector embeddings and storing them in the database."""

    def __init__(self):
        """Initialize the DocumentVectorizer with OpenAI embeddings."""
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",  # Using the latest embedding model
            dimensions=1536,  # Default dimension size
        )
        
        # Initialize Supabase client
        self.supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        
        # Default chunking parameters
        self.default_chunk_size = 1000
        self.default_chunk_overlap = 200
    
    def chunk_document_semantic(self, 
                               text: str, 
                               metadata: Dict[str, Any] = None,
                               breakpoint_type: str = "percentile",
                               threshold_amount: float = 95.0,
                               min_chunk_size: int = 100) -> List[Document]:
        """Chunk a document based on semantic similarity.
        
        Args:
            text: The text content to chunk
            metadata: Metadata to attach to each chunk
            breakpoint_type: Type of breakpoint to use (percentile, standard_deviation, interquartile, gradient)
            threshold_amount: Threshold amount for breakpoint detection
            min_chunk_size: Minimum chunk size in characters
            
        Returns:
            List of Document objects with chunked content
        """
        try:
            logger.info(f"Semantically chunking document with breakpoint_type={breakpoint_type}")
            
            # Create semantic chunker
            text_splitter = SemanticChunker(
                self.embeddings,
                breakpoint_threshold_type=breakpoint_type,
                breakpoint_threshold_amount=threshold_amount,
                min_chunk_size=min_chunk_size
            )
            
            # Create documents with metadata
            if metadata is None:
                metadata = {}
                
            documents = text_splitter.create_documents([text], [metadata])
            logger.info(f"Document semantically chunked into {len(documents)} chunks")
            
            return documents
        except Exception as e:
            logger.error(f"Error in semantic chunking: {str(e)}")
            # Fall back to recursive character splitting if semantic chunking fails
            return self.chunk_document_recursive(text, metadata)
    
    def chunk_document_recursive(self, 
                               text: str, 
                               metadata: Dict[str, Any] = None,
                               chunk_size: int = None,
                               chunk_overlap: int = None) -> List[Document]:
        """Chunk a document using recursive character splitting.
        
        Args:
            text: The text content to chunk
            metadata: Metadata to attach to each chunk
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
            
        Returns:
            List of Document objects with chunked content
        """
        try:
            if chunk_size is None:
                chunk_size = self.default_chunk_size
                
            if chunk_overlap is None:
                chunk_overlap = self.default_chunk_overlap
                
            logger.info(f"Recursively chunking document with chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
            
            # Create text splitter
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
            )
            
            # Create documents with metadata
            if metadata is None:
                metadata = {}
                
            documents = text_splitter.create_documents([text], [metadata])
            logger.info(f"Document recursively chunked into {len(documents)} chunks")
            
            return documents
        except Exception as e:
            logger.error(f"Error in recursive chunking: {str(e)}")
            # Create a single document if chunking fails
            if metadata is None:
                metadata = {}
            return [Document(page_content=text, metadata=metadata)]
    
    def embed_documents(self, documents: List[Document]) -> List[Tuple[Document, List[float]]]:
        """Create embeddings for a list of documents.
        
        Args:
            documents: List of Document objects to embed
            
        Returns:
            List of tuples containing (document, embedding)
        """
        try:
            logger.info(f"Creating embeddings for {len(documents)} documents")
            
            # Get text content from documents
            texts = [doc.page_content for doc in documents]
            
            # Create embeddings
            embeddings = self.embeddings.embed_documents(texts)
            
            # Return document-embedding pairs
            return list(zip(documents, embeddings))
        except Exception as e:
            logger.error(f"Error creating embeddings: {str(e)}")
            return []
    
    async def store_document_chunks(self, 
                                 document_id: str,
                                 org_id: str,
                                 user_id: str,
                                 document_chunks: List[Tuple[Document, List[float]]]) -> List[str]:
        """Store document chunks and their embeddings in the database.
        
        Args:
            document_id: ID of the original document (used as source_id in the database)
            org_id: Organization ID
            user_id: User ID (not stored in ContentChunks, but used in metadata)
            document_chunks: List of (document, embedding) tuples
            
        Returns:
            List of chunk IDs that were stored
        """
        try:
            logger.info(f"Storing {len(document_chunks)} chunks for document {document_id}")
            
            chunk_ids = []
            
            for idx, (doc, embedding) in enumerate(document_chunks):
                # Generate a unique ID for the chunk
                chunk_id = str(uuid.uuid4())
                
                # Prepare chunk data for storage according to ContentChunks schema
                chunk_data = {
                    "id": chunk_id,
                    "source_id": document_id,
                    "org_id": org_id,
                    "chunk_index": idx,
                    "chunk_text": doc.page_content,
                    "chunk_metadata": {
                        **doc.metadata,  
                        "user_id": user_id, 
                        "chunk_id": chunk_id
                    },
                    "embedding": embedding

                }
                
                # Store chunk in database
                result = await self._store_chunk_in_db(chunk_data)
                
                if result:
                    chunk_ids.append(chunk_id)
            
            logger.info(f"Successfully stored {len(chunk_ids)} chunks in database")
            return chunk_ids
        except Exception as e:
            logger.error(f"Error storing document chunks: {str(e)}")
            return []
    
    async def _store_chunk_in_db(self, chunk_data: Dict[str, Any]) -> bool:
        """Store a single chunk in the database.
        
        Args:
            chunk_data: Data for the chunk to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Insert chunk into contentchunks table
            response = self.supabase.table("contentchunks").insert(chunk_data).execute()
            
            # Check if insertion was successful
            if response.data and len(response.data) > 0:
                return True
            else:
                logger.error(f"Failed to insert chunk: {response.error}")
                return False
        except Exception as e:
            logger.error(f"Database error storing chunk: {str(e)}")
            return False
    
    async def process_document(self,
                            document_id: str,
                            org_id: str,
                            user_id: str,
                            text: str,
                            metadata: Dict[str, Any] = None,
                            use_semantic_chunking: bool = True) -> List[str]:
        """Process a document by chunking, embedding, and storing in the database.
        
        Args:
            document_id: ID of the document
            org_id: Organization ID
            user_id: User ID
            text: Text content of the document
            metadata: Metadata for the document
            use_semantic_chunking: Whether to use semantic chunking (True) or recursive chunking (False)
            
        Returns:
            List of chunk IDs that were stored
        """
        try:
            logger.info(f"Processing document {document_id} for organization {org_id}")
            
            # Add document ID to metadata
            if metadata is None:
                metadata = {}
            metadata["source_id"] = document_id
            metadata["org_id"] = org_id
            
            # Chunk the document
            if use_semantic_chunking:
                chunks = self.chunk_document_semantic(text, metadata)
            else:
                chunks = self.chunk_document_recursive(text, metadata)
            
            # Create embeddings
            document_chunks = self.embed_documents(chunks)
            
            # Store chunks in database
            chunk_ids = await self.store_document_chunks(document_id, org_id, user_id, document_chunks)
            
            return chunk_ids
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            return []
    
    async def similarity_search(self,
                             query: str,
                             org_id: str,
                             limit: int = 5,
                             threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for chunks similar to the query.
        
        Args:
            query: The search query
            org_id: Organization ID to filter results
            limit: Maximum number of results to return
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of matching chunks with similarity scores
        """
        try:
            logger.info(f"Performing similarity search for query: {query[:50]}...")
            
            # Create embedding for query
            query_embedding = self.embeddings.embed_query(query)
            
            # Execute similarity search using the match_documents function
            response = self.supabase.rpc(
                "match_documents",
                {
                    "query_embedding": query_embedding,
                    "filter": {"org_id": org_id},
                    "match_threshold": threshold,
                    "match_count": limit
                }
            ).execute()
            
            if response.data:
                logger.info(f"Found {len(response.data)} matching chunks")
                return response.data
            else:
                logger.warning(f"No matching chunks found for query: {query[:50]}...")
                return []
        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            return []


# Create a singleton instance
document_vectorizer = DocumentVectorizer()


# Convenience functions to use the singleton instance
async def process_document(document_id: str,
                         org_id: str,
                         user_id: str,
                         text: str,
                         metadata: Dict[str, Any] = None,
                         use_semantic_chunking: bool = True) -> List[str]:
    """Process a document by chunking, embedding, and storing in the database."""
    return await document_vectorizer.process_document(
        document_id, org_id, user_id, text, metadata, use_semantic_chunking
    )


async def similarity_search(query: str,
                          org_id: str,
                          limit: int = 5,
                          threshold: float = 0.7) -> List[Dict[str, Any]]:
    """Search for chunks similar to the query."""
    return await document_vectorizer.similarity_search(query, org_id, limit, threshold)
