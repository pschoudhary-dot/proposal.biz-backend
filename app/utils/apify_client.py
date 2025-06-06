"""
Apify client for Docling document processing.
"""
import asyncio
import zipfile
import io
import time
from typing import List, Dict, Any, Optional
from apify_client import ApifyClient

from app.core.config import settings
from app.core.logging import logger

class ApifyDoclingClient:
    """Client for processing documents using Apify Docling actor."""

    def __init__(self, api_token: str):
        """Initialize the Apify client."""
        if not api_token:
            raise ValueError("Apify API token is required.")
        self.client = ApifyClient(api_token)
        self.actor_id = "vancura/docling"

    def process_documents_from_urls(
        self,
        urls: List[str],
        output_formats: List[str] = None,
        do_ocr: bool = False
    ) -> Dict[str, Any]:
        """
        Process documents from URLs using Apify Docling actor. This is a synchronous, blocking call.

        Args:
            urls: List of document URLs to process
            output_formats: List of output formats (default: ["md"])
            do_ocr: Whether to perform OCR on documents

        Returns:
            Dictionary with processing results, including extracted file content.
        """
        if output_formats is None:
            output_formats = ["md"]

        run_input = {
            "http_sources": [{"url": url} for url in urls],
            "options": {
                "to_formats": output_formats,
                "do_ocr": do_ocr
            }
        }

        logger.info(f"Starting Apify Docling actor for {len(urls)} documents")
        logger.debug(f"Apify run_input: {run_input}")

        try:
            run = self.client.actor(self.actor_id).call(run_input=run_input)
            logger.info(f"Apify run finished with ID: {run['id']}, Status: {run['status']}")

            results = {
                "run_id": run["id"],
                "status": run["status"],
                "dataset_id": run.get("defaultDatasetId"),
                "key_value_store_id": run.get("defaultKeyValueStoreId"),
                "extracted_content": {}
            }

            if run["status"] != "SUCCEEDED":
                logger.error(f"Apify run {run['id']} did not succeed.")
                return results

            kv_store = self.client.key_value_store(run["defaultKeyValueStoreId"])
            output_record = None
            max_retries = 5
            retry_delay = 3

            for attempt in range(max_retries):
                logger.info(f"Attempt {attempt + 1}/{max_retries} to fetch 'OUTPUT' record.")
                record = kv_store.get_record("OUTPUT")
                if record and record.get("value"):
                    logger.info("Successfully fetched 'OUTPUT' record.")
                    output_record = record
                    break
                
                logger.warning(f"'OUTPUT' record not found or is empty, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)

            if not output_record:
                logger.error("Could not find 'OUTPUT' record after all retries.")
                return results
                
            zip_bytes = output_record.get("value")

            if not isinstance(zip_bytes, bytes):
                logger.error(f"Expected 'OUTPUT' record value to be bytes, but got {type(zip_bytes)}. Value: {zip_bytes}")
                return results

            logger.info(f"Received {len(zip_bytes)} bytes of ZIP data directly from key-value store.")

            with io.BytesIO(zip_bytes) as zip_buffer:
                with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
                    for filename in zip_ref.namelist():
                        if filename.endswith('.md') and not filename.startswith('__MACOSX'):
                            with zip_ref.open(filename) as md_file:
                                markdown_content = md_file.read().decode('utf-8')
                                results["extracted_content"][filename] = markdown_content
                                logger.info(f"Extracted markdown from {filename}")

            logger.info(f"Successfully processed Apify run and extracted {len(results['extracted_content'])} files.")
            return results

        except Exception as e:
            logger.error(f"Error during synchronous Apify processing: {str(e)}", exc_info=True)
            raise

apify_docling_client: Optional[ApifyDoclingClient] = None

def get_apify_client() -> ApifyDoclingClient:
    """Get or create Apify client instance."""
    global apify_docling_client
    if apify_docling_client is None:
        api_token = getattr(settings, 'APIFY_API_TOKEN', None)
        apify_docling_client = ApifyDoclingClient(api_token)
    return apify_docling_client

async def process_documents_with_apify(
    urls: List[str],
    output_formats: List[str] = None,
    do_ocr: bool = False
) -> Dict[str, Any]:
    """
    Async wrapper for running the synchronous Apify processing in a thread pool.
    """
    if output_formats is None:
        output_formats = ["md"]
    
    client = get_apify_client()
    
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            client.process_documents_from_urls,
            urls,
            output_formats,
            do_ocr
        )
        return result
    except Exception as e:
        logger.error(f"Error in async wrapper for Apify: {str(e)}", exc_info=True)
        raise
