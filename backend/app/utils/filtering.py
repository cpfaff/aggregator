"""Standardized filtering utilities for list endpoints."""

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class FilterError(Exception):
    """Raised when filter parsing or validation fails."""

    pass


class FilterOperator(StrEnum):
    """Supported filter operators."""

    EQ = "eq"  # Equal
    NE = "ne"  # Not equal
    GT = "gt"  # Greater than
    GTE = "gte"  # Greater than or equal
    LT = "lt"  # Less than
    LTE = "lte"  # Less than or equal
    LIKE = "like"  # SQL LIKE pattern
    IN = "in"  # In list


@dataclass
class FilterParam:
    """Parsed filter parameter."""

    field: str
    operator: FilterOperator
    value: Any


# Regex to parse filter[field] or filter[field][op]
FILTER_REGEX = re.compile(r"^filter\[(\w+)\](?:\[(\w+)\])?$")


def parse_filter_params(
    query_params: dict[str, str],
    allowed_fields: list[str],
    strict: bool = True,
) -> list[FilterParam]:
    """
    Parse filter query parameters into structured FilterParam objects.

    Args:
        query_params: Dict of query parameter key-value pairs
        allowed_fields: List of field names that can be filtered
        strict: If True, raise error for disallowed fields; if False, ignore them

    Returns:
        List of FilterParam objects

    Raises:
        FilterError: If field not allowed (strict mode) or operator invalid
    """
    filters = []

    for key, value in query_params.items():
        match = FILTER_REGEX.match(key)
        if not match:
            continue

        field, op_str = match.groups()

        # Check if field is allowed
        if field not in allowed_fields:
            if strict:
                raise FilterError(f"Field '{field}' is not filterable")
            continue

        # Parse operator (default to eq)
        if op_str is None:
            operator = FilterOperator.EQ
        else:
            try:
                operator = FilterOperator(op_str.lower())
            except ValueError as err:
                raise FilterError(
                    f"Invalid operator '{op_str}'. "
                    f"Valid operators: {[o.value for o in FilterOperator]}"
                ) from err

        # Handle IN operator (comma-separated values)
        if operator == FilterOperator.IN:
            value = [v.strip() for v in value.split(",")]

        filters.append(FilterParam(field=field, operator=operator, value=value))

    return filters
