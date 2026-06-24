"""Tests for JWT token generation and validation utilities."""

from datetime import timedelta

import jwt
import pytest
from fastapi import HTTPException

from app.security.token import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_data,
)


class TestCreateAccessToken:
    """Tests for create_access_token."""

    def test_creates_valid_token(self):
        """Test that a valid JWT is created with correct claims."""
        token = create_access_token(data={"sub": "testuser"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_subject(self):
        """Test that token contains the subject claim."""
        token = create_access_token(data={"sub": "testuser"})
        # Decode without verification to inspect claims
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["sub"] == "testuser"

    def test_token_has_expiration(self):
        """Test that token has an expiration claim."""
        token = create_access_token(data={"sub": "testuser"})
        payload = jwt.decode(token, options={"verify_signature": False})
        assert "exp" in payload

    def test_token_has_jti(self):
        """Test that token has a unique JWT ID."""
        token = create_access_token(data={"sub": "testuser"})
        payload = jwt.decode(token, options={"verify_signature": False})
        assert "jti" in payload

    def test_custom_expiration(self):
        """Test that custom expiration delta is applied."""
        token = create_access_token(data={"sub": "testuser"}, expires_delta=timedelta(hours=2))
        payload = jwt.decode(token, options={"verify_signature": False})
        assert "exp" in payload

    def test_tokens_have_unique_jti(self):
        """Test that each token gets a unique JTI."""
        token1 = create_access_token(data={"sub": "user"})
        token2 = create_access_token(data={"sub": "user"})
        payload1 = jwt.decode(token1, options={"verify_signature": False})
        payload2 = jwt.decode(token2, options={"verify_signature": False})
        assert payload1["jti"] != payload2["jti"]


class TestCreateRefreshToken:
    """Tests for create_refresh_token."""

    def test_creates_valid_token(self):
        """Test that a valid refresh token is created."""
        token = create_refresh_token(data={"sub": "testuser"})
        assert isinstance(token, str)

    def test_refresh_token_has_refresh_audience(self):
        """Test that refresh token has the :refresh audience suffix."""
        token = create_refresh_token(data={"sub": "testuser"})
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["aud"].endswith(":refresh")

    def test_refresh_token_has_jti(self):
        """Test that refresh token has a unique JWT ID."""
        token = create_refresh_token(data={"sub": "testuser"})
        payload = jwt.decode(token, options={"verify_signature": False})
        assert "jti" in payload


class TestDecodeToken:
    """Tests for decode_token."""

    def test_decodes_valid_token(self):
        """Test that a valid token is decoded correctly."""
        token = create_access_token(data={"sub": "testuser"})
        payload = decode_token(token)
        assert payload["sub"] == "testuser"

    def test_expired_token_raises_401(self):
        """Test that an expired token raises 401."""
        token = create_access_token(data={"sub": "testuser"}, expires_delta=timedelta(seconds=-1))
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail

    def test_invalid_audience_raises_401(self):
        """Wrong audience must map to a 401 HTTPException, not an AttributeError.

        Regression for B22: the handler caught the non-existent
        jwt.JWTClaimsError (python-jose name), which raised AttributeError on
        PyJWT for any non-expired token error instead of returning 401.
        """
        token = create_access_token(data={"sub": "testuser"})
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token, audience="wrong-audience")
        assert exc_info.value.status_code == 401

    def test_invalid_token_string_raises_401(self):
        """Garbage token string must map to a 401 HTTPException (regression B22)."""
        with pytest.raises(HTTPException) as exc_info:
            decode_token("not-a-valid-jwt")
        assert exc_info.value.status_code == 401

    def test_custom_audience_accepted(self):
        """Test that token with matching custom audience is accepted."""
        from app.core.config import settings

        token = create_refresh_token(data={"sub": "testuser"})
        payload = decode_token(token, audience=f"{settings.TOKEN_AUDIENCE}:refresh")
        assert payload["sub"] == "testuser"


class TestGetTokenData:
    """Tests for get_token_data."""

    def test_extracts_username(self):
        """Test that username is extracted from token."""
        token = create_access_token(data={"sub": "testuser"})
        data = get_token_data(token)
        assert data["username"] == "testuser"
        assert "payload" in data

    def test_missing_sub_claim_raises_401(self):
        """Test that token without sub claim raises 401."""
        # Create token without sub claim
        token = create_access_token(data={"role": "admin"})
        with pytest.raises(HTTPException) as exc_info:
            get_token_data(token)
        assert exc_info.value.status_code == 401
        assert "subject claim" in exc_info.value.detail
