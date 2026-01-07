"""
Archive snapshot model for tracking historical unit counts.

This implements a true append-only storage pattern for point-in-time
snapshots of archive analysis results.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.models.base import Base


class ArchiveSnapshotModel(Base):
    """Point-in-time snapshot of archive analysis results.

    Records the unit count for an archive at a specific time, enabling
    historical tracking of how datasets change over time.

    This is a TRUE append-only table - records are never updated.
    Each collection run creates new snapshot records.

    Attributes:
        id: Primary key
        archive_id: Foreign key to xml_archives table
        recorded_at: When this snapshot was taken
        unit_count: Number of biological units (<Unit> elements) in the archive
    """
    __tablename__ = "archive_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    archive_id = Column(
        Integer,
        ForeignKey("xml_archives.id", ondelete="CASCADE"),
        nullable=False
    )
    recorded_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    unit_count = Column(Integer, nullable=False, default=0)

    # Relationship back to archive
    archive = relationship("XmlArchiveModel", backref="snapshots")

    __table_args__ = (
        # Index for efficient "latest per archive" queries
        Index("idx_snapshot_archive_id", "archive_id"),
        Index("idx_snapshot_recorded_at", "recorded_at"),
        Index("idx_snapshot_archive_recorded", "archive_id", "recorded_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ArchiveSnapshot(id={self.id}, archive_id={self.archive_id}, "
            f"unit_count={self.unit_count}, recorded_at={self.recorded_at})>"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "archive_id": self.archive_id,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "unit_count": self.unit_count,
        }
