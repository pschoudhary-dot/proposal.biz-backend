"""
API router for version 1 of the API.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import extraction, color_palette, markdown_scrapping_from_url, doc_to_markdown, vector_search, content_lib

api_router = APIRouter()

api_router.include_router(extraction.router, prefix="/extraction", tags=["extraction"])
api_router.include_router(color_palette.router, prefix="/color-palette", tags=["color-palette"])
api_router.include_router(markdown_scrapping_from_url.router, prefix="/markdown", tags=["markdown"])
api_router.include_router(doc_to_markdown.router, prefix="/document", tags=["document"])
api_router.include_router(vector_search.router, prefix="/vector", tags=["vector-search"])
api_router.include_router(content_lib.router, prefix="/content-lib", tags=["content-lib"])