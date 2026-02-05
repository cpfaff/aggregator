"""Cursor-based pagination utilities."""

import base64
import json
from typing import Any


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
        return json.loads(json_str)
    except (ValueError, json.JSONDecodeError) as e:
        raise CursorError(f"Invalid cursor: {e}") from e
