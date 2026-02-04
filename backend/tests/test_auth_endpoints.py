"""Tests for authentication API endpoints.

Tests the HTTP contract: login success/failure, token refresh,
CSRF token generation. Mocks external dependencies at module boundary.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.v1.endpoints.auth import get_csrf_token, login, refresh_token

# ---------------------------------------------------------------------------
# GET /csrf-token
# ---------------------------------------------------------------------------


class TestGetCsrfToken:
    """Tests for the CSRF token endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.auth.csrf_protect")
    async def test_returns_csrf_token(self, mock_csrf):
        """Test that CSRF endpoint returns a token in the response body."""
        mock_csrf.generate_csrf_tokens.return_value = ("plain-token", "signed-token")
        mock_csrf.set_csrf_cookie = MagicMock()

        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()
        result = await get_csrf_token(request=mock_request)

        # Result is a JSONResponse, check it was constructed with token
        assert result is not None
        mock_csrf.generate_csrf_tokens.assert_called_once()
        mock_csrf.set_csrf_cookie.assert_called_once()


# ---------------------------------------------------------------------------
# POST /auth-token (login)
# ---------------------------------------------------------------------------


class TestLogin:
    """Tests for the login endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.auth.create_refresh_token")
    @patch("app.api.v1.endpoints.auth.create_access_token")
    @patch("app.api.v1.endpoints.auth.authenticate_user")
    async def test_successful_login_returns_tokens(
        self, mock_auth, mock_create_access, mock_create_refresh
    ):
        """Test that valid credentials return access and refresh tokens."""
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.is_global_admin = False
        mock_auth.return_value = mock_user

        mock_create_access.return_value = "access-token-123"
        mock_create_refresh.return_value = "refresh-token-456"

        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        mock_form = MagicMock()
        mock_form.username = "testuser"
        mock_form.password = "password123"

        mock_db = AsyncMock()

        result = await login(
            request=mock_request,
            form_data=mock_form,
            db=mock_db,
        )

        assert result["access_token"] == "access-token-123"
        assert result["refresh_token"] == "refresh-token-456"
        assert result["token_type"] == "bearer"
        assert "expires_in" in result

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.auth.authenticate_user")
    async def test_failed_login_returns_401(self, mock_auth):
        """Test that invalid credentials produce 401 with WWW-Authenticate header."""
        mock_auth.return_value = None

        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        mock_form = MagicMock()
        mock_form.username = "baduser"
        mock_form.password = "wrongpassword"

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await login(request=mock_request, form_data=mock_form, db=mock_db)

        assert exc_info.value.status_code == 401
        assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.auth.authenticate_user")
    async def test_login_handles_none_client(self, mock_auth):
        """Test that login handles request.client being None without crashing."""
        mock_auth.return_value = None

        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()
        mock_request.client = None

        mock_form = MagicMock()
        mock_form.username = "user"
        mock_form.password = "pass"

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await login(request=mock_request, form_data=mock_form, db=mock_db)

        # Should fail with 401 (bad credentials), not AttributeError
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# POST /refresh-token
# ---------------------------------------------------------------------------


class TestRefreshToken:
    """Tests for the token refresh endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.auth.create_refresh_token")
    @patch("app.api.v1.endpoints.auth.create_access_token")
    @patch("app.api.v1.endpoints.auth.get_user_model")
    @patch("app.api.v1.endpoints.auth.jwt.decode")
    async def test_valid_refresh_returns_new_tokens(
        self, mock_decode, mock_get_user, mock_create_access, mock_create_refresh
    ):
        """Test that a valid refresh token produces new access and refresh tokens."""
        mock_decode.return_value = {"sub": "testuser"}

        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_get_user.return_value = mock_user

        mock_create_access.return_value = "new-access-token"
        mock_create_refresh.return_value = "new-refresh-token"

        mock_db = AsyncMock()

        result = await refresh_token(refresh_token="valid-refresh-token", db=mock_db)

        assert result["access_token"] == "new-access-token"
        assert result["refresh_token"] == "new-refresh-token"
        assert result["token_type"] == "bearer"

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.auth.jwt.decode")
    async def test_invalid_token_returns_401(self, mock_decode):
        """Test that a malformed/expired token produces 401."""
        mock_decode.side_effect = jwt.PyJWTError("Invalid token")

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await refresh_token(refresh_token="bad-token", db=mock_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.auth.jwt.decode")
    async def test_token_missing_sub_claim_returns_401(self, mock_decode):
        """Test that a token without 'sub' claim produces 401."""
        mock_decode.return_value = {"exp": 999999}  # No 'sub' key

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await refresh_token(refresh_token="no-sub-token", db=mock_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.auth.get_user_model")
    @patch("app.api.v1.endpoints.auth.jwt.decode")
    async def test_user_not_found_returns_401(self, mock_decode, mock_get_user):
        """Test that a valid token for a deleted user produces 401."""
        mock_decode.return_value = {"sub": "deleteduser"}
        mock_get_user.return_value = None

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await refresh_token(refresh_token="valid-but-user-gone", db=mock_db)

        assert exc_info.value.status_code == 401
