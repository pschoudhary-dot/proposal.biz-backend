"""Utility functions for processing markdown content and extracting structured data."""
import os
from uuid import UUID
from typing import List, Dict, Any
from openai import OpenAI, AsyncOpenAI
import instructor
from app.core.database_content_lib import get_content_sources
from app.core.logging import logger
from app.schemas.content_library import BusinessInformationSchema
from langfuse import Langfuse
from dotenv import load_dotenv

load_dotenv()

# Initialize Langfuse client
langfuse = Langfuse(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)

# Configure OpenAI client for OpenRouter
client = instructor.from_openai(
    OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    ),
    mode=instructor.Mode.JSON  # or instructor.Mode.TOOLS for tool calling based on our needs
)

DEFAULT_MODEL = "deepseek/deepseek-r1-0528:free" #google/gemini-2.0-flash-exp:free

async def get_system_prompt():
    """Get the system prompt from Langfuse or use a default one."""
    try:
        prompt = langfuse.get_prompt("SYS_prompt", label="production")
        return prompt.prompt
    except Exception as e:
        logger.error(f"Error getting system prompt from Langfuse: {str(e)}")
        return """
        You are an expert business information extractor. Your task is to analyze the provided content and extract structured business information.
        
        INSTRUCTIONS:
        1. Carefully read and analyze the entire content
        2. Extract all relevant business information
        3. Follow the exact schema provided in the response model
        4. If information is not available for a field, leave it as null or empty
        5. Be thorough but only include information explicitly mentioned in the content
        
        IMPORTANT:
        - Extract all services, products, team members, and other business information
        - For each service/product, include all available details
        - For team members, extract names, roles, and other available information
        - Include any pricing information, case studies, or portfolio items
        - Extract technologies, methodologies, and metrics where mentioned
        
        Return the information in the exact format specified by the response model.
        """

async def extract_structured_data(content_texts: List[str], org_id: UUID) -> BusinessInformationSchema:
    """
    Extract structured data from markdown content using LLM.
    
    Args:
        content_texts: List of markdown content texts
        org_id: Organization ID
        
    Returns:
        Structured business information
    """
    try:
        # Get the system prompt
        system_prompt = await get_system_prompt()
        combined_content = "\n\n".join(content_texts)
        
        # Debug log the content being sent to LLM
        logger.debug(f"System prompt: {system_prompt[:200]}...")  # Log first 200 chars
        logger.debug(f"Content length: {len(combined_content)} characters")
        logger.debug(f"Sample content: {combined_content[:500]}...")  # Log first 500 chars
        
        # Prepare the messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract structured business information from the following content. Be thorough and include all relevant details.\n\n{combined_content}"}
        ]
        
        # Use the async client to make the API call
        async_client = AsyncOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        
        # Get the async instructor client
        aclient = instructor.from_openai(async_client, mode=instructor.Mode.JSON)
        
        # Make the API call with timeout and retry settings
        try:
            result = await aclient.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                response_model=BusinessInformationSchema,
                temperature=0.2,
                max_retries=3,
                timeout=60.0  # 60 seconds timeout
            )
            
            # Debug log the result
            logger.debug(f"Successfully extracted data. Result type: {type(result)}")
            logger.debug(f"Sample extracted data: {str(result)[:500]}...")
            
            logger.info(f"Successfully extracted structured data for org_id: {org_id}")
            return result
            
        except Exception as api_error:
            logger.error(f"OpenAI API error: {str(api_error)}")
            # Try to get more detailed error information
            if hasattr(api_error, 'response') and api_error.response:
                logger.error(f"API response: {api_error.response.text}")
            raise
        
    except Exception as e:
        logger.error(f"Error in extract_structured_data: {str(e)}", exc_info=True)
        raise

async def process_content_sources(source_ids: List[UUID], org_id: UUID) -> Dict[str, Any]:
    """
    Process multiple content sources and extract structured data.
    
    Args:
        source_ids: List of content source IDs
        org_id: Organization ID
        
    Returns:
        Processing result
    """    
    try:
        # Get content sources
        sources = await get_content_sources(source_ids, org_id)
        
        if not sources:
            logger.warning(f"No content sources found for org_id: {org_id}")
            return {"error": "No content sources found"}
        
        # Collect all content texts
        content_texts = []
        for source in sources:
            if source.get("parsed_content"):
                content_texts.append(source["parsed_content"])
        
        if not content_texts:
            logger.warning(f"No content found in sources for org_id: {org_id}")
            return {"error": "No content found in sources"}
        
        # Extract structured data
        result = await extract_structured_data(content_texts, org_id)
        
        return {"data": result}
        
    except Exception as e:
        logger.error(f"Error processing content sources: {str(e)}")
        return {"error": str(e)}
