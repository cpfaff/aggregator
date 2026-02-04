"""
User authentication and authorization permissions.
"""

import logging
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.db.session import get_db, get_sync_db
from app.models.user import UserModel
from app.security.password import verify_password
from app.security.token import decode_token, oauth2_scheme

logger = logging.getLogger(__name__)


def normalize_provider_roles(roles: Any) -> dict[str, str]:
    """
    Normalize provider roles to ensure they are in the correct format.

    Args:
        roles: Provider roles in various formats

    Returns:
        Dict[str, str]: Normalized provider roles
    """
    if not roles:
        return {}
    if isinstance(roles, dict):
        return {str(k): str(v) for k, v in roles.items()}
    return {}


async def get_user_model(username: str, db: AsyncSession) -> UserModel | None:
    """
    Retrieve a user model from the database by username.

    Args:
        username: The username to look up
        db: Database session

    Returns:
        Optional[UserModel]: The user if found, None otherwise
    """
    from sqlalchemy import select

    query = select(UserModel).where(UserModel.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()


def check_global_admin(current_user: UserModel) -> None:
    """
    Check if the current user has global admin privileges.

    Args:
        current_user: The current user

    Raises:
        HTTPException: If the user is not a global admin
    """
    if not current_user.is_global_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires global admin privileges",
        )


async def authenticate_user(username: str, password: str, db: AsyncSession) -> UserModel | None:
    """
    Authenticate a user with username and password.

    Args:
        username: The user's username
        password: The user's password
        db: Database session

    Returns:
        Optional[UserModel]: The user model if authentication successful, None otherwise
    """
    logger.info(f"Authenticating user: {username}")
    user_model = await get_user_model(username, db)
    if not user_model:
        logger.info("User not found")
        return None
    if not verify_password(password, user_model.hashed_password):
        logger.info("Invalid password")
        return None
    return user_model


def check_provider_permission(
    provider_id: int, current_user: UserModel, operation: str = "read"
) -> None:
    """
    Check if the current user has permission for a provider operation.

    Args:
        provider_id: The provider ID to check
        current_user: The current user
        operation: The operation type ("read" or "write")

    Raises:
        HTTPException: If the user doesn't have the required permission
    """
    if current_user.is_global_admin:
        return
    roles = normalize_provider_roles(current_user.provider_roles)
    role = roles.get(str(provider_id))
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted for this provider",
        )
    if operation == "write" and role not in ["admin", "curator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write operation requires provider admin or curator privileges",
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> UserModel:
    """
    Retrieve the current authenticated user from a JWT token.

    Args:
        token: The JWT token
        db: Database session

    Returns:
        UserModel: The authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except HTTPException:
        raise
    except Exception:
        raise credentials_exception from None

    user = await get_user_model(username, db)
    if user is None:
        logger.warning(f"User from token not found: {username}")
        raise credentials_exception

    return user


# Synchronous versions for compatibility with sync database sessions
def get_current_user_sync(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_sync_db)
) -> UserModel:
    """
    Synchronous version of get_current_user for use with sync database sessions.

    Args:
        token: The JWT token
        db: Database session

    Returns:
        UserModel: The authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except HTTPException:
        raise
    except Exception:
        raise credentials_exception from None

    user = db.query(UserModel).filter(UserModel.username == username).first()
    if user is None:
        logger.warning(f"User from token not found: {username}")
        raise credentials_exception

    return user


def get_current_user_optional(
    token: str | None = Depends(
        OAuth2PasswordBearer(tokenUrl="/api/v1/auth-token", auto_error=False)
    ),
    db: Session = Depends(get_sync_db),
) -> UserModel | None:
    """
    Get the current authenticated user or None if not authenticated.
    This is used for endpoints that have different behavior based on authentication status.

    Args:
        token: Optional JWT token from the request header
        db: Database session

    Returns:
        Optional[UserModel]: The authenticated user or None
    """
    if not token:
        return None

    try:
        # Decode and validate the token
        payload = decode_token(token)
        username = payload.get("sub")

        if not username:
            return None

        # Get the user from the database
        user = db.query(UserModel).filter(UserModel.username == username).first()

        if not user:
            return None

        # Update provider roles format if needed
        if hasattr(user, "provider_roles") and user.provider_roles:
            user.provider_roles = normalize_provider_roles(user.provider_roles)

        return user

    except (jwt.PyJWTError, HTTPException):
        # If token is invalid, return None instead of raising an exception
        return None


def require_admin(current_user: UserModel = Depends(get_current_user_sync)) -> UserModel:
    """
    Dependency that requires admin privileges.

    Args:
        current_user: The current user

    Returns:
        UserModel: The authenticated admin user

    Raises:
        HTTPException: If the user is not an admin
    """
    if not current_user.is_global_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user
