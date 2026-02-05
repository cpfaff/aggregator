"""Tests for standardized filtering utilities."""

import pytest

from app.utils.filtering import (
    FilterError,
    FilterOperator,
    parse_filter_params,
)


class TestParseFilterParams:
    def test_parse_simple_equality(self):
        """filter[name]=test → FilterParam(name, eq, test)"""
        result = parse_filter_params({"filter[name]": "test"}, allowed_fields=["name"])
        assert len(result) == 1
        assert result[0].field == "name"
        assert result[0].operator == FilterOperator.EQ
        assert result[0].value == "test"

    def test_parse_with_operator(self):
        """filter[age][gt]=18 → FilterParam(age, gt, 18)"""
        result = parse_filter_params({"filter[age][gt]": "18"}, allowed_fields=["age"])
        assert result[0].operator == FilterOperator.GT
        assert result[0].value == "18"

    def test_parse_multiple_filters(self):
        """Multiple filters parsed correctly."""
        result = parse_filter_params(
            {"filter[name]": "test", "filter[status]": "active"}, allowed_fields=["name", "status"]
        )
        assert len(result) == 2

    def test_parse_disallowed_field_strict(self):
        """Disallowed field raises FilterError when strict=True."""
        with pytest.raises(FilterError) as exc_info:
            parse_filter_params(
                {"filter[password]": "secret"}, allowed_fields=["name"], strict=True
            )
        assert "password" in str(exc_info.value)

    def test_parse_disallowed_field_lenient(self):
        """Disallowed field ignored when strict=False."""
        result = parse_filter_params(
            {"filter[password]": "secret"}, allowed_fields=["name"], strict=False
        )
        assert len(result) == 0

    def test_parse_invalid_operator(self):
        """Invalid operator raises FilterError."""
        with pytest.raises(FilterError) as exc_info:
            parse_filter_params({"filter[name][invalid]": "test"}, allowed_fields=["name"])
        assert "invalid" in str(exc_info.value).lower()

    def test_parse_empty_params(self):
        """No filter params returns empty list."""
        result = parse_filter_params({}, allowed_fields=["name"])
        assert result == []

    def test_parse_non_filter_params_ignored(self):
        """Non-filter query params are ignored."""
        result = parse_filter_params(
            {"limit": "20", "filter[name]": "test"}, allowed_fields=["name"]
        )
        assert len(result) == 1

    def test_parse_in_operator_multiple_values(self):
        """filter[status][in]=active,pending → list value."""
        result = parse_filter_params(
            {"filter[status][in]": "active,pending"}, allowed_fields=["status"]
        )
        assert result[0].operator == FilterOperator.IN
        assert result[0].value == ["active", "pending"]

    def test_parse_like_operator(self):
        """filter[name][like]=%test% → like pattern."""
        result = parse_filter_params({"filter[name][like]": "%test%"}, allowed_fields=["name"])
        assert result[0].operator == FilterOperator.LIKE

    def test_operator_case_insensitive(self):
        """Operators are case insensitive (GT, gt, Gt all work)."""
        result = parse_filter_params({"filter[age][GT]": "18"}, allowed_fields=["age"])
        assert result[0].operator == FilterOperator.GT
