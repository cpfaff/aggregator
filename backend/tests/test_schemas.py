"""Tests for Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from app.schemas.user import User, UserCreate, UserPermissions, UserUpdate


class TestUserSchema:
    """Tests for the User response schema."""

    def test_valid_user(self):
        """Test creating a valid User."""
        user = User(username="alice", provider_roles={"1": "admin"}, is_global_admin=True)
        assert user.username == "alice"

    def test_trims_whitespace_from_username(self):
        """Test that leading/trailing whitespace is trimmed."""
        user = User(username="  alice  ", provider_roles={})
        assert user.username == "alice"

    def test_from_attributes(self):
        """Test that from_attributes mode works with ORM objects."""

        class FakeUser:
            username = "bob"
            provider_roles = {"2": "curator"}
            is_global_admin = False
            last_login = None

        user = User.model_validate(FakeUser())
        assert user.username == "bob"


class TestUserCreateSchema:
    """Tests for the UserCreate schema."""

    def test_valid_create(self):
        """Test creating a valid UserCreate."""
        uc = UserCreate(username="newuser", password="longpassword123")
        assert uc.username == "newuser"

    def test_short_password_rejected(self):
        """Test that password below minimum length is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="newuser", password="ab")
        assert "Password must be at least" in str(exc_info.value)

    def test_trims_whitespace(self):
        """Test that whitespace is trimmed from username and password."""
        uc = UserCreate(username="  alice  ", password="  longpassword123  ")
        assert uc.username == "alice"
        assert uc.password == "longpassword123"

    def test_default_admin_false(self):
        """Test that is_global_admin defaults to False."""
        uc = UserCreate(username="user", password="longpassword123")
        assert uc.is_global_admin is False


class TestUserUpdateSchema:
    """Tests for the UserUpdate schema."""

    def test_all_fields_optional(self):
        """Test that all fields can be None."""
        uu = UserUpdate()
        assert uu.password is None
        assert uu.provider_roles is None
        assert uu.is_global_admin is None

    def test_short_password_rejected(self):
        """Test that short password is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UserUpdate(password="ab")
        assert "Password must be at least" in str(exc_info.value)

    def test_none_password_accepted(self):
        """Test that None password passes validation."""
        uu = UserUpdate(password=None)
        assert uu.password is None

    def test_trims_whitespace_from_password(self):
        """Test that whitespace is trimmed from password."""
        uu = UserUpdate(password="  longpassword123  ")
        assert uu.password == "longpassword123"


class TestUserPermissionsSchema:
    """Tests for the UserPermissions schema."""

    def test_valid_permissions(self):
        """Test creating valid UserPermissions."""
        up = UserPermissions(username="alice", is_global_admin=True, provider_roles={"1": "admin"})
        assert up.username == "alice"

    def test_trims_whitespace(self):
        """Test that whitespace is trimmed from username."""
        up = UserPermissions(username="  alice  ", is_global_admin=False, provider_roles={})
        assert up.username == "alice"
