"""Keyset pagination correctness for datasets (B6, B8).

Cursor pagination must stay contiguous and complete under a custom sort (B8) and
must return the preceding page for a ``before`` cursor (B6) — not the first page.
"""

import pytest

from app.models import DataProviderModel, DatasetModel
from app.repositories.dataset_repository import DatasetRepository
from app.schemas.pagination import PaginationParams
from app.utils.pagination import encode_cursor
from app.utils.sorting import SortDirection, SortParam


@pytest.mark.asyncio
async def test_custom_sort_pagination_walks_all_rows_in_order(db_session):
    """title-sorted paging must visit every row exactly once, in sorted order."""
    db_session.add(DataProviderModel(id=1, datacenter="dc", shortName="P", name="P"))
    # title order is the inverse of id order.
    for did, title in {1: "Zebra", 2: "Apple", 3: "Mango", 4: "Banana"}.items():
        db_session.add(DatasetModel(id=did, title=title, source="s", provider_id=1))
    await db_session.flush()

    repo = DatasetRepository(db_session)
    collected: list[int] = []
    cursor = None
    while True:
        items, _total, next_cursor, _prev = await repo.list_for_provider(
            1,
            sorts=[SortParam(field="title", direction=SortDirection.ASC)],
            pagination=PaginationParams(limit=2, after=cursor),
        )
        collected.extend(d.id for d in items)
        if not next_cursor:
            break
        cursor = next_cursor

    assert collected == [2, 4, 3, 1]  # Apple, Banana, Mango, Zebra
    assert len(collected) == len(set(collected)) == 4


@pytest.mark.asyncio
async def test_before_cursor_returns_preceding_page(db_session):
    """A ``before`` cursor returns the page immediately before it, not page 1."""
    db_session.add(DataProviderModel(id=1, datacenter="dc", shortName="P", name="P"))
    for did in range(1, 11):
        db_session.add(DatasetModel(id=did, title=f"D{did:02d}", source="s", provider_id=1))
    await db_session.flush()

    repo = DatasetRepository(db_session)
    items, _total, _next, previous_cursor = await repo.list_for_provider(
        1, pagination=PaginationParams(limit=3, before=encode_cursor({"id": 8}))
    )

    assert [d.id for d in items] == [5, 6, 7]
    assert previous_cursor is not None  # rows 1..4 still precede this page
