"""
Dependency functions for API endpoints.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from uuid import UUID

from app.core.config import settings
from app.core.logging import logger
from app.core.database import get_user_organizations

# # OAuth2 scheme for token authentication
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

# Update the OAuth2 scheme to not auto_error (this will allow requests without a token)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token",
    auto_error=False  # This is the key change
)

# async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
#     """
#     Get the current user ID from the authentication token.
    
#     This is a simplified implementation that assumes the token is the user ID.
#     In a real implementation, this would validate the token and extract the user ID.
    
#     Args:
#         token: JWT token from the request
        
#     Returns:
#         User ID string
#     """
#     # In a real implementation, this would validate the token and extract the user ID
#     # For now, we'll just return the token as the user ID for simplicity
#     # This should be replaced with proper JWT validation
#     try:
#         # Here you would decode and validate the JWT token
#         # For now, we'll just return the token as the user ID
#         user_id = token
#         return user_id
#     except Exception as e:
#         logger.error(f"Error validating token: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Could not validate credentials",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """
    Simplified version that doesn't validate the token.
    FOR TESTING PURPOSES ONLY.
    """
    return "e40fc540-244c-4c31-9f4f-b23392ad1a86"  # Return a test user ID

async def validate_org_access(user_id: str, org_id: UUID) -> bool:
    """
    Validate that a user has access to an organization.
    
    Args:
        user_id: User ID to check
        org_id: Organization ID to check access for
        
    Returns:
        True if user has access, False otherwise
    """
    # Get user's organizations
    user_orgs = await get_user_organizations(user_id)
    
    # Check if the requested org_id is in the user's organizations
    return str(org_id) in user_orgs