"""Tests for core utility functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.utils import apply_entity_updates


class TestApplyEntityUpdates:
    """Tests for the apply_entity_updates function."""

    def _make_entity(self, entity_id, url="http://example.com", is_latest=True):
        """Create a mock entity."""
        entity = MagicMock()
        entity.id = entity_id
        entity.url = url
        entity.isLatest = is_latest
        return entity

    def _make_new_entity(self, entity_id=None, url="http://new.com", is_latest=True):
        """Create a mock new entity from request data."""
        entity = MagicMock()
        entity.id = entity_id
        entity.model_dump.return_value = {"url": url, "isLatest": is_latest}
        return entity

    @pytest.mark.asyncio
    @patch("app.core.utils.invalidate_cache")
    async def test_creates_new_entities(self, mock_invalidate):
        """Test that new entities (no ID) are created."""
        db = AsyncMock()
        # db.add is synchronous in SQLAlchemy, so use MagicMock to avoid unawaited coroutine
        db.add = MagicMock()

        # Mock dataset lookup
        dataset = MagicMock()
        dataset.provider_id = 1
        dataset_result = MagicMock()
        dataset_result.scalar_one_or_none.return_value = dataset
        db.execute = AsyncMock(return_value=dataset_result)

        entity_class = MagicMock()
        entity_class.__tablename__ = "xml_archives"
        new_entity_instance = MagicMock()
        entity_class.return_value = new_entity_instance

        new_entity = self._make_new_entity(entity_id=None)

        result = await apply_entity_updates(
            db=db,
            entity_list=[],
            new_entities=[new_entity],
            entity_class=entity_class,
            dataset_id=5,
        )

        assert len(result) == 1
        db.add.assert_called_once_with(new_entity_instance)
        db.flush.assert_awaited_once()
        mock_invalidate.assert_called()

    @pytest.mark.asyncio
    @patch("app.core.utils.invalidate_cache")
    async def test_updates_existing_entities(self, mock_invalidate):
        """Test that existing entities are updated by ID."""
        db = AsyncMock()

        dataset = MagicMock()
        dataset.provider_id = 1
        dataset_result = MagicMock()
        dataset_result.scalar_one_or_none.return_value = dataset
        db.execute = AsyncMock(return_value=dataset_result)

        existing = self._make_entity(entity_id=10)
        new_data = self._make_new_entity(entity_id=10, url="http://updated.com")

        entity_class = MagicMock()
        entity_class.__tablename__ = "xml_archives"

        result = await apply_entity_updates(
            db=db,
            entity_list=[existing],
            new_entities=[new_data],
            entity_class=entity_class,
            dataset_id=5,
        )

        assert len(result) == 1
        assert result[0] == existing

    @pytest.mark.asyncio
    @patch("app.core.utils.invalidate_cache")
    async def test_deletes_removed_entities(self, mock_invalidate):
        """Test that entities not in the update list are deleted."""
        db = AsyncMock()

        dataset = MagicMock()
        dataset.provider_id = 1
        dataset_result = MagicMock()
        dataset_result.scalar_one_or_none.return_value = dataset
        db.execute = AsyncMock(return_value=dataset_result)

        existing = self._make_entity(entity_id=10)

        entity_class = MagicMock()
        entity_class.__tablename__ = "xml_archives"

        # Empty update list — existing entity should be deleted
        result = await apply_entity_updates(
            db=db,
            entity_list=[existing],
            new_entities=[],
            entity_class=entity_class,
            dataset_id=5,
        )

        assert len(result) == 0
        db.delete.assert_awaited_once_with(existing)

    @pytest.mark.asyncio
    @patch("app.core.utils.invalidate_cache")
    async def test_invalidates_caches(self, mock_invalidate):
        """Test that appropriate caches are invalidated."""
        db = AsyncMock()

        dataset = MagicMock()
        dataset.provider_id = 42
        dataset_result = MagicMock()
        dataset_result.scalar_one_or_none.return_value = dataset
        db.execute = AsyncMock(return_value=dataset_result)

        entity_class = MagicMock()
        entity_class.__tablename__ = "xml_archives"

        await apply_entity_updates(
            db=db,
            entity_list=[],
            new_entities=[],
            entity_class=entity_class,
            dataset_id=5,
        )

        cache_calls = [call.args[0] for call in mock_invalidate.call_args_list]
        assert "xml-archives" in cache_calls
        assert "dataset:5" in cache_calls
        assert "datasets" in cache_calls
        assert "provider:42" in cache_calls
        assert "providers" in cache_calls

    @pytest.mark.asyncio
    @patch("app.core.utils.invalidate_cache")
    async def test_no_provider_cache_when_dataset_missing(self, mock_invalidate):
        """Test that provider cache is not invalidated when dataset not found."""
        db = AsyncMock()

        dataset_result = MagicMock()
        dataset_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=dataset_result)

        entity_class = MagicMock()
        entity_class.__tablename__ = "useful_links"

        await apply_entity_updates(
            db=db,
            entity_list=[],
            new_entities=[],
            entity_class=entity_class,
            dataset_id=5,
        )

        cache_calls = [call.args[0] for call in mock_invalidate.call_args_list]
        assert "providers" not in cache_calls

    @pytest.mark.asyncio
    @patch("app.core.utils.invalidate_cache")
    async def test_handles_url_field_conversion(self, mock_invalidate):
        """Test that AnyUrl fields are converted to strings."""
        from pydantic import AnyUrl

        db = AsyncMock()
        # db.add is synchronous in SQLAlchemy, so use MagicMock to avoid unawaited coroutine
        db.add = MagicMock()

        dataset = MagicMock()
        dataset.provider_id = 1
        dataset_result = MagicMock()
        dataset_result.scalar_one_or_none.return_value = dataset
        db.execute = AsyncMock(return_value=dataset_result)

        entity_class = MagicMock()
        entity_class.__tablename__ = "xml_archives"

        new_entity = MagicMock()
        new_entity.id = None
        url_value = AnyUrl("http://example.com/archive.xml")
        new_entity.model_dump.return_value = {"url": url_value, "isLatest": True}

        await apply_entity_updates(
            db=db,
            entity_list=[],
            new_entities=[new_entity],
            entity_class=entity_class,
            dataset_id=5,
        )

        # The entity_class constructor should receive a string URL, not AnyUrl
        call_kwargs = entity_class.call_args
        assert isinstance(call_kwargs[1]["url"], str)
