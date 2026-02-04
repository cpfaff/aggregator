"""
Simplified archive snapshot collection tasks.

This module replaces the complex statistics_tasks.py with a simple,
focused implementation for collecting archive snapshots.

Includes HTTP-based change detection to skip unchanged archives.
"""

import logging
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from celery import shared_task

from app.db.session import SessionLocal
from app.models.archive_snapshot import ArchiveSnapshotModel
from app.models.dataset import XmlArchiveModel

logger = logging.getLogger(__name__)


@dataclass
class HttpMetadata:
    """HTTP metadata from archive download for change detection."""

    etag: Optional[str] = None
    last_modified: Optional[str] = None


@dataclass
class ArchiveParseResult:
    """Result of parsing an archive including HTTP metadata."""

    unit_count: int
    http_metadata: HttpMetadata


class XMLParsingError(Exception):
    """Raised when XML parsing fails."""

    pass


def _normalize_etag(etag: Optional[str]) -> Optional[str]:
    """
    Normalize an ETag for comparison.

    Strips weak validator prefix (W/) and surrounding quotes, as servers
    may vary in how they format ETags.

    Args:
        etag: Raw ETag header value

    Returns:
        Normalized ETag string, or None if input is None/empty
    """
    if not etag:
        return None
    # Strip weak validator prefix and quotes
    normalized = etag.strip()
    if normalized.startswith("W/"):
        normalized = normalized[2:]
    return normalized.strip('"')


def check_archive_changed(
    archive_url: str,
    previous_etag: Optional[str] = None,
    previous_last_modified: Optional[str] = None,
) -> tuple[bool, HttpMetadata]:
    """
    Check if an archive has changed using HTTP HEAD request.

    Compares ETag and Last-Modified headers against stored values
    to determine if the archive needs to be re-downloaded.

    Args:
        archive_url: URL of the archive to check
        previous_etag: ETag from the last download (if any)
        previous_last_modified: Last-Modified from the last download (if any)

    Returns:
        Tuple of (changed: bool, current_metadata: HttpMetadata)
        - changed is True if archive should be downloaded
        - current_metadata contains the current ETag/Last-Modified headers

    Note:
        If HEAD request fails or headers are missing, assumes changed (safe default).
        There is a small race condition window between this check and the actual
        download where the archive could change - this is acceptable for our use case
        as we prioritize avoiding unnecessary downloads over perfect consistency.
    """
    try:
        response = requests.head(archive_url, timeout=10, allow_redirects=True)
        response.raise_for_status()

        current_metadata = HttpMetadata(
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )

        # No previous data = assume changed (first run)
        if not previous_etag and not previous_last_modified:
            logger.debug(f"No previous metadata for {archive_url}, will download")
            return True, current_metadata

        # Compare ETag first (most reliable - content-based)
        # Normalize ETags to handle weak validators (W/) and quote variations
        prev_etag_normalized = _normalize_etag(previous_etag)
        curr_etag_normalized = _normalize_etag(current_metadata.etag)

        if prev_etag_normalized and curr_etag_normalized:
            if prev_etag_normalized == curr_etag_normalized:
                logger.debug(f"ETag match for {archive_url}, skipping download")
                return False, current_metadata
            else:
                logger.debug(f"ETag changed for {archive_url}, will download")
                return True, current_metadata

        # Fall back to Last-Modified comparison
        if previous_last_modified and current_metadata.last_modified:
            if previous_last_modified == current_metadata.last_modified:
                logger.debug(f"Last-Modified match for {archive_url}, skipping download")
                return False, current_metadata
            else:
                logger.debug(f"Last-Modified changed for {archive_url}, will download")
                return True, current_metadata

        # Can't determine = assume changed (safe default)
        logger.debug(f"Cannot determine change status for {archive_url}, will download")
        return True, current_metadata

    except requests.RequestException as e:
        logger.warning(f"HEAD request failed for {archive_url}: {e}, will download anyway")
        return True, HttpMetadata()


def parse_archive_xml(xml_url: str) -> ArchiveParseResult:
    """
    Download and parse an archive to count biological units.

    Handles both direct XML files and ZIP archives containing XML files.
    Uses streaming download and memory-efficient processing.

    Args:
        xml_url: URL of the XML file or ZIP archive

    Returns:
        ArchiveParseResult containing unit count and HTTP metadata

    Raises:
        XMLParsingError: If download or parsing fails
    """
    try:
        response = requests.get(xml_url, timeout=30, stream=True)
        response.raise_for_status()

        # Capture HTTP headers for change detection
        http_metadata = HttpMetadata(
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )

        total_unit_count = 0

        # Use SpooledTemporaryFile: small files in memory, large on disk
        with tempfile.SpooledTemporaryFile(max_size=10 * 1024 * 1024) as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_file.write(chunk)

            temp_file.seek(0)
            first_bytes = temp_file.read(2)
            temp_file.seek(0)

            if first_bytes == b"PK":
                # ZIP archive
                try:
                    with zipfile.ZipFile(temp_file) as zip_file:
                        xml_files = [
                            f
                            for f in zip_file.namelist()
                            if f.lower().endswith(".xml") and not f.startswith("__MACOSX/")
                        ]

                        if not xml_files:
                            raise XMLParsingError("No XML files found in ZIP archive")

                        for xml_filename in xml_files:
                            try:
                                with zip_file.open(xml_filename) as xml_file:
                                    xml_content = xml_file.read()
                                    root = ET.fromstring(xml_content)
                                    total_unit_count += _count_units(root)
                            except ET.ParseError as e:
                                logger.warning(f"Failed to parse {xml_filename}: {e}")
                                continue

                except zipfile.BadZipFile:
                    # Not a valid ZIP, try as direct XML
                    temp_file.seek(0)
                    root = ET.fromstring(temp_file.read())
                    total_unit_count = _count_units(root)
            else:
                # Direct XML file
                root = ET.fromstring(temp_file.read())
                total_unit_count = _count_units(root)

        return ArchiveParseResult(
            unit_count=total_unit_count,
            http_metadata=http_metadata,
        )

    except requests.RequestException as e:
        raise XMLParsingError(f"Download failed: {e}")
    except ET.ParseError as e:
        raise XMLParsingError(f"XML parsing failed: {e}")
    except Exception as e:
        raise XMLParsingError(f"Unexpected error: {e}")


def _count_units(root) -> int:
    """
    Count Unit elements in an XML root, handling multiple ABCD versions.

    Args:
        root: XML root element

    Returns:
        Number of Unit elements found
    """
    # ABCD namespace URIs
    namespaces = {
        "abcd206": "http://www.tdwg.org/schemas/abcd/2.06",
        "abcd21": "http://rs.tdwg.org/abcd/2.1",
        "abcd3": "http://rs.tdwg.org/abcd/3.0",
    }

    # Detect namespace from root element
    ns_uri = None
    if root.tag.startswith("{"):
        ns_uri = root.tag.split("}")[0][1:]
    else:
        # Check children for namespace
        for prefix, uri in namespaces.items():
            if any(uri in elem.tag for elem in root.iter()):
                ns_uri = uri
                break

    # Count units
    if ns_uri:
        # Try various paths with namespace
        for path in [f".//{{{ns_uri}}}Unit", ".//Unit"]:
            units = root.findall(path)
            if units:
                return len(units)
    else:
        # No namespace - try direct
        units = root.findall(".//Unit")
        if units:
            return len(units)

    return 0


@shared_task(name="snapshots.collect_single_archive_snapshot", queue="light_tasks")
def collect_single_archive_snapshot(archive_id: int, force: bool = False) -> Dict[str, Any]:
    """
    Collect a snapshot for a single archive.

    Called when a new archive is registered to immediately capture its unit count.
    This is still append-only - just adds data sooner rather than waiting for nightly job.

    Uses HTTP change detection to skip unchanged archives unless force=True.

    Args:
        archive_id: ID of the archive to snapshot
        force: If True, skip change detection and always download

    Returns:
        Dict with status and unit_count
    """
    db = SessionLocal()
    try:
        archive = db.query(XmlArchiveModel).filter(XmlArchiveModel.id == archive_id).first()

        if not archive:
            logger.warning(f"Archive {archive_id} not found for snapshot")
            return {"status": "error", "message": "Archive not found"}

        if not archive.isLatest:
            logger.info(f"Archive {archive_id} is not latest, skipping snapshot")
            return {"status": "skipped", "message": "Archive is not latest version"}

        # Get the latest snapshot for this archive to check for changes
        latest_snapshot = (
            db.query(ArchiveSnapshotModel)
            .filter(ArchiveSnapshotModel.archive_id == archive_id)
            .order_by(ArchiveSnapshotModel.recorded_at.desc())
            .first()
        )

        # Check if archive has changed (unless force=True or no previous snapshot)
        if not force and latest_snapshot:
            changed, _ = check_archive_changed(
                archive.url,
                previous_etag=latest_snapshot.http_etag,
                previous_last_modified=latest_snapshot.http_last_modified,
            )
            if not changed:
                logger.info(f"Archive {archive_id} unchanged, skipping download")
                return {
                    "status": "unchanged",
                    "archive_id": archive_id,
                    "message": "Archive unchanged since last snapshot",
                }

        try:
            result = parse_archive_xml(archive.url)

            snapshot = ArchiveSnapshotModel(
                archive_id=archive.id,
                unit_count=result.unit_count,
                http_etag=result.http_metadata.etag,
                http_last_modified=result.http_metadata.last_modified,
            )
            db.add(snapshot)
            db.commit()

            logger.info(f"Snapshot created for archive {archive_id}: {result.unit_count} units")
            return {"status": "success", "archive_id": archive_id, "unit_count": result.unit_count}

        except XMLParsingError as e:
            logger.warning(f"Failed to parse archive {archive_id}: {e}")
            return {"status": "error", "message": str(e)}

    except Exception as e:
        logger.error(f"Unexpected error collecting snapshot for archive {archive_id}: {e}")
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@shared_task(name="snapshots.collect_archive_snapshots", queue="light_tasks")
def collect_archive_snapshots():
    """
    Collect snapshots for all current archives.

    This is a TRUE append-only operation - creates new snapshot records
    without updating or deleting existing data.

    Runs daily via Celery beat to build historical timeline.
    Uses HTTP change detection to skip downloading unchanged archives.
    Skips archives that already have a snapshot for today.
    """
    from datetime import date

    from sqlalchemy import func

    db = SessionLocal()
    try:
        today = date.today()

        # Get all current (latest) archives
        archives = db.query(XmlArchiveModel).filter(XmlArchiveModel.isLatest == True).all()

        # Get archive IDs that already have snapshots for today
        existing_today = (
            db.query(ArchiveSnapshotModel.archive_id)
            .filter(func.date(ArchiveSnapshotModel.recorded_at) == today)
            .all()
        )
        existing_archive_ids = {r[0] for r in existing_today}

        # Filter to archives that need snapshots
        archives_to_process = [a for a in archives if a.id not in existing_archive_ids]

        # Build a map of archive_id -> latest snapshot for HTTP metadata lookup
        # This is more efficient than querying per archive in the loop.
        # Note: For very large archive collections (10k+), consider chunked processing
        # to reduce memory usage. Current scale (~100-200 archives) is fine.
        latest_snapshot_subq = (
            db.query(
                ArchiveSnapshotModel.archive_id,
                func.max(ArchiveSnapshotModel.recorded_at).label("max_recorded"),
            )
            .group_by(ArchiveSnapshotModel.archive_id)
            .subquery()
        )

        latest_snapshots = (
            db.query(ArchiveSnapshotModel)
            .join(
                latest_snapshot_subq,
                (ArchiveSnapshotModel.archive_id == latest_snapshot_subq.c.archive_id)
                & (ArchiveSnapshotModel.recorded_at == latest_snapshot_subq.c.max_recorded),
            )
            .all()
        )

        # Create lookup map: archive_id -> (http_etag, http_last_modified, unit_count)
        snapshot_metadata_map = {
            s.archive_id: (s.http_etag, s.http_last_modified, s.unit_count)
            for s in latest_snapshots
        }

        logger.info(
            f"Starting snapshot collection: {len(archives_to_process)} archives to check "
            f"({len(existing_archive_ids)} already have snapshots today)"
        )

        success_count = 0
        unchanged_count = 0
        error_count = 0
        skipped_today_count = len(existing_archive_ids)

        for archive in archives_to_process:
            try:
                # Get previous snapshot data for this archive
                prev_etag, prev_last_modified, prev_unit_count = snapshot_metadata_map.get(
                    archive.id, (None, None, None)
                )

                # Check if archive has changed
                changed, current_http_metadata = check_archive_changed(
                    archive.url,
                    previous_etag=prev_etag,
                    previous_last_modified=prev_last_modified,
                )

                if not changed and prev_unit_count is not None:
                    # Archive unchanged - create snapshot with previous data to maintain daily timeline
                    # This avoids re-downloading while still building the historical timeline
                    snapshot = ArchiveSnapshotModel(
                        archive_id=archive.id,
                        unit_count=prev_unit_count,
                        http_etag=current_http_metadata.etag or prev_etag,
                        http_last_modified=current_http_metadata.last_modified
                        or prev_last_modified,
                    )
                    db.add(snapshot)
                    logger.debug(
                        f"Archive {archive.id} unchanged, using previous unit count: {prev_unit_count}"
                    )
                    unchanged_count += 1
                    continue

                # Archive changed or first time - download and parse
                result = parse_archive_xml(archive.url)

                snapshot = ArchiveSnapshotModel(
                    archive_id=archive.id,
                    unit_count=result.unit_count,
                    http_etag=result.http_metadata.etag,
                    http_last_modified=result.http_metadata.last_modified,
                )
                db.add(snapshot)

                logger.info(f"Snapshot for archive {archive.id}: {result.unit_count} units")
                success_count += 1

            except XMLParsingError as e:
                logger.warning(f"Failed to process archive {archive.id}: {e}")
                error_count += 1
                continue
            except Exception as e:
                logger.error(f"Unexpected error for archive {archive.id}: {e}")
                error_count += 1
                continue

        db.commit()
        logger.info(
            f"Snapshot collection complete: {success_count} downloaded, "
            f"{unchanged_count} unchanged (reused previous data), {error_count} failed, "
            f"{skipped_today_count} skipped (already done today)"
        )

        return {
            "success_count": success_count,
            "unchanged_count": unchanged_count,
            "error_count": error_count,
            "skipped_today_count": skipped_today_count,
            "total_archives": len(archives),
        }

    except Exception as e:
        logger.error(f"Snapshot collection failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()
