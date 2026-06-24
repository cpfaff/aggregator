"""
Unit tests for UserService.

Tests all user management operations with real database via testcontainers,
following TDD principles and covering edge cases.
"""

from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi import HTTPException

from app.models.user import UserModel
from app.services.user_service import UserService


@pytest_asyncio.fixture
async def user_service(db_session):
    """Create UserService instance with test database session."""
    return UserService(db_session)


@pytest_asyncio.fixture
async def sample_user(db_session):
    """Create a sample user for testing."""
    user = UserModel(
        username="testuser",
        hashed_password="hashed_password_123",
        provider_roles={"1": "admin", "2": "curator"},
        is_global_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def admin_user(db_session):
    """Create a global admin user for testing."""
    user = UserModel(
        username="admin",
        hashed_password="hashed_admin_password",
        provider_roles={},
        is_global_admin=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


# Test list_users with pagination
@pytest.mark.asyncio
async def test_list_users_empty(user_service):
    """Test listing users when none exist."""
    result = await user_service.list_users()
    assert result.data == []
    assert result.pagination.total_count == 0


@pytest.mark.asyncio
async def test_list_users_with_data(user_service, sample_user, admin_user):
    """Test listing users with multiple users."""
    result = await user_service.list_users()
    assert len(result.data) == 2
    usernames = [u.username for u in result.data]
    assert "testuser" in usernames
    assert "admin" in usernames
    assert result.pagination.total_count == 2


@pytest.mark.asyncio
async def test_list_users_pagination(user_service, db_session):
    """Test cursor-based pagination with limit."""
    from app.schemas.pagination import PaginationParams

    # Create 5 users
    for i in range(5):
        user = UserModel(
            username=f"user{i}",
            hashed_password=f"hash{i}",
            provider_roles={},
            is_global_admin=False,
        )
        db_session.add(user)
    await db_session.commit()

    # Test limit
    pagination = PaginationParams(limit=2)
    result = await user_service.list_users(pagination=pagination)
    assert len(result.data) == 2
    assert result.pagination.total_count == 5
    assert result.pagination.has_next is True
    assert result.pagination.next_cursor is not None

    # Test cursor navigation (fetch next page)
    next_pagination = PaginationParams(limit=2, after=result.pagination.next_cursor)
    result2 = await user_service.list_users(pagination=next_pagination)
    assert len(result2.data) == 2
    assert result2.pagination.has_previous is True


# Test get_user_by_username (found + not found)
@pytest.mark.asyncio
async def test_get_user_by_username_found(user_service, sample_user):
    """Test getting user by username when user exists."""
    user = await user_service.get_user_by_username("testuser")
    assert user is not None
    assert user.username == "testuser"
    assert user.hashed_password == "hashed_password_123"


@pytest.mark.asyncio
async def test_get_user_by_username_not_found(user_service):
    """Test getting user by username when user doesn't exist."""
    user = await user_service.get_user_by_username("nonexistent")
    assert user is None


# Test get_user_or_404 (raises HTTPException when not found)
@pytest.mark.asyncio
async def test_get_user_or_404_found(user_service, sample_user):
    """Test get_user_or_404 when user exists."""
    user = await user_service.get_user_or_404("testuser")
    assert user is not None
    assert user.username == "testuser"


@pytest.mark.asyncio
async def test_get_user_or_404_not_found(user_service):
    """Test get_user_or_404 raises 404 when user doesn't exist."""
    with pytest.raises(HTTPException) as exc_info:
        await user_service.get_user_or_404("nonexistent")
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"


# Test create_user (success + duplicate username)
@pytest.mark.asyncio
@patch("app.services.user_service.get_password_hash")
@patch("app.services.user_service.normalize_provider_roles")
@patch("app.services.user_service.invalidate_cache")
async def test_create_user_success(mock_invalidate, mock_normalize, mock_hash, user_service):
    """Test creating a new user successfully."""
    mock_hash.return_value = "hashed_password"
    mock_normalize.return_value = {"1": "admin"}

    user = await user_service.create_user(
        username="newuser",
        password="password123",
        provider_roles={"1": "admin"},
        is_global_admin=False,
    )

    assert user.username == "newuser"
    assert user.hashed_password == "hashed_password"
    assert user.provider_roles == {"1": "admin"}
    assert user.is_global_admin is False

    mock_hash.assert_called_once_with("password123")
    mock_normalize.assert_called_once_with({"1": "admin"})
    mock_invalidate.assert_called_once_with("users")


@pytest.mark.asyncio
async def test_create_user_duplicate_username(user_service, sample_user):
    """Test creating user with duplicate username raises 400."""
    with pytest.raises(HTTPException) as exc_info:
        await user_service.create_user(
            username="testuser",  # Already exists
            password="password123",
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Username already exists"


@pytest.mark.asyncio
async def test_create_user_race_duplicate_returns_400(user_service, sample_user):
    """A create that passes a stale existence check but hits the DB unique
    constraint must still surface a clean 400, not a 500 (B2 TOCTOU)."""
    from unittest.mock import AsyncMock

    # Simulate the TOCTOU window: the existence check misses the row.
    with patch.object(user_service, "get_user_by_username", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc_info:
            await user_service.create_user(username="testuser", password="password123")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Username already exists"


# Test update_user_password (own password with verification, admin changing other)
@pytest.mark.asyncio
@patch("app.services.user_service.verify_password")
@patch("app.services.user_service.get_password_hash")
async def test_update_user_password_own_success(mock_hash, mock_verify, user_service, sample_user):
    """Test user updating their own password successfully."""
    mock_verify.return_value = True
    mock_hash.return_value = "new_hashed_password"

    updated = await user_service.update_user_password(
        user=sample_user,
        new_password="newpass123",
        old_password="oldpass123",
        current_username="testuser",
    )

    assert updated.hashed_password == "new_hashed_password"
    mock_verify.assert_called_once_with("oldpass123", "hashed_password_123")
    mock_hash.assert_called_once_with("newpass123")


@pytest.mark.asyncio
@patch("app.services.user_service.verify_password")
async def test_update_user_password_own_wrong_old_password(mock_verify, user_service, sample_user):
    """Test updating own password with wrong old password fails."""
    mock_verify.return_value = False

    with pytest.raises(HTTPException) as exc_info:
        await user_service.update_user_password(
            user=sample_user,
            new_password="newpass123",
            old_password="wrongpass",
            current_username="testuser",
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Old password is incorrect"


@pytest.mark.asyncio
@patch("app.services.user_service.get_password_hash")
async def test_update_user_password_admin_changing_other(mock_hash, user_service, sample_user):
    """Test admin changing another user's password (no old password verification)."""
    mock_hash.return_value = "admin_set_password"

    updated = await user_service.update_user_password(
        user=sample_user,
        new_password="adminsetpass",
        current_username="admin",  # Different from sample_user.username
    )

    assert updated.hashed_password == "admin_set_password"
    mock_hash.assert_called_once_with("adminsetpass")


# Test update_user (password + roles + admin status)
@pytest.mark.asyncio
@patch("app.services.user_service.get_password_hash")
@patch("app.services.user_service.normalize_provider_roles")
@patch("app.services.user_service.invalidate_cache")
async def test_update_user_all_fields(
    mock_invalidate, mock_normalize, mock_hash, user_service, sample_user
):
    """Test updating user with all optional fields."""
    mock_hash.return_value = "new_hash"
    mock_normalize.return_value = {"3": "viewer"}

    updated = await user_service.update_user(
        username="testuser",
        password="newpassword",
        provider_roles={"3": "viewer"},
        is_global_admin=True,
    )

    assert updated.hashed_password == "new_hash"
    assert updated.provider_roles == {"3": "viewer"}
    assert updated.is_global_admin is True
    mock_invalidate.assert_called_once_with("user:testuser")


@pytest.mark.asyncio
@patch("app.services.user_service.normalize_provider_roles")
@patch("app.services.user_service.invalidate_cache")
async def test_update_user_only_roles(mock_invalidate, mock_normalize, user_service, sample_user):
    """Test updating only provider roles."""
    mock_normalize.return_value = {"5": "admin"}

    updated = await user_service.update_user(username="testuser", provider_roles={"5": "admin"})

    assert updated.provider_roles == {"5": "admin"}
    # Password should remain unchanged
    assert updated.hashed_password == "hashed_password_123"
    mock_invalidate.assert_called_once_with("user:testuser")


@pytest.mark.asyncio
async def test_update_user_not_found(user_service):
    """Test updating non-existent user raises 404."""
    with pytest.raises(HTTPException) as exc_info:
        await user_service.update_user(username="nonexistent", is_global_admin=True)
    assert exc_info.value.status_code == 404


# Test delete_user (success + not found)
@pytest.mark.asyncio
@patch("app.services.user_service.invalidate_cache")
async def test_delete_user_success(mock_invalidate, user_service, sample_user):
    """Test deleting a user successfully."""
    await user_service.delete_user("testuser")

    # Verify user is deleted
    user = await user_service.get_user_by_username("testuser")
    assert user is None

    # Verify cache invalidation
    assert mock_invalidate.call_count == 2
    mock_invalidate.assert_any_call("users")
    mock_invalidate.assert_any_call("user:testuser")


@pytest.mark.asyncio
async def test_delete_user_not_found(user_service):
    """Test deleting non-existent user raises 404."""
    with pytest.raises(HTTPException) as exc_info:
        await user_service.delete_user("nonexistent")
    assert exc_info.value.status_code == 404


# Test add_provider_association (new + update existing)
@pytest.mark.asyncio
@patch("app.services.user_service.normalize_provider_roles")
@patch("app.services.user_service.invalidate_cache")
async def test_add_provider_association_new(
    mock_invalidate, mock_normalize, user_service, sample_user
):
    """Test adding a new provider association."""
    mock_normalize.return_value = {"1": "admin", "2": "curator", "3": "viewer"}

    updated = await user_service.add_provider_association(
        username="testuser", provider_id=3, role="viewer"
    )

    assert updated.provider_roles == {"1": "admin", "2": "curator", "3": "viewer"}
    mock_invalidate.assert_called_once_with("user:testuser")


@pytest.mark.asyncio
@patch("app.services.user_service.normalize_provider_roles")
@patch("app.services.user_service.invalidate_cache")
async def test_add_provider_association_update_existing(
    mock_invalidate, mock_normalize, user_service, sample_user
):
    """Test updating an existing provider association."""
    # First call: get current roles
    # Second call: not called in this flow (roles dict modified directly)
    mock_normalize.side_effect = [
        {"1": "admin", "2": "curator"},  # Current roles
    ]

    updated = await user_service.add_provider_association(
        username="testuser",
        provider_id=1,
        role="superadmin",  # Update existing
    )

    assert updated.provider_roles["1"] == "superadmin"
    mock_invalidate.assert_called_once_with("user:testuser")


# Test update_provider_association (success + association not found)
@pytest.mark.asyncio
@patch("app.services.user_service.normalize_provider_roles")
@patch("app.services.user_service.invalidate_cache")
async def test_update_provider_association_success(
    mock_invalidate, mock_normalize, user_service, sample_user
):
    """Test updating an existing provider association."""
    mock_normalize.return_value = {"1": "admin", "2": "curator"}

    updated = await user_service.update_provider_association(
        username="testuser", provider_id=1, role="superadmin"
    )

    assert updated.provider_roles["1"] == "superadmin"
    assert mock_invalidate.call_count == 2
    mock_invalidate.assert_any_call("user:testuser")
    mock_invalidate.assert_any_call("provider:1")


@pytest.mark.asyncio
@patch("app.services.user_service.normalize_provider_roles")
async def test_update_provider_association_not_found(mock_normalize, user_service, sample_user):
    """Test updating non-existent provider association raises 404."""
    mock_normalize.return_value = {"1": "admin", "2": "curator"}

    with pytest.raises(HTTPException) as exc_info:
        await user_service.update_provider_association(
            username="testuser",
            provider_id=999,
            role="admin",  # Doesn't exist
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User or association not found"


# Test remove_provider_association (success + not found)
@pytest.mark.asyncio
@patch("app.services.user_service.normalize_provider_roles")
@patch("app.services.user_service.invalidate_cache")
async def test_remove_provider_association_success(
    mock_invalidate, mock_normalize, user_service, sample_user
):
    """Test removing a provider association."""
    mock_normalize.return_value = {"1": "admin", "2": "curator"}

    updated = await user_service.remove_provider_association(username="testuser", provider_id=1)

    assert "1" not in updated.provider_roles
    assert "2" in updated.provider_roles
    assert mock_invalidate.call_count == 2
    mock_invalidate.assert_any_call("user:testuser")
    mock_invalidate.assert_any_call("provider:1")


@pytest.mark.asyncio
@patch("app.services.user_service.normalize_provider_roles")
async def test_remove_provider_association_not_found(mock_normalize, user_service, sample_user):
    """Test removing non-existent provider association raises 404."""
    mock_normalize.return_value = {"1": "admin", "2": "curator"}

    with pytest.raises(HTTPException) as exc_info:
        await user_service.remove_provider_association(
            username="testuser",
            provider_id=999,  # Doesn't exist
        )
    assert exc_info.value.status_code == 404


# Test get_user_permissions (normalizes provider_roles)
@patch("app.services.user_service.normalize_provider_roles")
def test_get_user_permissions(mock_normalize, user_service, sample_user):
    """Test getting user permissions with normalized provider roles."""
    mock_normalize.return_value = {"1": "admin", "2": "curator"}

    permissions = user_service.get_user_permissions(sample_user)

    assert permissions == {
        "username": "testuser",
        "is_global_admin": False,
        "provider_roles": {"1": "admin", "2": "curator"},
    }
    mock_normalize.assert_called_once_with({"1": "admin", "2": "curator"})


@patch("app.services.user_service.normalize_provider_roles")
def test_get_user_permissions_global_admin(mock_normalize, user_service, admin_user):
    """Test getting permissions for global admin."""
    mock_normalize.return_value = {}

    permissions = user_service.get_user_permissions(admin_user)

    assert permissions == {
        "username": "admin",
        "is_global_admin": True,
        "provider_roles": {},
    }
