"""
Utility functions for markdown extraction using Hyperbrowser API.
"""
from typing import List
import asyncio
from hyperbrowser import Hyperbrowser
from hyperbrowser.models import StartBatchScrapeJobParams, ScrapeOptions
from app.core.config import settings
from app.core.logging import logger
from app.core.database import (
    update_url_markdown_content,
    update_markdown_extraction_status
)


async def start_batch_scrape(job_id: str, urls: List[str], org_id: str) -> None:
    """
    Process multiple URLs using batch scraping.
    
    Args:
        job_id: The unique job identifier
        urls: List of URLs to scrape
        org_id: Organization ID
    """
    logger.info(f"Starting batch scraping for job {job_id} with {len(urls)} URLs")
    
    try:
        # Update job status to running
        await update_markdown_extraction_status(job_id, "running", org_id)
        
        # Initialize Hyperbrowser client
        client = Hyperbrowser(api_key=settings.HYPERBROWSER_API_KEY)
        
        # Ensure all URLs have a scheme
        processed_urls = []
        for url in urls:
            if not url.startswith('http'):
                url = f"https://{url}"
                logger.info(f"Added https:// scheme to URL: {url}")
            processed_urls.append(url)
        
        # Start batch scrape
        logger.info(f"Starting batch scrape for {len(processed_urls)} URLs")
        try:
            # Initialize URL records with processing status
            for url in processed_urls:
                await update_url_markdown_content(
                    job_id=job_id,
                    url=url,
                    markdown_text="",
                    status="processing",
                    org_id=org_id
                )
            
            # Start batch scrape
            batch_job = client.scrape.batch.start(
                StartBatchScrapeJobParams(
                    urls=processed_urls,
                    scrape_options=ScrapeOptions(
                        formats=["markdown", "links"],
                        only_main_content=True,
                        timeout=30000,
                        wait_until="networkidle"
                    )
                )
            )
            
            # Poll for batch job completion
            await poll_batch_job_status(client, job_id, batch_job.job_id, org_id)
            
        except Exception as e:
            logger.error(f"Error starting batch scrape: {str(e)}")
            await update_markdown_extraction_status(job_id, "failed", org_id)
            
    except Exception as e:
        logger.error(f"Error in batch processing for job {job_id}: {str(e)}")
        await update_markdown_extraction_status(job_id, "failed", org_id)


async def poll_batch_job_status(client: Hyperbrowser, job_id: str, hyperbrowser_job_id: str, org_id: str) -> None:
    """
    Poll Hyperbrowser for batch job status until completion.
    
    Args:
        client: Hyperbrowser client
        job_id: Our internal job ID
        hyperbrowser_job_id: Hyperbrowser's job ID
        org_id: Organization ID
    """
    max_attempts = 60  # Maximum number of polling attempts (10 minutes at 10-second intervals)
    attempt = 0
    
    while attempt < max_attempts:
        try:
            # Check job status
            status_response = client.scrape.batch.get_status(hyperbrowser_job_id)
            status = status_response.status
            
            logger.info(f"Hyperbrowser batch job {hyperbrowser_job_id} status: {status}")
            
            if status == "completed":
                # Job is complete, process results
                batch_result = client.scrape.batch.get(hyperbrowser_job_id)
                await process_batch_results(job_id, batch_result, org_id)
                return
            elif status == "failed":
                # Job failed
                logger.error(f"Hyperbrowser batch job {hyperbrowser_job_id} failed")
                await update_markdown_extraction_status(job_id, "failed", org_id)
                return
            
            # Wait before polling again
            await asyncio.sleep(10)  # Poll every 10 seconds
            attempt += 1
            
        except Exception as e:
            logger.error(f"Error polling batch job status: {str(e)}")
            await asyncio.sleep(10)  # Wait before retrying
            attempt += 1
    
    # If we reach here, we've exceeded max attempts
    logger.error(f"Exceeded maximum polling attempts for job {hyperbrowser_job_id}")
    await update_markdown_extraction_status(job_id, "failed", org_id)


async def process_batch_results(job_id: str, batch_result, org_id: str) -> None:
    """
    Process the results of a completed batch scrape job.
    
    Args:
        job_id: Our internal job ID
        batch_result: The batch scrape result from Hyperbrowser
        org_id: Organization ID
    """
    try:
        # Check if we have data
        if not batch_result or not hasattr(batch_result, "data") or not batch_result.data:
            logger.error(f"No data returned from Hyperbrowser for batch job")
            await update_markdown_extraction_status(job_id, "failed", org_id)
            return
        
        logger.info(f"Processing batch results with {len(batch_result.data)} items for job {job_id}")
            
        # Process each URL result
        for result in batch_result.data:
            # Access URL and status directly from the result object
            url = result.url if hasattr(result, "url") else "unknown"
            status = result.status if hasattr(result, "status") else "failed"
            error = result.error if hasattr(result, "error") else None
            
            if status == "completed" and not error:
                # Access data directly from the result object
                markdown_text = ""
                metadata = {}
                links = []
                html = ""
                screenshot = ""
                
                # Safely access attributes
                if hasattr(result, "markdown"):
                    markdown_text = result.markdown
                if hasattr(result, "metadata"):
                    metadata = result.metadata
                if hasattr(result, "links"):
                    links = result.links
                if hasattr(result, "html"):
                    html = result.html
                if hasattr(result, "screenshot"):
                    screenshot = result.screenshot
                
                logger.info(f"Successfully scraped URL {url} for job {job_id} - Markdown length: {len(markdown_text)}, Links: {len(links)}")
                
                # Save to database
                await update_url_markdown_content(
                    job_id=job_id,
                    url=url,
                    markdown_text=markdown_text,
                    status="completed",
                    metadata=metadata,
                    links=links,
                    html=html,
                    screenshot=screenshot,
                    org_id=org_id
                )
            else:
                # Save error
                error_message = error if error else "Unknown error during batch scraping"
                logger.error(f"Error scraping URL {url}: {error_message}")
                
                await update_url_markdown_content(
                    job_id=job_id,
                    url=url,
                    markdown_text="",
                    status="failed",
                    metadata={"error": error_message},
                    links=[],
                    html="",
                    screenshot="",
                    org_id=org_id
                )
                
        # Update job status to completed
        await update_markdown_extraction_status(job_id, "completed", org_id)
        logger.info(f"Completed processing batch results for job {job_id}")
        
    except Exception as e:
        logger.error(f"Error processing batch results: {str(e)}")
        await update_markdown_extraction_status(job_id, "failed", org_id)

