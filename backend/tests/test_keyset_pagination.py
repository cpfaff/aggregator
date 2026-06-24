"""Keyset pagination correctness for the provider, user and validation repos.

All four list repositories share the keyset helper. Dataset is covered in
test_dataset_pagination.py; here we cover the descending default of the
validation repo (B7) and custom-sort walks for providers and users (B6/B8).
"""

import pytest

from app.models import DataProviderModel, UserModel, ValidationJobModel
from app.repositories.provider_repository import ProviderRepository
from app.repositories.user_repository import UserRepository
from app.repositories.validation_repository import ValidationRepository
from app.schemas.pagination import PaginationParams
from app.utils.pagination import encode_cursor
from app.utils.sorting import SortDirection, SortParam


@pytest.mark.asyncio
async def test_validation_jobs_forward_paging_is_most_recent_first(db_session):
    for jid in range(1, 11):
        db_session.add(ValidationJobModel(id=jid, task_id=f"t{jid}", status="pending"))
    await db_session.flush()
    repo = ValidationRepository(db_session)

    page1, _total, next_cursor, _prev = await repo.list_jobs(
        pagination=PaginationParams(limit=3)
    )
    assert [j.id for j in page1] == [10, 9, 8]

    page2, _t, _n, _p = await repo.list_jobs(
        pagination=PaginationParams(limit=3, after=next_cursor)
    )
    assert [j.id for j in page2] == [7, 6, 5]


@pytest.mark.asyncio
async def test_validation_jobs_before_cursor_returns_preceding_page(db_session):
    """Descending display [10..1]; before id=5 -> the preceding page 8,7,6 (B7)."""
    for jid in range(1, 11):
        db_session.add(ValidationJobModel(id=jid, task_id=f"t{jid}", status="pending"))
    await db_session.flush()
    repo = ValidationRepository(db_session)

    items, _total, _next, previous_cursor = await repo.list_jobs(
        pagination=PaginationParams(limit=3, before=encode_cursor({"id": 5}))
    )
    assert [j.id for j in items] == [8, 7, 6]
    assert previous_cursor is not None  # 10, 9 still precede this page


@pytest.mark.asyncio
async def test_provider_custom_sort_pagination_walks_all_rows(db_session):
    for pid, name in {1: "Zebra", 2: "Apple", 3: "Mango", 4: "Banana"}.items():
        db_session.add(
            DataProviderModel(id=pid, datacenter="dc", shortName=f"P{pid}", name=name)
        )
    await db_session.flush()
    repo = ProviderRepository(db_session)

    collected: list[int] = []
    cursor = None
    while True:
        items, _t, next_cursor, _p = await repo.list_for_user(
            None,
            sorts=[SortParam(field="name", direction=SortDirection.ASC)],
            pagination=PaginationParams(limit=2, after=cursor),
        )
        collected.extend(p.id for p in items)
        if not next_cursor:
            break
        cursor = next_cursor

    assert collected == [2, 4, 3, 1]  # Apple, Banana, Mango, Zebra


@pytest.mark.asyncio
async def test_user_custom_sort_pagination_walks_all_rows(db_session):
    for uid, username in {1: "zoe", 2: "amy", 3: "max", 4: "bob"}.items():
        db_session.add(
            UserModel(id=uid, username=username, hashed_password="x", provider_roles={})
        )
    await db_session.flush()
    repo = UserRepository(db_session)

    collected: list[int] = []
    cursor = None
    while True:
        items, _t, next_cursor, _p = await repo.list_paginated(
            sorts=[SortParam(field="username", direction=SortDirection.ASC)],
            pagination=PaginationParams(limit=2, after=cursor),
        )
        collected.extend(u.id for u in items)
        if not next_cursor:
            break
        cursor = next_cursor

    assert collected == [2, 4, 3, 1]  # amy, bob, max, zoe
