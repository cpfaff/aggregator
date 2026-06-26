"""Canonical time helper for the application (REQ-SH-NOW).

``utc_now()`` is THE single naive-UTC "now" for the codebase. It lives in this
dependency-free leaf module — importing nothing from ``app`` — so that ORM models
(``app.models.base``) can use it as a column default without importing the
heavier ``app.core.utils`` (which pulls in models and the cache, creating an
import cycle). ``app.core.utils`` re-exports it, so ``from app.core.utils import
utc_now`` keeps working as the canonical reference path.
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-naive datetime.

    Naive-UTC is the codebase convention for ``TIMESTAMP WITHOUT TIME ZONE``
    columns and for serialized statistics datetimes (REQ-SH-NOW-4, Q2). This is
    the single replacement for the deprecated ``datetime.utcnow()``.
    """
    return datetime.now(UTC).replace(tzinfo=None)
