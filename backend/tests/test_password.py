"""Tests for password hashing and verification utilities."""

from app.security.password import get_password_hash, verify_password


class TestGetPasswordHash:
    """Tests for get_password_hash."""

    def test_returns_hashed_string(self):
        """Test that a bcrypt hash is returned."""
        hashed = get_password_hash("password123")
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")

    def test_different_passwords_produce_different_hashes(self):
        """Test that different inputs produce different hashes."""
        hash1 = get_password_hash("password1")
        hash2 = get_password_hash("password2")
        assert hash1 != hash2

    def test_same_password_produces_different_hashes(self):
        """Test that same password with different salts produces different hashes."""
        hash1 = get_password_hash("same_password")
        hash2 = get_password_hash("same_password")
        assert hash1 != hash2  # Different salts

    def test_empty_password_returns_empty_string(self):
        """Test that empty password returns empty string."""
        assert get_password_hash("") == ""

    def test_none_returns_empty_string(self):
        """Test that None/falsy input returns empty string."""
        assert get_password_hash(None) == ""


class TestVerifyPassword:
    """Tests for verify_password."""

    def test_correct_password_returns_true(self):
        """Test that correct password verifies successfully."""
        hashed = get_password_hash("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_wrong_password_returns_false(self):
        """Test that wrong password fails verification."""
        hashed = get_password_hash("mypassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_invalid_hash_returns_false(self):
        """Test that invalid hash format returns False (doesn't crash)."""
        assert verify_password("password", "not-a-valid-hash") is False

    def test_empty_password_against_hash_returns_false(self):
        """Test that empty password against a real hash returns False."""
        hashed = get_password_hash("realpassword")
        assert verify_password("", hashed) is False
