"""Pydantic response schema + status enum for the harvest-success indicator.

The wire contract is **snake_case** (Pydantic v2, ``from_attributes`` so it
validates straight off a service-built object). ``HarvestStatus`` is a
:class:`~enum.StrEnum` (ruff UP042) whose member values are the snake_case wire
strings, so ``HarvestStatus.PARTIAL == "partial"`` round-trips cleanly.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class HarvestStatus(StrEnum):
    """Per-dataset harvest-success status.

    * ``STAGED`` — dataset is not harvest-ready; ES is never consulted.
    * ``NOT_IN_INDEX`` — harvest-ready but the dataset doc is absent (M = 0).
    * ``PARTIAL`` — present but fewer indexed units than expected (M < N).
    * ``IN_INDEX`` — present and M >= N, or N is unknown (M-only degrade).
    * ``UNKNOWN`` — Elasticsearch was unreachable for this query (honest signal,
      never a guessed presence).
    """

    STAGED = "staged"
    NOT_IN_INDEX = "not_in_index"
    PARTIAL = "partial"
    IN_INDEX = "in_index"
    UNKNOWN = "unknown"


class HarvestStatusResponse(BaseModel):
    """The per-dataset harvest-success response.

    ``units_in_index`` (M) and ``units_expected`` (N) are nullable: both are
    ``None`` on the ``staged`` / ``unknown`` soft outcomes, and ``units_expected``
    is ``None`` on the M-only degrade when N is unknown. ``index_checked_at`` is
    always a timezone-aware UTC datetime.
    """

    dataset_id: int
    is_harvest_ready: bool
    harvest_status: HarvestStatus
    units_in_index: int | None
    units_expected: int | None
    last_seen_in_index_at: datetime | None
    index_checked_at: datetime

    model_config = ConfigDict(from_attributes=True)
