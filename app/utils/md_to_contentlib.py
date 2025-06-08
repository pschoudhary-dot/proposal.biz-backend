"""Utility functions for processing markdown content and extracting structured data with OpenRouter and Langfuse."""
import os
from typing import List, Dict, Any
from openai import AsyncOpenAI
import instructor
from app.core.database_content_lib import get_content_sources_by_ids
from app.core.logging import logger
from app.schemas.content_library import BusinessInformationSchema
from app.core.config import settings
from langfuse import Langfuse
from langfuse.decorators import observe

# Initialize Langfuse client
langfuse = Langfuse(
    secret_key=settings.LANGFUSE_SECRET_KEY,
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    host=settings.LANGFUSE_HOST
)

def estimate_token_count(content: str | int) -> int:
    """
    Estimate token count based on character count.
    
    Args:
        content: Input text as string or length as integer
        
    Returns:
        Estimated token count
    """
    if isinstance(content, str):
        char_count = len(content)
    else:  # Assume it's already a length (integer)
        char_count = content
        
    return int(char_count / settings.CHARS_PER_TOKEN_ESTIMATE)

def select_optimal_model(content_length: int) -> Dict[str, Any]:
    """
    Select the optimal model based on content length and context limits.
    
    Args:
        content_length: Length of content in characters (integer)
        
    Returns:
        Selected model configuration
    """
    estimated_tokens = estimate_token_count(content_length)
    
    # Add buffer for system prompt, user prompt, and response
    total_tokens_needed = estimated_tokens + 5000  # 5K buffer
    
    # Try models in order of preference
    model_priority = [
        settings.DEFAULT_CONTENT_LIB_MODEL,
        "gemini-2.5-pro-preview",
        "deepseek-r1"
    ]
    
    for model_key in model_priority:
        if model_key in settings.OPENROUTER_MODELS:
            model_config = settings.OPENROUTER_MODELS[model_key]
            if total_tokens_needed <= model_config["context_limit"]:
                logger.info(f"Selected model {model_key} for {estimated_tokens} estimated tokens")
                return model_config
    
    # If no model can handle the content, raise an error
    raise ValueError(f"Content too large ({estimated_tokens} estimated tokens) for any available model. Maximum supported: {max(m['context_limit'] for m in settings.OPENROUTER_MODELS.values())}")

async def get_system_prompt() -> str:
    """Get the system prompt from Langfuse or use a default one."""
    try:
        prompt = langfuse.get_prompt("SYS_prompt", label="production")
        return prompt.prompt
    except Exception as e:
        logger.error(f"Error getting system prompt from Langfuse: {str(e)}")
        return """You are a meticulous data extraction specialist. Your task is to extract ALL business information from provided documents and organize it according to the given JSON schema structure.

CRITICAL EXTRACTION RULES:

1. COMPLETENESS: Extract EVERY piece of information available. If a company has 8 services, list all 8. If they have 20 team members, list all 20. Never summarize or consolidate - capture everything.

2. ACCURACY: Extract information EXACTLY as it appears in the source documents. Do not:
   - Make assumptions or inferences
   - Create or invent any information
   - Fill in missing data with guesses
   - Combine or summarize multiple items into one

3. EMPTY FIELDS: If information for a required field is not found in the documents:
   - For strings: Use empty string ""
   - For arrays: Use empty array []
   - For objects: Include the object with empty/default values for its properties

4. EXTRACTION METHODOLOGY:
   - Scan the entire document thoroughly before starting extraction
   - Look for information in all possible locations (headers, footers, sidebars, etc.)
   - Parse all listed items completely - never stop at examples or samples
   - Check for paginated content or "View More" sections that might contain additional items

5. ARRAY FIELDS: For fields that accept arrays (like Services, Portfolio, Team, etc.):
   - Include EVERY instance found in the documents
   - Each item should be a complete, separate entry
   - Do not merge similar items
   - Preserve the original order when possible

6. SPECIFIC FIELD GUIDANCE:
   - Services: Extract each service as a separate object, even if they seem related
   - Portfolio/Projects: List every single project mentioned, no matter how briefly
   - Case Studies: Include all success stories, testimonials, and client examples
   - Team Members: Extract every person mentioned with a role/title
   - Technologies: List all tools, platforms, and integrations mentioned
   - Awards: Include all recognitions, certifications, and accolades
   - FAQs: Extract every question-answer pair found

7. TEXT EXTRACTION:
   - Preserve the original wording and phrasing
   - Maintain professional language and terminology
   - Keep numerical values and percentages exactly as stated
   - Include units of measurement (%, $, months, etc.)

8. URL AND LINK EXTRACTION:
   - Extract complete URLs including protocol (http/https)
   - For relative links, note them as-is without constructing full URLs
   - Include all external links, social media profiles, and resource links

9. HIERARCHICAL INFORMATION:
   - Respect parent-child relationships (e.g., service categories)
   - Maintain groupings and classifications from the source
   - Preserve organizational structures

10. VALIDATION:
    - Double-check that no information has been skipped
    - Ensure all required fields are present in the output
    - Verify that arrays contain all found items, not just samples

Remember: Your role is to extract and organize information, not to interpret, summarize, or make editorial decisions. Every piece of business information in the source documents should appear in your extraction."""

async def get_user_prompt() -> str:
    """Get the user prompt from Langfuse or use a default one."""
    try:
        prompt = langfuse.get_prompt("Model_prompt", label="production")
        return prompt.prompt
    except Exception as e:
        logger.error(f"Error getting user prompt from Langfuse: {str(e)}")
        return """Generate a detailed JSON schema representation of the specified company using only real and verifiable information. Avoid including any fabricated or speculative content.

# Steps

1. Identify and gather accurate, up-to-date information about the company you are tasked to describe. This includes aspects such as the company's name, industry, headquarters, founding date, key personnel, services, products, history, and achievements.
2. Ensure all information is factual and verifiable, pulling from reputable sources.
3. Organize the collected information into a comprehensive JSON schema format.

# Output Format

The output should be formatted as a JSON object. Each key-value pair should represent a specific piece of information about the company. Ensure the JSON schema includes all the information and relevant data

# Notes

- Ensure all entries in the JSON are supported by cited data.
- Do not include placeholders in the final output; ensure each element is populated with actual data.
- Double-check the correctness of the information and ensure there are no speculative entries."""

@observe(name="extract_structured_data")
async def extract_structured_data(content_texts: List[str], org_id: int) -> BusinessInformationSchema:
    """
    Extract structured data from markdown content using OpenRouter LLM.
    
    Args:
        content_texts: List of markdown content texts
        org_id: Organization ID
        
    Returns:
        Structured business information
    """
    try:
        # Combine all content
        combined_content = "\n\n".join(content_texts)
        content_length = len(combined_content)
        
        logger.info(f"Processing {len(content_texts)} documents, total length: {content_length} characters for org_id: {org_id}")
        
        # Select optimal model based on content length
        try:
            model_config = select_optimal_model(content_length)
            model_id = model_config["id"]
            logger.info(f"Using model: {model_id}")
        except ValueError as e:
            logger.error(f"Content length error: {str(e)}")
            raise ValueError(f"Content too large for processing: {str(e)}")
        
        # Get prompts from Langfuse
        system_prompt = await get_system_prompt()
        user_prompt = await get_user_prompt()
        
        # Prepare the complete user message
        full_user_prompt = f"{user_prompt}\n\nContent to process:\n\n{combined_content}"
        
        # Prepare the messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_user_prompt}
        ]
        
        # Create OpenRouter client with instructor
        async_client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://proposal.biz",
                "X-Title": "ProposalBiz Content Library"
            }
        )
        
        # Get the async instructor client
        aclient = instructor.from_openai(async_client, mode=instructor.Mode.JSON)
        
        # Make the API call with timeout and retry settings
        try:
            result = await aclient.chat.completions.create(
                model=model_id,
                messages=messages,
                response_model=BusinessInformationSchema,
                temperature=0.2,
                max_retries=3,
                timeout=120.0  # 2 minutes timeout for large content
            )
            
            logger.info(f"Successfully extracted structured data for org_id: {org_id}")
            logger.debug(f"Extracted data preview: {str(result)[:500]}...")
            
            return result
            
        except Exception as api_error:
            logger.error(f"OpenRouter API error: {str(api_error)}")
            # Check if it's a context length error
            if "context" in str(api_error).lower() or "length" in str(api_error).lower():
                raise ValueError(f"Content exceeds model context limit: {str(api_error)}")
            raise
        
    except Exception as e:
        logger.error(f"Error in extract_structured_data: {str(e)}", exc_info=True)
        raise

@observe(name="process_content_sources")
async def process_content_sources(source_ids: List[str], org_id: int) -> Dict[str, Any]:
    """
    Process multiple content sources and extract structured data.
    
    Args:
        source_ids: List of content source IDs (UUIDs as strings)
        org_id: Organization ID (integer)
        
    Returns:
        Processing result
    """    
    try:
        logger.info(f"Processing content sources: {source_ids} for org_id: {org_id}")
        
        # Get content sources with markdown content
        sources = await get_content_sources_by_ids(source_ids, org_id)
        
        if not sources:
            logger.warning(f"No content sources found for org_id: {org_id}")
            return {"error": "No content sources found"}
        
        # Collect all markdown texts
        content_texts = []
        for source in sources:
            markdown_content = source.get("markdown_content")
            if markdown_content and markdown_content.strip():
                content_texts.append(markdown_content)
                logger.info(f"Added content from source {source['id']}: {len(markdown_content)} characters")
        
        if not content_texts:
            logger.warning(f"No markdown content found in sources for org_id: {org_id}")
            return {"error": "No markdown content found in sources"}
        
        # Extract structured data
        result = await extract_structured_data(content_texts, org_id)
        
        return {"data": result}
        
    except Exception as e:
        logger.error(f"Error processing content sources: {str(e)}", exc_info=True)
        return {"error": str(e)}    