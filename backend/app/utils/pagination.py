"""Cursor-based pagination utilities."""

import base64
import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, or_

from app.utils.sorting import SortDirection


class CursorError(Exception):
    """Raised when cursor encoding/decoding fails."""

    pass


def encode_cursor(values: dict[str, Any]) -> str:
    """
    Encode a dictionary to a URL-safe base64 cursor string.

    Args:
        values: Dictionary of cursor values (must be JSON-serializable)

    Returns:
        URL-safe base64 encoded string

    Example:
        >>> encode_cursor({"id": 123})
        'eyJpZCI6IDEyM30='
    """
    # sort_keys ensures deterministic encoding
    json_str = json.dumps(values, sort_keys=True)
    return base64.urlsafe_b64encode(json_str.encode()).decode()


def decode_cursor(cursor: str | None) -> dict[str, Any] | None:
    """
    Decode a cursor string back to a dictionary.

    Args:
        cursor: URL-safe base64 encoded cursor string, or None

    Returns:
        Decoded dictionary, or None if cursor was None

    Raises:
        CursorError: If cursor is invalid (empty string, bad base64, bad JSON)

    Example:
        >>> decode_cursor('eyJpZCI6IDEyM30=')
        {'id': 123}
    """
    if cursor is None:
        return None
    if not cursor:
        raise CursorError("Cursor cannot be empty string")
    try:
        json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
        decoded = json.loads(json_str)
    except (ValueError, json.JSONDecodeError) as e:
        raise CursorError(f"Invalid cursor: {e}") from e
    # The contract is dict | None; a bare JSON array/scalar/null would slip
    # through json.loads and crash callers doing decoded[...] / decoded.get(...).
    if not isinstance(decoded, dict):
        raise CursorError("Invalid cursor: expected a JSON object")
    return decoded


# ---------------------------------------------------------------------------
# Keyset (cursor) pagination
# ---------------------------------------------------------------------------
#
# Correct keyset pagination requires the WHERE boundary predicate to use the
# SAME ordered tuple of columns as the ORDER BY. The previous implementation
# keyed the cursor on id only while ordering by an arbitrary sort column then
# id, which skipped/duplicated rows under a custom sort (B8) and returned the
# first page instead of the preceding one for ``before`` cursors (B6/B7).


def _json_safe(value: Any) -> Any:
    """Make a cursor value JSON-serializable (datetimes -> ISO strings)."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _restore(value: Any, column) -> Any:
    """Restore a cursor value to the column's Python type for comparison."""
    if isinstance(value, str):
        try:
            python_type = column.type.python_type
        except (NotImplementedError, AttributeError):
            return value
        if python_type is datetime:
            return datetime.fromisoformat(value)
        if python_type is date:
            return date.fromisoformat(value)
    return value


def build_keyset_order(
    sorts, sort_field_map, id_column, id_key: str = "id", id_ascending: bool = True
):
    """Build the full ordering as ``[(key, column, ascending), ...]``.

    Custom sorts (validated against ``sort_field_map``) come first, then the
    unique ``id`` tiebreaker is always appended so the ordering is total.
    ``id_ascending`` sets the default id direction (e.g. False for
    most-recent-first listings).
    """
    order = []
    seen: set[str] = set()
    for sort in sorts or []:
        column = sort_field_map.get(sort.field)
        if column is not None and sort.field not in seen:
            order.append((sort.field, column, sort.direction == SortDirection.ASC))
            seen.add(sort.field)
    if id_key not in seen:
        order.append((id_key, id_column, id_ascending))
    return order


def _keyset_predicate(order, cursor: dict, *, reverse: bool):
    """Lexicographic "strictly past the cursor" predicate for ``order``.

    ``reverse`` flips every direction (used for ``before`` navigation).
    Returns ``None`` if the cursor lacks a required key.
    """
    or_terms = []
    for i, (key, column, ascending) in enumerate(order):
        if key not in cursor:
            return None
        and_terms = []
        for j in range(i):
            prev_key, prev_col, _ = order[j]
            and_terms.append(prev_col == _restore(cursor[prev_key], prev_col))
        effective_asc = ascending if not reverse else not ascending
        boundary = _restore(cursor[key], column)
        and_terms.append(column > boundary if effective_asc else column < boundary)
        or_terms.append(and_(*and_terms))
    return or_(*or_terms)


async def paginate_keyset(db, base_query, order, pagination, options=None):
    """Run keyset pagination over ``base_query``.

    ``order`` is ``[(key, column, ascending), ...]`` ending with a unique
    tiebreaker (see :func:`build_keyset_order`). Returns
    ``(items, next_cursor, previous_cursor)``.
    """
    going_back = bool(pagination.before) and not pagination.after

    cursor = None
    if pagination.after:
        cursor = decode_cursor(pagination.after)
    elif pagination.before:
        cursor = decode_cursor(pagination.before)

    query = base_query
    if cursor:
        predicate = _keyset_predicate(order, cursor, reverse=going_back)
        if predicate is not None:
            query = query.filter(predicate)

    order_by = []
    for _key, column, ascending in order:
        effective_asc = ascending if not going_back else not ascending
        order_by.append(column.asc() if effective_asc else column.desc())
    query = query.order_by(*order_by)

    if options:
        query = query.options(*options)

    result = await db.execute(query.limit(pagination.limit + 1))
    items = list(result.scalars().all())
    has_more = len(items) > pagination.limit
    if has_more:
        items = items[: pagination.limit]
    if going_back:
        items.reverse()  # restore forward display order

    def _cursor_of(item) -> str:
        return encode_cursor({key: _json_safe(getattr(item, col.key)) for key, col, _ in order})

    next_cursor = None
    previous_cursor = None
    if items:
        if going_back:
            # Paged backward: more rows exist before iff has_more; the page we
            # came from is always after, so a next cursor always exists here.
            previous_cursor = _cursor_of(items[0]) if has_more else None
            next_cursor = _cursor_of(items[-1])
        else:
            next_cursor = _cursor_of(items[-1]) if has_more else None
            previous_cursor = _cursor_of(items[0]) if pagination.after else None

    return items, next_cursor, previous_cursor
