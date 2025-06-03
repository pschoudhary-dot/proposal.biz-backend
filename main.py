"""
Main application module for Proposal Biz.
"""
import os
import time
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import logger
from app.utils.jwt_handler import verify_jwt_cookie_middleware

# Set environment variable to prevent __pycache__ creation
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle application startup and shutdown events.
    """
    logger.info(f"Starting {settings.PROJECT_NAME} application")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME} application")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for extracting business data from websites",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add JWT cookie verification middleware
app.middleware("http")(verify_jwt_cookie_middleware)

# Add middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log all requests and responses.
    """
    start_time = time.time()

    # Get client IP and request details
    client_host = request.client.host if request.client else "unknown"
    request_path = request.url.path
    request_method = request.method

    logger.info(f"Request: {request_method} {request_path} from {client_host}")

    try:
        response = await call_next(request)

        # Log response details
        process_time = time.time() - start_time
        logger.info(
            f"Response: {request_method} {request_path} - Status: {response.status_code} - "
            f"Completed in {process_time:.4f}s"
        )

        return response
    except Exception as e:
        # Log any unhandled exceptions
        process_time = time.time() - start_time
        logger.error(
            f"Error processing {request_method} {request_path} - "
            f"Error: {str(e)} - Took {process_time:.4f}s"
        )

        # Return a JSON response for the error
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Please try again later."}
        )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to log all unhandled exceptions.
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."}
    )


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    """
    Root endpoint.
    """
    logger.info("Root endpoint called")
    return {
        "message": "Welcome to Proposal Biz API",
        "docs": "/docs",
    }

if __name__ == "__main__":
    logger.info("Starting development server")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
