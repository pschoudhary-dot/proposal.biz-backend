"""
Utility functions for markdown extraction using Hyperbrowser API - Improved with on-demand processing.
"""
from typing import List, Optional, Dict, Any
from hyperbrowser import Hyperbrowser
from hyperbrowser.models import StartBatchScrapeJobParams, ScrapeOptions
from app.core.config import settings
from app.core.logging import logger
from app.core.database import (
    update_url_markdown_content,
    update_markdown_extraction_status,
    get_markdown_extraction_job,
    update_processing_job_status
)


async def start_batch_scrape(hyperbrowser_job_id: str, urls: List[str], org_id: int) -> Optional[str]:
    """
    Start batch scraping with Hyperbrowser and return the batch job ID.
    No polling - just submit and return job ID for later checking.
    
    Args:
        hyperbrowser_job_id: Our internal hyperbrowser job identifier
        urls: List of URLs to scrape (max 1000)
        org_id: Organization ID (integer)
        
    Returns:
        Hyperbrowser batch job ID if successful, None if failed
    """
    logger.info(f"Starting batch scrape submission for hyperbrowser job {hyperbrowser_job_id} with {len(urls)} URLs in org {org_id}")
    
    try:
        # Update job status to processing
        await update_markdown_extraction_status(hyperbrowser_job_id, "processing", org_id)
        logger.info(f"Updated job {hyperbrowser_job_id} status to processing")
        
        # Initialize Hyperbrowser client
        if not settings.HYPERBROWSER_API_KEY:
            raise ValueError("HYPERBROWSER_API_KEY not configured")
        
        client = Hyperbrowser(api_key=settings.HYPERBROWSER_API_KEY)
        logger.info(f"Initialized Hyperbrowser client for job {hyperbrowser_job_id}")
        
        # Ensure all URLs have a scheme
        processed_urls = []
        for url in urls:
            original_url = url
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
                logger.debug(f"Added https:// scheme to URL: {original_url} -> {url}")
            processed_urls.append(url)
        
        logger.info(f"Processed {len(processed_urls)} URLs for batch scraping")
        
        # Start batch scrape with Hyperbrowser
        logger.info(f"Submitting Hyperbrowser batch scrape for {len(processed_urls)} URLs")
        
        batch_job = client.scrape.batch.start(
            StartBatchScrapeJobParams(
                urls=processed_urls,
                scrape_options=ScrapeOptions(
                    formats=["markdown", "links"],
                    only_main_content=True,
                    timeout=30000,  # 30 seconds timeout per URL
                    wait_until="networkidle"
                )
            )
        )
        
        hyperbrowser_batch_id = batch_job.job_id
        logger.info(f"Hyperbrowser batch job submitted with ID: {hyperbrowser_batch_id}")
        
        # Store the Hyperbrowser batch job ID in our job metadata
        job = await get_markdown_extraction_job(hyperbrowser_job_id, org_id)
        if job:
            current_metadata = job.get("metadata", {})
            current_metadata["hyperbrowser_batch_id"] = hyperbrowser_batch_id
            await update_processing_job_status(
                job["job_id"], 
                "processing", 
                org_id=org_id,
                metadata=current_metadata # Pass updated metadata
            )
            logger.info(f"Stored Hyperbrowser batch ID {hyperbrowser_batch_id} in job metadata")
        
        return hyperbrowser_batch_id
        
    except Exception as e:
        error_msg = f"Error starting Hyperbrowser batch scrape: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        try:
            await update_markdown_extraction_status(hyperbrowser_job_id, "failed", org_id, error_message=error_msg)
        except Exception as status_error:
            logger.error(f"Failed to update job status to failed: {str(status_error)}")
        
        return None


async def check_and_process_batch_job(hyperbrowser_job_id: str, org_id: int) -> Dict[str, Any]:
    """
    Check Hyperbrowser batch job status and process results if completed.
    This is called on-demand when user checks status or requests results.
    
    Args:
        hyperbrowser_job_id: Our internal hyperbrowser job identifier
        org_id: Organization ID (integer)
        
    Returns:
        Dictionary with status information
    """
    logger.info(f"Checking batch job status for hyperbrowser job {hyperbrowser_job_id}")
    
    try:
        # Get our job record
        job = await get_markdown_extraction_job(hyperbrowser_job_id, org_id)
        if not job:
            logger.error(f"Job not found for hyperbrowser job {hyperbrowser_job_id}")
            return {"status": "not_found", "error": "Job not found"}
        
        # Check if job is already completed or failed
        current_status = job.get("status")
        if current_status in ["completed", "failed"]:
            logger.info(f"Job {hyperbrowser_job_id} already {current_status}")
            return {"status": current_status, "error": job.get("error_message")}
        
        # Get Hyperbrowser batch job ID from metadata
        hyperbrowser_batch_id = job.get("metadata", {}).get("hyperbrowser_batch_id")
        if not hyperbrowser_batch_id:
            error_msg = "Missing Hyperbrowser batch ID"
            logger.error(f"No Hyperbrowser batch ID found for job {hyperbrowser_job_id}")
            await update_markdown_extraction_status(hyperbrowser_job_id, "failed", org_id, error_message=error_msg)
            return {"status": "error", "error": error_msg}
        
        # Initialize Hyperbrowser client
        client = Hyperbrowser(api_key=settings.HYPERBROWSER_API_KEY)
        
        # Check status with Hyperbrowser
        try:
            status_response = client.scrape.batch.get_status(hyperbrowser_batch_id)
            hyperbrowser_status = status_response.status
            
            logger.info(f"Hyperbrowser batch job {hyperbrowser_batch_id} status: {hyperbrowser_status}")
            
            if hyperbrowser_status == "completed":
                # Job completed - process results
                logger.info(f"Processing completed results for job {hyperbrowser_job_id}")
                batch_result = client.scrape.batch.get(hyperbrowser_batch_id)
                await process_batch_results(hyperbrowser_job_id, batch_result, org_id)
                return {"status": "completed"}
                
            elif hyperbrowser_status == "failed":
                # Job failed
                error_msg = f"Hyperbrowser job {hyperbrowser_batch_id} failed."
                # Attempt to get more details from Hyperbrowser if available
                try:
                    batch_result = client.scrape.batch.get(hyperbrowser_batch_id)
                    if batch_result and batch_result.data:
                        failed_urls = [res.url for res in batch_result.data if res.status == 'failed' and res.error]
                        if failed_urls:
                            error_msg += f" Errors on URLs: {', '.join(failed_urls[:3])}"
                except Exception as detail_err:
                    logger.warning(f"Could not get failure details from Hyperbrowser: {detail_err}")

                logger.error(error_msg)
                await update_markdown_extraction_status(hyperbrowser_job_id, "failed", org_id, error_message=error_msg)
                return {"status": "failed", "error": error_msg}
                
            elif hyperbrowser_status in ["pending", "running"]:
                # Job still processing
                logger.debug(f"Hyperbrowser batch job {hyperbrowser_batch_id} still {hyperbrowser_status}")
                return {"status": "processing"}
                
            else:
                logger.warning(f"Unknown Hyperbrowser status: {hyperbrowser_status}")
                return {"status": "unknown", "hyperbrowser_status": hyperbrowser_status}
                
        except Exception as e:
            error_msg = f"Error checking Hyperbrowser status: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await update_markdown_extraction_status(hyperbrowser_job_id, "failed", org_id, error_message=error_msg)
            return {"status": "error", "error": error_msg}
        
    except Exception as e:
        error_msg = f"Error in check_and_process_batch_job: {str(e)}"
        logger.error(error_msg, exc_info=True)
        # Attempt to update status if job_id is available
        if 'hyperbrowser_job_id' in locals() and hyperbrowser_job_id:
            try:
                await update_markdown_extraction_status(hyperbrowser_job_id, "failed", org_id, error_message=error_msg)
            except Exception as status_update_err:
                logger.error(f"Failed to update job status during outer exception handling: {status_update_err}")
        return {"status": "error", "error": error_msg}


async def process_batch_results(hyperbrowser_job_id: str, batch_result, org_id: int) -> None:
    """
    Process the results of a completed batch scrape job.
    
    Args:
        hyperbrowser_job_id: Our internal hyperbrowser job ID
        batch_result: The batch scrape result from Hyperbrowser
        org_id: Organization ID (integer)
    """
    try:
        logger.info(f"Processing batch results for job {hyperbrowser_job_id}")
        
        # Check if we have data
        if not batch_result or not hasattr(batch_result, "data") or not batch_result.data:
            error_msg = f"No data returned from Hyperbrowser for batch job {hyperbrowser_job_id}"
            logger.error(error_msg)
            await update_markdown_extraction_status(hyperbrowser_job_id, "failed", org_id, error_message=error_msg)
            return
        
        results_data = batch_result.data
        total_results = len(results_data)
        successful_results = 0
        
        logger.info(f"Processing {total_results} URL results for job {hyperbrowser_job_id}")
        
        # Process each URL result
        for i, result in enumerate(results_data):
            try:
                # Access URL and status from the result object
                url = getattr(result, "url", "unknown")
                status = getattr(result, "status", "failed")
                error = getattr(result, "error", None)
                
                logger.debug(f"Processing result {i + 1}/{total_results}: {url} - status: {status}")
                
                if status == "completed" and not error:
                    # Extract data from successful result
                    markdown_text = getattr(result, "markdown", "")
                    metadata = getattr(result, "metadata", {})
                    links = getattr(result, "links", [])
                    html = getattr(result, "html", "")
                    screenshot = getattr(result, "screenshot", "")
                    
                    # Ensure we have meaningful content
                    if not markdown_text.strip():
                        logger.warning(f"Empty markdown content for URL {url}")
                        markdown_text = "No content extracted"
                    
                    logger.info(f"Successfully scraped URL {url} - Markdown: {len(markdown_text)} chars, Links: {len(links)}")
                    
                    # Save to database
                    await update_url_markdown_content(
                        hyperbrowser_job_id=hyperbrowser_job_id,
                        url=url,
                        markdown_text=markdown_text,
                        status="completed",
                        metadata=metadata,
                        links=links,
                        html=html,
                        screenshot=screenshot,
                        org_id=org_id
                    )
                    successful_results += 1
                    
                else:
                    # Handle failed result
                    error_message = error if error else f"Unknown error during scraping (status: {status})"
                    logger.warning(f"Failed to scrape URL {url}: {error_message}")
                    
                    await update_url_markdown_content(
                        hyperbrowser_job_id=hyperbrowser_job_id,
                        url=url,
                        markdown_text="",
                        status="failed",
                        metadata={"error": error_message},
                        links=[],
                        html="",
                        screenshot="",
                        org_id=org_id
                    )
                    
            except Exception as e:
                error_msg = f"Error processing individual result for URL {getattr(result, 'url', 'unknown')}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                
                # Try to save error result
                try:
                    await update_url_markdown_content(
                        hyperbrowser_job_id=hyperbrowser_job_id,
                        url=getattr(result, 'url', 'unknown'),
                        markdown_text="",
                        status="failed",
                        metadata={"error": error_msg},
                        links=[],
                        html="",
                        screenshot="",
                        org_id=org_id
                    )
                except Exception as save_error:
                    logger.error(f"Failed to save error result: {str(save_error)}")
        
        # Update job status to completed
        final_status = "completed" if successful_results > 0 else "failed"
        final_error_message = None if successful_results == total_results else f"{total_results - successful_results} of {total_results} URLs failed."
        await update_markdown_extraction_status(hyperbrowser_job_id, final_status, org_id, error_message=final_error_message)
        
        logger.info(f"Completed processing batch results for job {hyperbrowser_job_id}: "
                   f"{successful_results}/{total_results} successful, final status: {final_status}")
        
    except Exception as e:
        error_msg = f"Critical error processing batch results for job {hyperbrowser_job_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await update_markdown_extraction_status(hyperbrowser_job_id, "failed", org_id, error_message=error_msg)