"""Tests for dataset-related Pydantic schemas."""

import pytest

from app.models.dataset import DatasetModel
from app.schemas.dataset import Dataset, UsefulLink, XmlArchive


class TestXmlArchiveSchema:
    """Tests for the XmlArchive schema."""

    def test_valid_archive(self):
        """Test creating a valid XmlArchive."""
        archive = XmlArchive(url="https://example.com/archive.xml", isLatest=True)
        assert archive.isLatest is True

    def test_optional_id(self):
        """Test that id defaults to None."""
        archive = XmlArchive(url="https://example.com/archive.xml", isLatest=False)
        assert archive.id is None


class TestUsefulLinkSchema:
    """Tests for the UsefulLink schema."""

    def test_valid_link(self):
        """Test creating a valid UsefulLink."""
        link = UsefulLink(title="My Link", url="https://example.com", isLatest=True)
        assert link.title == "My Link"

    def test_trims_title_whitespace(self):
        """Test that leading/trailing whitespace is trimmed from title."""
        link = UsefulLink(title="  My Link  ", url="https://example.com", isLatest=True)
        assert link.title == "My Link"


class TestDatasetSchema:
    """Tests for the Dataset schema."""

    def test_valid_dataset(self):
        """Test creating a valid Dataset."""
        ds = Dataset(source="GFBio", title="Test Dataset")
        assert ds.source == "GFBio"
        assert ds.title == "Test Dataset"

    def test_trims_whitespace(self):
        """Test that source and title are trimmed."""
        ds = Dataset(source="  GFBio  ", title="  Test  ")
        assert ds.source == "GFBio"
        assert ds.title == "Test"

    def test_empty_landing_page_url_becomes_none(self):
        """Test that empty string for landingPageUrl becomes None."""
        ds = Dataset(source="GFBio", title="Test", landingPageUrl="")
        assert ds.landingPageUrl is None

    def test_valid_landing_page_url(self):
        """Test that valid URL is preserved."""
        ds = Dataset(source="GFBio", title="Test", landingPageUrl="https://example.com")
        assert str(ds.landingPageUrl) == "https://example.com/"

    def test_model_dump_excludes_empty_archives(self):
        """Test that model_dump removes empty xmlArchives list."""
        ds = Dataset(source="GFBio", title="Test")
        data = ds.model_dump()
        assert "xmlArchives" not in data

    def test_model_dump_excludes_empty_useful_links(self):
        """Test that model_dump removes empty usefulLinks list."""
        ds = Dataset(source="GFBio", title="Test")
        data = ds.model_dump()
        assert "usefulLinks" not in data

    def test_model_dump_includes_nonempty_archives(self):
        """Test that model_dump keeps non-empty xmlArchives."""
        ds = Dataset(
            source="GFBio",
            title="Test",
            xmlArchives=[XmlArchive(url="https://example.com/a.xml", isLatest=True)],
        )
        data = ds.model_dump()
        assert "xmlArchives" in data
        assert len(data["xmlArchives"]) == 1

    def test_is_harvest_ready_defaults_to_false(self):
        """A new dataset is staged (not harvest-ready) unless explicitly set."""
        ds = Dataset(source="GFBio", title="Test")
        assert ds.isHarvestReady is False

    def test_is_harvest_ready_survives_model_dump(self):
        """An explicit harvest-ready flag survives the overridden model_dump."""
        ds = Dataset(source="GFBio", title="Test", isHarvestReady=True)
        data = ds.model_dump()
        assert data["isHarvestReady"] is True


class TestDatasetModelHarvestReady:
    """Tests for the isHarvestReady column default on the ORM model."""

    @pytest.mark.asyncio
    async def test_new_dataset_defaults_to_not_harvest_ready(self, db_session):
        """A dataset inserted without isHarvestReady persists as False (staged)."""
        ds = DatasetModel(source="GFBio", title="Test")
        db_session.add(ds)
        await db_session.flush()
        await db_session.refresh(ds)
        assert ds.isHarvestReady is False
