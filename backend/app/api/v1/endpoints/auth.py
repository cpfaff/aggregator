"""
Authentication API endpoints.

This module contains endpoints for CSRF token generation, user authentication,
and token refresh functionality.
"""

import logging
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import csrf_protect, limiter
from app.core.config import settings
from app.db import get_db
from app.schemas import TokenResponse
from app.security import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_user_model,
)

logger = logging.getLogger("api")

router = APIRouter()


@router.get("/csrf-token", summary="Get CSRF token")
@limiter.limit(settings.CSRF_TOKEN_RATE_LIMIT)
async def get_csrf_token(request: Request):
    """
    Retrieve a CSRF token to protect against cross-site request forgery in subsequent requests.
    Returns a JSON object with the token.

    This endpoint is rate-limited to prevent abuse.
    """
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = JSONResponse(content={"csrf_token": csrf_token})
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@router.post("/auth-token", response_model=TokenResponse)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate a user and return JWT access and refresh tokens.

    - **username**: The user's username
    - **password**: The user's password

    Returns a JSON object containing the access token, refresh token, token type, and expiration time.
    """
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        logger.warning(
            f"Failed login attempt",
            extra={
                "username": form_data.username,
                "ip_address": request.client.host if request.client else None,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.username})

    logger.info(
        f"User authenticated",
        extra={
            "username": user.username,
            "is_admin": user.is_global_admin,
            "ip_address": request.client.host if request.client else None,
        },
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(refresh_token: str = Body(...), db: AsyncSession = Depends(get_db)):
    """
    Get a new access token using a refresh token.

    - **refresh_token**: A valid refresh token previously issued

    Returns a new access token and refresh token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=f"{settings.TOKEN_AUDIENCE}:refresh",
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception from None

    user = await get_user_model(username, db)
    if user is None:
        raise credentials_exception

    # Create new tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    new_refresh_token = create_refresh_token(data={"sub": user.username})

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
