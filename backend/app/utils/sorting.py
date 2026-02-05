"""Standardized sorting utilities for list endpoints."""

from dataclasses import dataclass
from enum import StrEnum


class SortError(Exception):
    """Raised when sort parsing or validation fails."""

    pass


class SortDirection(StrEnum):
    """Supported sort directions."""

    ASC = "asc"
    DESC = "desc"


@dataclass
class SortParam:
    """Parsed sort parameter."""

    field: str
    direction: SortDirection


def parse_sort_params(
    sort_string: str | None,
    allowed_fields: list[str],
    strict: bool = True,
) -> list[SortParam]:
    """
    Parse sort query parameter into structured SortParam objects.

    Args:
        sort_string: Comma-separated sort specs (e.g., "name:asc,created:desc")
        allowed_fields: List of field names that can be sorted
        strict: If True, raise error for disallowed fields; if False, ignore them

    Returns:
        List of SortParam objects

    Raises:
        SortError: If field not allowed (strict mode) or direction invalid
    """
    if not sort_string:
        return []

    sorts = []
    for spec in sort_string.split(","):
        spec = spec.strip()
        if not spec:
            continue

        # Parse field and optional direction
        if ":" in spec:
            field, dir_str = spec.split(":", 1)
        else:
            field, dir_str = spec, "asc"

        field = field.strip()
        dir_str = dir_str.strip().lower()

        # Check if field is allowed
        if field not in allowed_fields:
            if strict:
                raise SortError(f"Field '{field}' is not sortable")
            continue

        # Parse direction
        try:
            direction = SortDirection(dir_str)
        except ValueError:
            raise SortError(f"Invalid direction '{dir_str}'. Valid directions: asc, desc") from None

        sorts.append(SortParam(field=field, direction=direction))

    return sorts
