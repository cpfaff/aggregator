"""Tests for user management API endpoints.

Tests the HTTP contract layer: correct service wiring, admin checks,
response models, status codes, and error handling.
Service logic is tested separately in tests/services/test_user_service.py.
"""

import importlib
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

# Patch the CSRF decorator before importing user endpoints.
# The @csrf_protect.validate_csrf decorator is an async method that,
# when used as a decorator, turns the endpoint into a coroutine object
# instead of a callable function. We make it a passthrough.
import app.api.deps as _deps

_deps.csrf_protect.validate_csrf = lambda fn: fn
if "app.api.v1.endpoints.users" in sys.modules:
    importlib.reload(sys.modules["app.api.v1.endpoints.users"])

from app.api.v1.endpoints.users import (  # noqa: E402
    add_provider_association,
    create_user,
    delete_user,
    get_user_endpoint,
    get_user_permissions,
    list_users,
    remove_provider_association,
    update_provider_association,
    update_user,
)


def _admin_user():
    """Create a mock admin user."""
    user = MagicMock()
    user.is_global_admin = True
    user.username = "admin"
    user.provider_roles = {"1": "admin"}
    return user


def _regular_user():
    """Create a mock non-admin user."""
    user = MagicMock()
    user.is_global_admin = False
    user.username = "regularuser"
    user.provider_roles = {}
    return user


# ---------------------------------------------------------------------------
# GET /me/permissions
# ---------------------------------------------------------------------------


class TestGetUserPermissions:
    """Tests for GET /me/permissions endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.users.UserService")
    async def test_returns_permissions_for_current_user(self, MockServiceClass):
        """Test happy path returns UserPermissions model."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_user_permissions.return_value = {
            "username": "testuser",
            "is_global_admin": True,
            "provider_roles": {"1": "admin"},
        }

        mock_user = _admin_user()
        mock_db = MagicMock()

        result = await get_user_permissions(current_user=mock_user, db=mock_db)

        assert result.username == "testuser"
        assert result.is_global_admin is True
        assert result.provider_roles == {"1": "admin"}
        MockServiceClass.assert_called_once_with(mock_db)
        mock_service.get_user_permissions.assert_called_once_with(mock_user)

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.users.UserService")
    async def test_returns_empty_roles_for_new_user(self, MockServiceClass):
        """Test that a user with no provider roles gets empty dict."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_user_permissions.return_value = {
            "username": "newuser",
            "is_global_admin": False,
            "provider_roles": {},
        }

        result = await get_user_permissions(current_user=_regular_user(), db=MagicMock())

        assert result.provider_roles == {}
        assert result.is_global_admin is False


# ---------------------------------------------------------------------------
# GET /users
# ---------------------------------------------------------------------------


class TestListUsers:
    """Tests for GET /users endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.users.UserService")
    async def test_admin_can_list_users(self, MockServiceClass):
        """Test that admin users can list all users."""
        from app.schemas.pagination import PaginationParams

        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.list_users = AsyncMock(return_value=MagicMock(data=[], pagination=MagicMock()))

        pagination = PaginationParams(limit=20)
        result = await list_users(
            current_user=_admin_user(),
            db=MagicMock(),
            pagination=pagination,
            filters=[],
            sorts=[],
        )

        assert result.data == []
        mock_service.list_users.assert_awaited_once_with(
            filters=[], sorts=[], pagination=pagination
        )

    @pytest.mark.asyncio
    async def test_non_admin_gets_403(self):
        """Test that non-admin users receive 403."""
        from app.schemas.pagination import PaginationParams

        with pytest.raises(HTTPException) as exc_info:
            await list_users(
                current_user=_regular_user(),
                db=MagicMock(),
                pagination=PaginationParams(),
                filters=[],
                sorts=[],
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.users.UserService")
    async def test_pagination_params_forwarded(self, MockServiceClass):
        """Test that pagination and filter/sort params are forwarded to service."""
        from app.schemas.pagination import PaginationParams
        from app.utils.filtering import FilterOperator, FilterParam
        from app.utils.sorting import SortDirection, SortParam

        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.list_users = AsyncMock(return_value=MagicMock(data=[], pagination=MagicMock()))

        pagination = PaginationParams(limit=50, after="cursor123")
        filters = [FilterParam(field="username", operator=FilterOperator.LIKE, value="test")]
        sorts = [SortParam(field="username", direction=SortDirection.ASC)]
        await list_users(
            current_user=_admin_user(),
            db=MagicMock(),
            pagination=pagination,
            filters=filters,
            sorts=sorts,
        )

        mock_service.list_users.assert_awaited_once_with(
            filters=filters, sorts=sorts, pagination=pagination
        )


# ---------------------------------------------------------------------------
# GET /users/{username}
# ---------------------------------------------------------------------------


class TestGetUserEndpoint:
    """Tests for GET /users/{username} endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.users.UserService")
    async def test_admin_can_get_user(self, MockServiceClass):
        """Test that admin can retrieve user by username."""
        mock_user_result = MagicMock()
        mock_user_result.username = "targetuser"
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_user_or_404 = AsyncMock(return_value=mock_user_result)

        result = await get_user_endpoint(
            username="targetuser", current_user=_admin_user(), db=MagicMock()
        )

        assert result.username == "targetuser"

    @pytest.mark.asyncio
    async def test_non_admin_gets_403(self):
        """Test that non-admin users receive 403."""
        with pytest.raises(HTTPException) as exc_info:
            await get_user_endpoint(
                username="anyuser", current_user=_regular_user(), db=MagicMock()
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.users.UserService")
    async def test_user_not_found_raises_404(self, MockServiceClass):
        """Test that missing user raises 404 from service."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_user_or_404 = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="User not found")
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_user_endpoint(username="missing", current_user=_admin_user(), db=MagicMock())

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# PUT /users/{username}
# ---------------------------------------------------------------------------


class TestUpdateUser:
    """Tests for PUT /users/{username} endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.users.UserService")
    async def test_admin_can_update_user(self, MockServiceClass):
        """Test that admin can update a user."""
        mock_updated = MagicMock()
        mock_updated.username = "targetuser"
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.update_user = AsyncMock(return_value=mock_updated)

        mock_user_update = MagicMock()
        mock_user_update.password = "newpass"
        mock_user_update.provider_roles = None
        mock_user_update.is_global_admin = None

        result = await update_user(
            username="targetuser",
            user=mock_user_update,
            current_user=_admin_user(),
            db=MagicMock(),
            old_password=None,
        )

        assert result.username == "targetuser"
        mock_service.update_user.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_non_admin_gets_403(self):
        """Test that non-admin users receive 403."""
        mock_user_update = MagicMock()
        mock_user_update.password = None
        mock_user_update.provider_roles = None
        mock_user_update.is_global_admin = None

        with pytest.raises(HTTPException) as exc_info:
            await update_user(
                username="anyuser",
                user=mock_user_update,
                current_user=_regular_user(),
                db=MagicMock(),
                old_password=None,
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.users.UserService")
    async def test_forwards_old_password_and_current_username(self, MockServiceClass):
        """Test that old_password and current_username are forwarded to service."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.update_user = AsyncMock(return_value=MagicMock())

        admin = _admin_user()
        mock_user_update = MagicMock()
        mock_user_update.password = "newpass"
        mock_user_update.provider_roles = {"2": "curator"}
        mock_user_update.is_global_admin = False

        await update_user(
            username="admin",
            user=mock_user_update,
            current_user=admin,
            db=MagicMock(),
            old_password="oldpass",
        )

        mock_service.update_user.assert_awaited_once_with(
            username="admin",
            password="newpass",
            provider_roles={"2": "curator"},
            is_global_admin=False,
            old_password="oldpass",
            current_username="admin",
        )


# ---------------------------------------------------------------------------
# POST /users
# ---------------------------------------------------------------------------


class TestCreateUser:
    """Tests for POST /users endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.users.UserService")
    async def test_admin_can_create_user(self, MockServiceClass):
        """Test that admin can create a new user."""
        mock_created = MagicMock()
        mock_created.username = "newuser"
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.create_user = AsyncMock(return_value=mock_created)

        mock_user_create = MagicMock()
        mock_user_create.username = "newuser"
        mock_user_create.password = "password123"
        mock_user_create.provider_roles = {}
        mock_user_create.is_global_admin = False

        result = await create_user(
            user=mock_user_create, current_user=_admin_user(), db=MagicMock()
        )

        assert result.username == "newuser"
        mock_service.create_user.assert_awaited_once_with(
            username="newuser",
            password="password123",
            provider_roles={},
            is_global_admin=False,
        )

    @pytest.mark.asyncio
    async def test_non_admin_gets_403(self):
        """Test that non-admin users receive 403."""
        mock_user_create = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await create_user(user=mock_user_create, current_user=_regular_user(), db=MagicMock())

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.users.UserService")
    async def test_duplicate_username_raises_400(self, MockServiceClass):
        """Test that duplicate username raises 400 from service."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.create_user = AsyncMock(
            side_effect=HTTPException(status_code=400, detail="Username already exists")
        )

        mock_user_create = MagicMock()
        mock_user_create.username = "existing"
        mock_user_create.password = "pass"
        mock_user_create.provider_roles = {}
        mock_user_create.is_global_admin = False

        with pytest.raises(HTTPException) as exc_info:
            await create_user(user=mock_user_create, current_user=_admin_user(), db=MagicMock())

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /users/{username}
# ---------------------------------------------------------------------------


class TestDeleteUser:
    """Tests for DELETE /users/{username} endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.users.UserService")
    async def test_admin_can_delete_user(self, MockServiceClass):
        """Test that admin can delete a user, returns None (204)."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.delete_user = AsyncMock(return_value=None)

        result = await delete_user(
            username="targetuser", current_user=_admin_user(), db=MagicMock()
        )

        assert result is None
        mock_service.delete_user.assert_awaited_once_with("targetuser")

    @pytest.mark.asyncio
    async def test_non_admin_gets_403(self):
        """Test that non-admin users receive 403."""
        with pytest.raises(HTTPException) as exc_info:
            await delete_user(username="anyuser", current_user=_regular_user(), db=MagicMock())

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.users.UserService")
    async def test_deleting_missing_user_raises_404(self, MockServiceClass):
        """Test that deleting a non-existent user raises 404."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.delete_user = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="User not found")
        )

        with pytest.raises(HTTPException) as exc_info:
            await delete_user(username="missing", current_user=_admin_user(), db=MagicMock())

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# POST /users/{username}/data-providers
# ---------------------------------------------------------------------------


class TestAddProviderAssociation:
    """Tests for POST /users/{username}/data-providers endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.users.UserService")
    async def test_admin_can_add_association(self, MockServiceClass):
        """Test that admin can add a provider association."""
        mock_updated = MagicMock()
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.add_provider_association = AsyncMock(return_value=mock_updated)

        mock_assoc = MagicMock()
        mock_assoc.provider_id = 5
        mock_assoc.role = "curator"

        result = await add_provider_association(
            username="testuser",
            association=mock_assoc,
            current_user=_admin_user(),
            db=MagicMock(),
        )

        assert result is mock_updated
        mock_service.add_provider_association.assert_awaited_once_with(
            username="testuser", provider_id=5, role="curator"
        )

    @pytest.mark.asyncio
    async def test_non_admin_gets_403(self):
        """Test that non-admin users receive 403."""
        with pytest.raises(HTTPException) as exc_info:
            await add_provider_association(
                username="anyuser",
                association=MagicMock(),
                current_user=_regular_user(),
                db=MagicMock(),
            )

        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# PUT /users/{username}/data-providers/{provider_id}
# ---------------------------------------------------------------------------


class TestUpdateProviderAssociation:
    """Tests for PUT /users/{username}/data-providers/{provider_id} endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.users.UserService")
    async def test_admin_can_update_association(self, MockServiceClass):
        """Test that admin can update a provider association."""
        mock_updated = MagicMock()
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.update_provider_association = AsyncMock(return_value=mock_updated)

        mock_assoc = MagicMock()
        mock_assoc.role = "admin"

        result = await update_provider_association(
            username="testuser",
            provider_id=5,
            association=mock_assoc,
            current_user=_admin_user(),
            db=MagicMock(),
        )

        assert result is mock_updated
        mock_service.update_provider_association.assert_awaited_once_with(
            username="testuser", provider_id=5, role="admin"
        )

    @pytest.mark.asyncio
    async def test_non_admin_gets_403(self):
        """Test that non-admin users receive 403."""
        with pytest.raises(HTTPException) as exc_info:
            await update_provider_association(
                username="anyuser",
                provider_id=1,
                association=MagicMock(),
                current_user=_regular_user(),
                db=MagicMock(),
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.users.UserService")
    async def test_association_not_found_raises_404(self, MockServiceClass):
        """Test that updating a non-existent association raises 404."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.update_provider_association = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="User or association not found")
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_provider_association(
                username="testuser",
                provider_id=999,
                association=MagicMock(),
                current_user=_admin_user(),
                db=MagicMock(),
            )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /users/{username}/data-providers/{provider_id}
# ---------------------------------------------------------------------------


class TestRemoveProviderAssociation:
    """Tests for DELETE /users/{username}/data-providers/{provider_id} endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.users.UserService")
    async def test_admin_can_remove_association(self, MockServiceClass):
        """Test that admin can remove a provider association."""
        mock_updated = MagicMock()
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.remove_provider_association = AsyncMock(return_value=mock_updated)

        result = await remove_provider_association(
            username="testuser",
            provider_id=5,
            current_user=_admin_user(),
            db=MagicMock(),
        )

        assert result is mock_updated
        mock_service.remove_provider_association.assert_awaited_once_with(
            username="testuser", provider_id=5
        )

    @pytest.mark.asyncio
    async def test_non_admin_gets_403(self):
        """Test that non-admin users receive 403."""
        with pytest.raises(HTTPException) as exc_info:
            await remove_provider_association(
                username="anyuser",
                provider_id=1,
                current_user=_regular_user(),
                db=MagicMock(),
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.users.UserService")
    async def test_association_not_found_raises_404(self, MockServiceClass):
        """Test that removing a non-existent association raises 404."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.remove_provider_association = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="User or association not found")
        )

        with pytest.raises(HTTPException) as exc_info:
            await remove_provider_association(
                username="testuser",
                provider_id=999,
                current_user=_admin_user(),
                db=MagicMock(),
            )

        assert exc_info.value.status_code == 404
