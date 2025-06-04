"""
this for the future handling of the jwt token
"""

# app/utils/jwt_handler.py
import jwt
from fastapi import Request
from starlette.responses import JSONResponse
from app.core.logging import logger
from dotenv import load_dotenv
import os
load_dotenv()

# JWT configuration
JWT_SECRET_KEY = os.getenv("AUTH_SECRET", "FTYDRSJRYS")  # Set your actual secret key in settings
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "access_token")

async def verify_jwt_cookie_middleware(request: Request, call_next):
    """
    Middleware function that verifies JWT tokens from cookies or Authorization header.
    
    This middleware:
    1. Extracts the JWT token from cookies or Authorization header
    2. Verifies it using PyJWT
    3. Sets user information in request state
    4. Returns 401 if token is invalid
    
    Args:
        request: FastAPI request object
        call_next: Function that will call the next middleware or route handler
        
    Returns:
        Response from the next middleware or route handler
    """
    # Define public endpoints that don't require authentication
    public_endpoints = [
        # User endpoints
        "/api/v1/usr/users",
        "/api/v1/usr/login",
        "/api/v1/usr/register",
        # Documentation
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/openapi.json",  # Add the actual OpenAPI endpoint
        "/",  # Root endpoint
    ]
    
    # Skip authentication for public endpoints
    for endpoint in public_endpoints:
        if request.url.path.startswith(endpoint):
            return await call_next(request)
    
    # Check for extraction status endpoint pattern (public)
    if "/api/v1/extraction/extract/" in request.url.path and request.url.path.endswith("/status"):
        return await call_next(request)
    
    # Try to get token from Authorization header first
    auth_header = request.headers.get("Authorization")
    token = None
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
    else:
        # If not in header, try to get from cookies
        token = request.cookies.get(JWT_COOKIE_NAME)
    
    # If no token is provided from either source
    if not token:
        return JSONResponse(status_code=401, content={"detail": "No authentication token provided"})
        
    try:
        # Verify the token with PyJWT
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Set user information in request state for use in route handlers
        request.state.user = payload
        request.state.user_id = payload.get("sub")
        
        # Continue with the request
        return await call_next(request)
        
    except jwt.ExpiredSignatureError:
        logger.warning(f"Expired JWT token in cookie")
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication credentials expired"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as e:
        logger.error(f"Invalid JWT token in cookie: {str(e)}")
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid authentication credentials"},
            headers={"WWW-Authenticate": "Bearer"},
        )







#         # In your config
# DYNAMIC_PUBLIC_ROUTES = {
#     "/api/v1/items/{item_id}": ["GET"],  # Only GET is public
#     "/api/v1/products/{product_id}": ["GET", "POST"]  # GET and POST are public
# }

# # In middleware
# from fastapi.routing import get_route_handler

# async def verify_jwt_cookie_middleware(request: Request, call_next):
#     # Get the actual route path
#     route = request.scope.get("route")
#     if route:
#         path = route.path
#         method = request.method
        
#         # Check if path matches any dynamic public route
#         for route_pattern, methods in settings.DYNAMIC_PUBLIC_ROUTES.items():
#             if route_pattern.split('{')[0] in path and method in methods:
#                 return await call_next(request)
    
#     # Rest of your JWT verification logic