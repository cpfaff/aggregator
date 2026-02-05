"""
JWT token generation and validation utilities.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings

# Create OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/tokens")

logger = logging.getLogger(__name__)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token with an expiration time and additional security claims.

    Args:
        data: The data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        str: The encoded JWT token
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update(
        {
            "exp": expire,
            "aud": settings.TOKEN_AUDIENCE,
            "jti": str(uuid.uuid4()),  # Add JWT ID for token revocation capability
            "iat": datetime.now(UTC),
        }
    )
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token with longer expiration.

    Args:
        data: The data to encode in the token

    Returns:
        str: The encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update(
        {
            "exp": expire,
            "aud": f"{settings.TOKEN_AUDIENCE}:refresh",
            "jti": str(uuid.uuid4()),
            "iat": datetime.now(UTC),
        }
    )
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, audience: str | None = None) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token to decode
        audience: Optional audience to verify

    Returns:
        Dict[str, Any]: The decoded token payload

    Raises:
        HTTPException: If token validation fails
    """
    try:
        # Use the specified audience or default to the application audience
        token_audience = audience or settings.TOKEN_AUDIENCE

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=token_audience,
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.JWTClaimsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims such as audience or issuer",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.PyJWTError as e:
        logger.warning(f"JWT token validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def get_token_data(token: str) -> dict[str, Any]:
    """
    Extract username and other data from a token.

    Args:
        token: The JWT token

    Returns:
        Dict[str, Any]: The token data

    Raises:
        HTTPException: If token validation fails or subject claim is missing
    """
    payload = decode_token(token)
    username = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"username": username, "payload": payload}
