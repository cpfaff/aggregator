"""Tests for cursor-based pagination utilities."""

import base64

import pytest
from pydantic import ValidationError

from app.schemas.pagination import PaginatedResponse, PaginationMeta, PaginationParams
from app.utils.pagination import CursorError, decode_cursor, encode_cursor


class TestEncodeCursor:
    """Tests for encode_cursor function."""

    def test_encode_cursor_with_single_id(self):
        """Encode dict with single id field to base64 string."""
        result = encode_cursor({"id": 123})
        assert isinstance(result, str)
        assert len(result) > 0
        # Should be URL-safe base64 (no + or /)
        assert "+" not in result
        assert "/" not in result

    def test_encode_cursor_with_multiple_fields(self):
        """Encode dict with multiple fields."""
        result = encode_cursor({"id": 123, "name": "test"})
        assert isinstance(result, str)

    def test_encode_cursor_preserves_order(self):
        """Same dict encoded twice gives same result (deterministic)."""
        dict1 = {"id": 123, "name": "test"}
        dict2 = {"name": "test", "id": 123}  # Different order
        assert encode_cursor(dict1) == encode_cursor(dict2)

    def test_encode_cursor_with_unicode(self):
        """Encode dict with Unicode values."""
        result = encode_cursor({"name": "Müller"})
        decoded = decode_cursor(result)
        assert decoded["name"] == "Müller"

    def test_encode_cursor_empty_dict(self):
        """Encode empty dict is valid."""
        result = encode_cursor({})
        assert isinstance(result, str)
        assert decode_cursor(result) == {}


class TestDecodeCursor:
    """Tests for decode_cursor function."""

    def test_decode_cursor_valid(self):
        """Decode valid cursor back to original dict."""
        original = {"id": 123, "name": "test"}
        encoded = encode_cursor(original)
        decoded = decode_cursor(encoded)
        assert decoded == original

    def test_decode_cursor_invalid_base64(self):
        """Invalid base64 raises CursorError."""
        with pytest.raises(CursorError) as exc_info:
            decode_cursor("not-valid-base64!!!")
        assert "Invalid cursor" in str(exc_info.value)

    def test_decode_cursor_invalid_json(self):
        """Valid base64 but invalid JSON raises CursorError."""
        invalid_json = base64.urlsafe_b64encode(b"not json").decode()
        with pytest.raises(CursorError) as exc_info:
            decode_cursor(invalid_json)
        assert "Invalid cursor" in str(exc_info.value)

    def test_decode_cursor_empty_string(self):
        """Empty string raises CursorError."""
        with pytest.raises(CursorError) as exc_info:
            decode_cursor("")
        assert "empty" in str(exc_info.value).lower()

    def test_decode_cursor_none(self):
        """None returns None (valid case: no cursor provided)."""
        result = decode_cursor(None)
        assert result is None


class TestPaginationParams:
    """Tests for PaginationParams schema."""

    def test_pagination_params_defaults(self):
        """Default values: limit=20, after=None, before=None."""
        params = PaginationParams()
        assert params.limit == 20
        assert params.after is None
        assert params.before is None

    def test_pagination_params_custom_limit(self):
        """Custom limit is accepted."""
        params = PaginationParams(limit=50)
        assert params.limit == 50

    def test_pagination_params_max_limit_enforced(self):
        """Limit > 100 is clamped to 100."""
        params = PaginationParams(limit=500)
        assert params.limit == 100

    def test_pagination_params_min_limit_enforced(self):
        """Limit < 1 raises ValidationError."""
        with pytest.raises(ValidationError):
            PaginationParams(limit=0)

    def test_pagination_params_negative_limit(self):
        """Negative limit raises ValidationError."""
        with pytest.raises(ValidationError):
            PaginationParams(limit=-5)

    def test_pagination_params_with_cursors(self):
        """After and before cursors accepted."""
        params = PaginationParams(after="abc123", before="xyz789")
        assert params.after == "abc123"
        assert params.before == "xyz789"


class TestPaginatedResponse:
    """Tests for PaginatedResponse schema."""

    def test_paginated_response_wraps_list(self):
        """Data list is wrapped with pagination metadata."""
        meta = PaginationMeta(
            limit=20,
            has_next=True,
            has_previous=False,
            next_cursor="abc123",
            total_count=100,
        )
        response = PaginatedResponse(data=[{"id": 1}, {"id": 2}], pagination=meta)
        assert len(response.data) == 2
        assert response.pagination.has_next is True
        assert response.pagination.total_count == 100

    def test_paginated_response_empty_list(self):
        """Empty data list is valid."""
        meta = PaginationMeta(limit=20, has_next=False, has_previous=False, total_count=0)
        response = PaginatedResponse(data=[], pagination=meta)
        assert response.data == []
        assert response.pagination.total_count == 0

    def test_paginated_response_with_cursors(self):
        """Cursors included when has_next/has_previous."""
        meta = PaginationMeta(
            limit=20,
            has_next=True,
            has_previous=True,
            next_cursor="next123",
            previous_cursor="prev456",
            total_count=100,
        )
        response = PaginatedResponse(data=[{"id": 1}], pagination=meta)
        assert response.pagination.next_cursor == "next123"
        assert response.pagination.previous_cursor == "prev456"

    def test_paginated_response_optional_total_count(self):
        """Total count can be None."""
        meta = PaginationMeta(
            limit=20,
            has_next=True,
            has_previous=False,
            total_count=None,
        )
        response = PaginatedResponse(data=[{"id": 1}], pagination=meta)
        assert response.pagination.total_count is None
