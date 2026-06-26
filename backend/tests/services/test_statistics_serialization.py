"""REQ-SH-NOW-4: statistics API datetimes serialize under one convention.

Discovery F-B/F-L#3: ``OverviewStats.last_updated`` was stamped with an *aware*
``datetime.now(UTC)`` while every other statistics datetime (``recorded_at``,
``created_at``, ``last_activity`` …) is stored and serialized naive. A response
that mixes offset-bearing and offset-less timestamps forces a consumer to parse
two conventions. Q2 fixes the single convention as **naive-UTC** (matching the
``utc_now`` "strips tzinfo for DB compatibility" rule).

Verified at the API-contract seam: the real service result, serialized through
the response model, carries no timezone offset.
"""

import json

from app.schemas.statistics import OverviewStats
from app.services.snapshot_service import SnapshotService


def test_overview_last_updated_serializes_without_offset(sync_db_session):
    """REQ-SH-NOW-4: the overview's last_updated is naive-UTC, so the serialized
    response carries no '+00:00'/'Z' offset — one convention with the other
    (naive) statistics datetimes."""
    service = SnapshotService(sync_db_session)
    stats = service.get_overview_stats()

    assert stats["last_updated"].tzinfo is None, "last_updated must be naive-UTC (Q2)"

    payload = json.loads(OverviewStats(**stats).model_dump_json())
    last_updated = payload["last_updated"]
    assert "+" not in last_updated and not last_updated.endswith("Z"), (
        f"last_updated serialized with a timezone offset ({last_updated}); "
        "statistics datetimes must all be offset-less (REQ-SH-NOW-4)"
    )
