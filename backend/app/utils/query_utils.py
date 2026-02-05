"""Utilities for applying filters and sorts to SQLAlchemy queries."""

from typing import Any, TypeVar

from sqlalchemy import Select, asc, desc
from sqlalchemy.orm import InstrumentedAttribute

from app.utils.filtering import FilterOperator, FilterParam
from app.utils.sorting import SortDirection, SortParam

T = TypeVar("T")


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
            query = query.filter(column.ilike(f"%{value}%"))
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
