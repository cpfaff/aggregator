"""Tests for security/permissions module.

Tests the permission checking functions: normalize_provider_roles,
check_global_admin, check_provider_permission, authenticate_user,
get_current_user, get_current_user_sync, get_current_user_optional,
and require_admin.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException

from app.security.permissions import (
    authenticate_user,
    check_global_admin,
    check_provider_permission,
    get_current_user,
    get_current_user_optional,
    get_current_user_sync,
    normalize_provider_roles,
    require_admin,
)

# ---------------------------------------------------------------------------
# normalize_provider_roles
# ---------------------------------------------------------------------------


class TestNormalizeProviderRoles:
    """Tests for the normalize_provider_roles function."""

    def test_normalizes_dict_with_int_keys(self):
        """Test that integer keys are converted to strings."""
        result = normalize_provider_roles({1: "admin", 2: "curator"})
        assert result == {"1": "admin", "2": "curator"}

    def test_returns_empty_dict_for_none(self):
        """Test that None returns empty dict."""
        assert normalize_provider_roles(None) == {}

    def test_returns_empty_dict_for_empty_dict(self):
        """Test that empty dict returns empty dict."""
        assert normalize_provider_roles({}) == {}

    def test_returns_empty_dict_for_falsy_values(self):
        """Test that other falsy values return empty dict."""
        assert normalize_provider_roles("") == {}
        assert normalize_provider_roles(0) == {}
        assert normalize_provider_roles([]) == {}

    def test_returns_empty_dict_for_non_dict_truthy(self):
        """Test that non-dict truthy values return empty dict."""
        assert normalize_provider_roles("not a dict") == {}
        assert normalize_provider_roles([1, 2, 3]) == {}

    def test_string_keys_preserved(self):
        """Test that string keys are preserved as-is."""
        result = normalize_provider_roles({"1": "admin"})
        assert result == {"1": "admin"}

    def test_values_converted_to_strings(self):
        """Test that non-string values are converted to strings."""
        result = normalize_provider_roles({"1": 42})
        assert result == {"1": "42"}


# ---------------------------------------------------------------------------
# check_global_admin
# ---------------------------------------------------------------------------


class TestCheckGlobalAdmin:
    """Tests for the check_global_admin function."""

    def test_admin_passes_silently(self):
        """Test that global admin passes without exception."""
        user = MagicMock()
        user.is_global_admin = True
        check_global_admin(user)  # Should not raise

    def test_non_admin_raises_403(self):
        """Test that non-admin user raises 403."""
        user = MagicMock()
        user.is_global_admin = False

        with pytest.raises(HTTPException) as exc_info:
            check_global_admin(user)

        assert exc_info.value.status_code == 403
        assert "global admin" in exc_info.value.detail


# ---------------------------------------------------------------------------
# check_provider_permission
# ---------------------------------------------------------------------------


class TestCheckProviderPermission:
    """Tests for the check_provider_permission function."""

    def test_global_admin_always_passes(self):
        """Test that global admin bypasses all permission checks."""
        user = MagicMock()
        user.is_global_admin = True

        check_provider_permission(1, user, "read")
        check_provider_permission(1, user, "write")
        # Should not raise for any operation

    def test_user_with_role_can_read(self):
        """Test that user with any role on provider can read."""
        user = MagicMock()
        user.is_global_admin = False
        user.provider_roles = {"1": "viewer"}

        check_provider_permission(1, user, "read")  # Should not raise

    def test_user_without_role_gets_403_on_read(self):
        """Test that user with no role on provider gets 403."""
        user = MagicMock()
        user.is_global_admin = False
        user.provider_roles = {"2": "admin"}

        with pytest.raises(HTTPException) as exc_info:
            check_provider_permission(1, user, "read")

        assert exc_info.value.status_code == 403

    def test_admin_role_can_write(self):
        """Test that user with admin role can write."""
        user = MagicMock()
        user.is_global_admin = False
        user.provider_roles = {"1": "admin"}

        check_provider_permission(1, user, "write")  # Should not raise

    def test_curator_role_can_write(self):
        """Test that user with curator role can write."""
        user = MagicMock()
        user.is_global_admin = False
        user.provider_roles = {"1": "curator"}

        check_provider_permission(1, user, "write")  # Should not raise

    def test_viewer_role_cannot_write(self):
        """Test that user with viewer role cannot write."""
        user = MagicMock()
        user.is_global_admin = False
        user.provider_roles = {"1": "viewer"}

        with pytest.raises(HTTPException) as exc_info:
            check_provider_permission(1, user, "write")

        assert exc_info.value.status_code == 403
        assert "Write operation" in exc_info.value.detail

    def test_no_roles_at_all_gets_403(self):
        """Test that user with no roles at all gets 403."""
        user = MagicMock()
        user.is_global_admin = False
        user.provider_roles = None

        with pytest.raises(HTTPException) as exc_info:
            check_provider_permission(1, user, "read")

        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# authenticate_user
# ---------------------------------------------------------------------------


class TestAuthenticateUser:
    """Tests for the authenticate_user function."""

    @pytest.mark.asyncio
    @patch("app.security.permissions.verify_password")
    @patch("app.security.permissions.get_user_model")
    async def test_valid_credentials_returns_user(self, mock_get_user, mock_verify):
        """Test that valid username + password returns user model."""
        mock_user = MagicMock()
        mock_user.hashed_password = "hashed"
        mock_get_user.return_value = mock_user
        mock_verify.return_value = True

        result = await authenticate_user("testuser", "password123", AsyncMock())

        assert result is mock_user

    @pytest.mark.asyncio
    @patch("app.security.permissions.get_user_model")
    async def test_unknown_user_returns_none(self, mock_get_user):
        """Test that non-existent username returns None."""
        mock_get_user.return_value = None

        result = await authenticate_user("unknown", "password", AsyncMock())

        assert result is None

    @pytest.mark.asyncio
    @patch("app.security.permissions.verify_password")
    @patch("app.security.permissions.get_user_model")
    async def test_wrong_password_returns_none(self, mock_get_user, mock_verify):
        """Test that wrong password returns None."""
        mock_user = MagicMock()
        mock_user.hashed_password = "hashed"
        mock_get_user.return_value = mock_user
        mock_verify.return_value = False

        result = await authenticate_user("testuser", "wrongpass", AsyncMock())

        assert result is None


# ---------------------------------------------------------------------------
# get_current_user (async)
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    """Tests for the async get_current_user dependency."""

    @pytest.mark.asyncio
    @patch("app.security.permissions.get_user_model")
    @patch("app.security.permissions.decode_token")
    async def test_valid_token_returns_user(self, mock_decode, mock_get_user):
        """Test that valid JWT returns the associated user."""
        mock_decode.return_value = {"sub": "testuser"}
        mock_user = MagicMock()
        mock_get_user.return_value = mock_user

        result = await get_current_user(token="valid-token", db=AsyncMock())

        assert result is mock_user

    @pytest.mark.asyncio
    @patch("app.security.permissions.decode_token")
    async def test_token_without_sub_raises_401(self, mock_decode):
        """Test that token without 'sub' claim raises 401."""
        mock_decode.return_value = {"exp": 999999}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="no-sub-token", db=AsyncMock())

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch("app.security.permissions.decode_token")
    async def test_decode_failure_raises_401(self, mock_decode):
        """Test that token decode failure raises 401."""
        mock_decode.side_effect = ValueError("Invalid token")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="bad-token", db=AsyncMock())

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch("app.security.permissions.get_user_model")
    @patch("app.security.permissions.decode_token")
    async def test_user_not_found_raises_401(self, mock_decode, mock_get_user):
        """Test that valid token for deleted user raises 401."""
        mock_decode.return_value = {"sub": "deleteduser"}
        mock_get_user.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="valid-token", db=AsyncMock())

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch("app.security.permissions.decode_token")
    async def test_http_exception_from_decode_re_raised(self, mock_decode):
        """Test that HTTPException from decode_token is re-raised directly."""
        mock_decode.side_effect = HTTPException(status_code=401, detail="Token expired")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="expired-token", db=AsyncMock())

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Token expired"


# ---------------------------------------------------------------------------
# get_current_user_sync
# ---------------------------------------------------------------------------


class TestGetCurrentUserSync:
    """Tests for the sync get_current_user_sync dependency."""

    @patch("app.security.permissions.decode_token")
    def test_valid_token_returns_user(self, mock_decode):
        """Test that valid JWT returns user from sync DB query."""
        mock_decode.return_value = {"sub": "testuser"}
        mock_user = MagicMock()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = get_current_user_sync(token="valid-token", db=mock_db)

        assert result is mock_user

    @patch("app.security.permissions.decode_token")
    def test_token_without_sub_raises_401(self, mock_decode):
        """Test that token without 'sub' claim raises 401."""
        mock_decode.return_value = {"exp": 999999}

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_sync(token="no-sub-token", db=MagicMock())

        assert exc_info.value.status_code == 401

    @patch("app.security.permissions.decode_token")
    def test_user_not_found_raises_401(self, mock_decode):
        """Test that valid token for deleted user raises 401."""
        mock_decode.return_value = {"sub": "deleteduser"}
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_sync(token="valid-token", db=mock_db)

        assert exc_info.value.status_code == 401

    @patch("app.security.permissions.decode_token")
    def test_decode_failure_raises_401(self, mock_decode):
        """Test that token decode failure raises 401."""
        mock_decode.side_effect = ValueError("Invalid token")

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_sync(token="bad-token", db=MagicMock())

        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# get_current_user_optional
# ---------------------------------------------------------------------------


class TestGetCurrentUserOptional:
    """Tests for the get_current_user_optional dependency."""

    def test_no_token_returns_none(self):
        """Test that None token returns None (unauthenticated)."""
        result = get_current_user_optional(token=None, db=MagicMock())
        assert result is None

    @patch("app.security.permissions.decode_token")
    def test_valid_token_returns_user(self, mock_decode):
        """Test that valid token returns user."""
        mock_decode.return_value = {"sub": "testuser"}
        mock_user = MagicMock()
        mock_user.provider_roles = {"1": "admin"}

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = get_current_user_optional(token="valid-token", db=mock_db)

        assert result is mock_user

    @patch("app.security.permissions.decode_token")
    def test_token_without_sub_returns_none(self, mock_decode):
        """Test that token without 'sub' claim returns None."""
        mock_decode.return_value = {"exp": 999999}

        result = get_current_user_optional(token="no-sub-token", db=MagicMock())

        assert result is None

    @patch("app.security.permissions.decode_token")
    def test_user_not_found_returns_none(self, mock_decode):
        """Test that valid token for deleted user returns None."""
        mock_decode.return_value = {"sub": "deleteduser"}
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = get_current_user_optional(token="valid-token", db=mock_db)

        assert result is None

    @patch("app.security.permissions.decode_token")
    def test_invalid_token_returns_none(self, mock_decode):
        """Test that invalid token returns None instead of raising."""
        mock_decode.side_effect = jwt.PyJWTError("Invalid token")

        result = get_current_user_optional(token="bad-token", db=MagicMock())

        assert result is None

    @patch("app.security.permissions.decode_token")
    def test_user_without_provider_roles_not_normalized(self, mock_decode):
        """Test that user without provider_roles is not normalized."""
        mock_decode.return_value = {"sub": "testuser"}
        mock_user = MagicMock()
        mock_user.provider_roles = None

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = get_current_user_optional(token="valid-token", db=mock_db)

        assert result is mock_user


# ---------------------------------------------------------------------------
# require_admin
# ---------------------------------------------------------------------------


class TestRequireAdmin:
    """Tests for the require_admin dependency."""

    def test_admin_user_passes(self):
        """Test that admin user passes and is returned."""
        user = MagicMock()
        user.is_global_admin = True

        result = require_admin(current_user=user)

        assert result is user

    def test_non_admin_raises_403(self):
        """Test that non-admin user raises 403."""
        user = MagicMock()
        user.is_global_admin = False

        with pytest.raises(HTTPException) as exc_info:
            require_admin(current_user=user)

        assert exc_info.value.status_code == 403
        assert "Admin privileges" in exc_info.value.detail
