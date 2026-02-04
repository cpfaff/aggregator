"""Tests for the DatasetDeletionService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.dataset_deletion import DatasetDeletionService


class TestDeleteDatasetCascade:
    """Tests for delete_dataset_cascade."""

    @pytest.mark.asyncio
    async def test_deletes_dataset_with_archives(self):
        """Test cascade deletion when dataset has XML archives."""
        db = AsyncMock()

        # Mock archive query returning 2 archive IDs
        archive_result = MagicMock()
        archive_result.fetchall.return_value = [(10,), (20,)]

        # Mock deletion results
        snapshot_delete = MagicMock(rowcount=3)
        validation_delete = MagicMock(rowcount=1)
        archives_delete = MagicMock(rowcount=2)
        links_delete = MagicMock(rowcount=1)
        dataset_delete = MagicMock(rowcount=1)

        db.execute = AsyncMock(
            side_effect=[
                archive_result,
                snapshot_delete,
                validation_delete,
                archives_delete,
                links_delete,
                dataset_delete,
            ]
        )

        service = DatasetDeletionService(db)
        result = await service.delete_dataset_cascade(dataset_id=5, provider_id=1)

        assert result["status"] == "success"
        assert result["dataset_id"] == 5
        assert result["provider_id"] == 1
        assert result["deleted_counts"]["archive_snapshots"] == 3
        assert result["deleted_counts"]["validation_jobs"] == 1
        assert result["deleted_counts"]["xml_archives"] == 2
        assert result["deleted_counts"]["useful_links"] == 1
        assert result["deleted_counts"]["dataset"] == 1
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deletes_dataset_without_archives(self):
        """Test cascade deletion when dataset has no XML archives."""
        db = AsyncMock()

        # No archives found
        archive_result = MagicMock()
        archive_result.fetchall.return_value = []

        archives_delete = MagicMock(rowcount=0)
        links_delete = MagicMock(rowcount=0)
        dataset_delete = MagicMock(rowcount=1)

        db.execute = AsyncMock(
            side_effect=[
                archive_result,
                archives_delete,
                links_delete,
                dataset_delete,
            ]
        )

        service = DatasetDeletionService(db)
        result = await service.delete_dataset_cascade(dataset_id=5, provider_id=1)

        assert result["status"] == "success"
        assert result["deleted_counts"]["archive_snapshots"] == 0
        assert result["deleted_counts"]["validation_jobs"] == 0
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dataset_not_found_returns_not_found_status(self):
        """Test that deleting a non-existent dataset returns not_found status."""
        db = AsyncMock()

        archive_result = MagicMock()
        archive_result.fetchall.return_value = []

        archives_delete = MagicMock(rowcount=0)
        links_delete = MagicMock(rowcount=0)
        dataset_delete = MagicMock(rowcount=0)  # Dataset not found

        db.execute = AsyncMock(
            side_effect=[
                archive_result,
                archives_delete,
                links_delete,
                dataset_delete,
            ]
        )

        service = DatasetDeletionService(db)
        result = await service.delete_dataset_cascade(dataset_id=999, provider_id=1)

        assert result["status"] == "not_found"
        assert result["deleted_counts"]["dataset"] == 0

    @pytest.mark.asyncio
    async def test_rollback_on_error(self):
        """Test that database is rolled back on error."""
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=RuntimeError("DB error"))

        service = DatasetDeletionService(db)
        with pytest.raises(RuntimeError, match="DB error"):
            await service.delete_dataset_cascade(dataset_id=5, provider_id=1)

        db.rollback.assert_awaited_once()


class TestGetDatasetDependencies:
    """Tests for get_dataset_dependencies."""

    @pytest.mark.asyncio
    async def test_counts_all_dependencies(self):
        """Test that all dependency types are counted."""
        db = AsyncMock()

        # Mock archives query
        archive1 = MagicMock()
        archive1.id = 10
        archive2 = MagicMock()
        archive2.id = 20
        archives_result = MagicMock()
        archives_result.fetchall.return_value = [(archive1,), (archive2,)]

        # Mock snapshot count
        snapshots_result = MagicMock()
        snapshots_result.fetchall.return_value = [MagicMock()] * 5

        # Mock validation count
        validation_result = MagicMock()
        validation_result.fetchall.return_value = [MagicMock()] * 2

        # Mock links count
        links_result = MagicMock()
        links_result.fetchall.return_value = [MagicMock()] * 3

        db.execute = AsyncMock(
            side_effect=[archives_result, snapshots_result, validation_result, links_result]
        )

        service = DatasetDeletionService(db)
        counts = await service.get_dataset_dependencies(dataset_id=5)

        assert counts["xml_archives"] == 2
        assert counts["archive_snapshots"] == 5
        assert counts["validation_jobs"] == 2
        assert counts["useful_links"] == 3

    @pytest.mark.asyncio
    async def test_zero_dependencies(self):
        """Test counts when dataset has no dependencies."""
        db = AsyncMock()

        # No archives
        archives_result = MagicMock()
        archives_result.fetchall.return_value = []

        # No links
        links_result = MagicMock()
        links_result.fetchall.return_value = []

        db.execute = AsyncMock(side_effect=[archives_result, links_result])

        service = DatasetDeletionService(db)
        counts = await service.get_dataset_dependencies(dataset_id=5)

        assert counts["xml_archives"] == 0
        assert counts["archive_snapshots"] == 0
        assert counts["validation_jobs"] == 0
        assert counts["useful_links"] == 0
