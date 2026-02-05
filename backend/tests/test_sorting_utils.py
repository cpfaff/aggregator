"""Tests for standardized sorting utilities."""

import pytest

from app.utils.sorting import (
    SortDirection,
    SortError,
    parse_sort_params,
)


class TestParseSortParams:
    def test_parse_single_field_asc(self):
        """sort=name:asc → SortParam(name, asc)"""
        result = parse_sort_params("name:asc", allowed_fields=["name"])
        assert len(result) == 1
        assert result[0].field == "name"
        assert result[0].direction == SortDirection.ASC

    def test_parse_single_field_desc(self):
        """sort=name:desc → SortParam(name, desc)"""
        result = parse_sort_params("name:desc", allowed_fields=["name"])
        assert result[0].direction == SortDirection.DESC

    def test_parse_default_direction(self):
        """sort=name (no direction) → defaults to asc"""
        result = parse_sort_params("name", allowed_fields=["name"])
        assert result[0].direction == SortDirection.ASC

    def test_parse_multiple_fields(self):
        """sort=name:asc,created:desc → multiple SortParams"""
        result = parse_sort_params("name:asc,created:desc", allowed_fields=["name", "created"])
        assert len(result) == 2
        assert result[0].field == "name"
        assert result[1].field == "created"
        assert result[1].direction == SortDirection.DESC

    def test_parse_disallowed_field_strict(self):
        """Disallowed field raises SortError when strict=True."""
        with pytest.raises(SortError) as exc_info:
            parse_sort_params("password:asc", allowed_fields=["name"], strict=True)
        assert "password" in str(exc_info.value)

    def test_parse_disallowed_field_lenient(self):
        """Disallowed field ignored when strict=False."""
        result = parse_sort_params("password:asc", allowed_fields=["name"], strict=False)
        assert len(result) == 0

    def test_parse_invalid_direction(self):
        """Invalid direction raises SortError."""
        with pytest.raises(SortError) as exc_info:
            parse_sort_params("name:invalid", allowed_fields=["name"])
        assert "invalid" in str(exc_info.value).lower()

    def test_parse_empty_string(self):
        """Empty sort string returns empty list."""
        result = parse_sort_params("", allowed_fields=["name"])
        assert result == []

    def test_parse_none(self):
        """None returns empty list."""
        result = parse_sort_params(None, allowed_fields=["name"])
        assert result == []

    def test_direction_case_insensitive(self):
        """Directions are case insensitive (ASC, asc, Asc all work)."""
        result = parse_sort_params("name:ASC", allowed_fields=["name"])
        assert result[0].direction == SortDirection.ASC

    def test_parse_with_whitespace(self):
        """Whitespace is trimmed from field and direction."""
        result = parse_sort_params(" name : asc ", allowed_fields=["name"])
        assert result[0].field == "name"
        assert result[0].direction == SortDirection.ASC
