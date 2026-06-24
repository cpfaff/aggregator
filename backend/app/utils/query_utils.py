"""Utilities for applying filters and sorts to SQLAlchemy queries."""

from typing import Any, TypeVar

from sqlalchemy import Select, asc, desc
from sqlalchemy.orm import InstrumentedAttribute

from app.utils.filtering import FilterError, FilterOperator, FilterParam
from app.utils.sorting import SortDirection, SortParam

T = TypeVar("T")

_TRUE_STRINGS = {"true", "1", "yes", "t"}
_FALSE_STRINGS = {"false", "0", "no", "f"}


def _coerce_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in _TRUE_STRINGS:
        return True
    if normalized in _FALSE_STRINGS:
        return False
    raise ValueError(f"not a boolean: {value!r}")


def _coerce_scalar(column: InstrumentedAttribute, value: Any) -> Any:
    """Coerce one raw string filter value to the column's Python type (B18).

    Filter values arrive as strings from the query string and were compared
    against typed columns verbatim, so a non-castable value (provider_id=abc,
    is_global_admin=maybe) raised a DB DataError -> 500. Coerce here and raise
    FilterError (mapped to 400) on bad input instead.
    """
    if not isinstance(value, str):
        return value
    try:
        python_type = column.type.python_type
    except (NotImplementedError, AttributeError):
        return value
    if python_type is str:
        return value
    try:
        if python_type is bool:
            return _coerce_bool(value)
        return python_type(value)
    except (ValueError, TypeError) as exc:
        raise FilterError(
            f"Invalid filter value '{value}': expected {python_type.__name__}"
        ) from exc


def _coerce_value(column: InstrumentedAttribute, value: Any) -> Any:
    if isinstance(value, list):
        return [_coerce_scalar(column, item) for item in value]
    return _coerce_scalar(column, value)


def apply_filters(
    query: Select[tuple[T]],
    filters: list[FilterParam],
    field_map: dict[str, InstrumentedAttribute],
) -> Select[tuple[T]]:
    """
    Apply filter parameters to a SQLAlchemy query.

    Args:
        query: The SQLAlchemy select query
        filters: List of FilterParam objects
        field_map: Mapping from filter field names to model attributes

    Returns:
        Modified query with filters applied
    """
    for f in filters:
        if f.field not in field_map:
            continue

        column = field_map[f.field]
        query = _apply_single_filter(query, column, f.operator, f.value)

    return query


def _apply_single_filter(
    query: Select[tuple[T]],
    column: InstrumentedAttribute,
    operator: FilterOperator,
    value: Any,
) -> Select[tuple[T]]:
    """Apply a single filter condition to the query."""
    # Coerce the raw string value to the column's type for value comparisons.
    # LIKE keeps the raw string (it builds a text pattern).
    if operator is not FilterOperator.LIKE:
        value = _coerce_value(column, value)
    match operator:
        case FilterOperator.EQ:
            query = query.filter(column == value)
        case FilterOperator.NE:
            query = query.filter(column != value)
        case FilterOperator.GT:
            query = query.filter(column > value)
        case FilterOperator.GTE:
            query = query.filter(column >= value)
        case FilterOperator.LT:
            query = query.filter(column < value)
        case FilterOperator.LTE:
            query = query.filter(column <= value)
        case FilterOperator.LIKE:
            # Escape LIKE wildcards so user-supplied % and _ match literally
            # instead of acting as wildcards (B17). Escape the backslash first.
            escaped = str(value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.filter(column.ilike(f"%{escaped}%", escape="\\"))
        case FilterOperator.IN:
            if isinstance(value, list):
                query = query.filter(column.in_(value))
            else:
                query = query.filter(column == value)

    return query


def apply_sorts(
    query: Select[tuple[T]],
    sorts: list[SortParam],
    field_map: dict[str, InstrumentedAttribute],
    default_sort: InstrumentedAttribute | None = None,
) -> Select[tuple[T]]:
    """
    Apply sort parameters to a SQLAlchemy query.

    Args:
        query: The SQLAlchemy select query
        sorts: List of SortParam objects
        field_map: Mapping from sort field names to model attributes
        default_sort: Default sort column if no sorts provided

    Returns:
        Modified query with sorting applied
    """
    if not sorts and default_sort is not None:
        return query.order_by(asc(default_sort))

    for s in sorts:
        if s.field not in field_map:
            continue

        column = field_map[s.field]
        if s.direction == SortDirection.ASC:
            query = query.order_by(asc(column))
        else:
            query = query.order_by(desc(column))

    return query
