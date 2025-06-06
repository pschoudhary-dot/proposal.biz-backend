"""
Dependency functions for API endpoints.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.database import get_default_org_id
from app.core.config import settings
from app.core.database import get_user_organizations

# Update the OAuth2 scheme to not auto_error (this will allow requests without a token)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token",
    auto_error=False  # This is the key change
)

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    """
    Simplified version that doesn't validate the token.
    FOR TESTING PURPOSES ONLY.
    """
    return 1  # Return a test user ID (integer)

async def validate_org_access(user_id: int, org_id: int) -> bool:
    """
    Validate that a user has access to an organization.
    
    Args:
        user_id: User ID to check (integer)
        org_id: Organization ID to check access for (integer)
        
    Returns:
        True if user has access, False otherwise
    """
    # Get user's organizations
    user_orgs = await get_user_organizations(user_id)
    
    # Check if the requested org_id is in the user's organizations
    return org_id in user_orgs

async def get_user_default_org(user_id: int) -> int:
    """
    Get the default organization ID for a user.
    
    Args:
        user_id: User ID (integer)
        
    Returns:
        Default organization ID
        
    Raises:
        HTTPException: If user has no organizations
    """
    org_id = await get_default_org_id(user_id)
    if not org_id:
        raise HTTPException(
            status_code=400,
            detail="User is not a member of any organization"
        )
    return org_id