"""
Simplified archive snapshot collection tasks.

This module replaces the complex statistics_tasks.py with a simple,
focused implementation for collecting archive snapshots.

Total: ~100 lines (vs 2,988 in the old system)
"""
import logging
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Any

import requests
from celery import shared_task

from app.db.session import SessionLocal
from app.models.dataset import XmlArchiveModel
from app.models.archive_snapshot import ArchiveSnapshotModel

logger = logging.getLogger(__name__)


class XMLParsingError(Exception):
    """Raised when XML parsing fails."""
    pass


def parse_archive_xml(xml_url: str) -> int:
    """
    Download and parse an archive to count biological units.

    Handles both direct XML files and ZIP archives containing XML files.
    Uses streaming download and memory-efficient processing.

    Args:
        xml_url: URL of the XML file or ZIP archive

    Returns:
        Total unit count across all XML files in the archive

    Raises:
        XMLParsingError: If download or parsing fails
    """
    try:
        response = requests.get(xml_url, timeout=30, stream=True)
        response.raise_for_status()

        total_unit_count = 0

        # Use SpooledTemporaryFile: small files in memory, large on disk
        with tempfile.SpooledTemporaryFile(max_size=10*1024*1024) as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_file.write(chunk)

            temp_file.seek(0)
            first_bytes = temp_file.read(2)
            temp_file.seek(0)

            if first_bytes == b'PK':
                # ZIP archive
                try:
                    with zipfile.ZipFile(temp_file) as zip_file:
                        xml_files = [
                            f for f in zip_file.namelist()
                            if f.lower().endswith('.xml') and not f.startswith('__MACOSX/')
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

        return total_unit_count

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
        'abcd206': 'http://www.tdwg.org/schemas/abcd/2.06',
        'abcd21': 'http://rs.tdwg.org/abcd/2.1',
        'abcd3': 'http://rs.tdwg.org/abcd/3.0'
    }

    # Detect namespace from root element
    ns_uri = None
    if root.tag.startswith('{'):
        ns_uri = root.tag.split('}')[0][1:]
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


@shared_task(name="snapshots.collect_single_archive_snapshot", queue='light_tasks')
def collect_single_archive_snapshot(archive_id: int) -> Dict[str, Any]:
    """
    Collect a snapshot for a single archive.

    Called when a new archive is registered to immediately capture its unit count.
    This is still append-only - just adds data sooner rather than waiting for nightly job.

    Args:
        archive_id: ID of the archive to snapshot

    Returns:
        Dict with status and unit_count
    """
    db = SessionLocal()
    try:
        archive = db.query(XmlArchiveModel).filter(
            XmlArchiveModel.id == archive_id
        ).first()

        if not archive:
            logger.warning(f"Archive {archive_id} not found for snapshot")
            return {"status": "error", "message": "Archive not found"}

        if not archive.isLatest:
            logger.info(f"Archive {archive_id} is not latest, skipping snapshot")
            return {"status": "skipped", "message": "Archive is not latest version"}

        try:
            unit_count = parse_archive_xml(archive.url)

            snapshot = ArchiveSnapshotModel(
                archive_id=archive.id,
                unit_count=unit_count
            )
            db.add(snapshot)
            db.commit()

            logger.info(f"Snapshot created for archive {archive_id}: {unit_count} units")
            return {
                "status": "success",
                "archive_id": archive_id,
                "unit_count": unit_count
            }

        except XMLParsingError as e:
            logger.warning(f"Failed to parse archive {archive_id}: {e}")
            return {"status": "error", "message": str(e)}

    except Exception as e:
        logger.error(f"Unexpected error collecting snapshot for archive {archive_id}: {e}")
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@shared_task(name="snapshots.collect_archive_snapshots", queue='light_tasks')
def collect_archive_snapshots():
    """
    Collect snapshots for all current archives.

    This is a TRUE append-only operation - creates new snapshot records
    without updating or deleting existing data.

    Runs daily via Celery beat to build historical timeline.
    Skips archives that already have a snapshot for today.
    """
    from datetime import date
    from sqlalchemy import func

    db = SessionLocal()
    try:
        today = date.today()

        # Get all current (latest) archives
        archives = db.query(XmlArchiveModel).filter(
            XmlArchiveModel.isLatest == True
        ).all()

        # Get archive IDs that already have snapshots for today
        existing_today = db.query(ArchiveSnapshotModel.archive_id).filter(
            func.date(ArchiveSnapshotModel.recorded_at) == today
        ).all()
        existing_archive_ids = {r[0] for r in existing_today}

        # Filter to archives that need snapshots
        archives_to_process = [a for a in archives if a.id not in existing_archive_ids]

        logger.info(
            f"Starting snapshot collection: {len(archives_to_process)} archives to process "
            f"({len(existing_archive_ids)} already have snapshots today)"
        )

        success_count = 0
        error_count = 0
        skipped_count = len(existing_archive_ids)

        for archive in archives_to_process:
            try:
                unit_count = parse_archive_xml(archive.url)

                snapshot = ArchiveSnapshotModel(
                    archive_id=archive.id,
                    unit_count=unit_count
                )
                db.add(snapshot)

                logger.info(f"Snapshot for archive {archive.id}: {unit_count} units")
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
            f"Snapshot collection complete: {success_count} successful, "
            f"{error_count} failed, {skipped_count} skipped (already done today)"
        )

        return {
            "success_count": success_count,
            "error_count": error_count,
            "skipped_count": skipped_count,
            "total_archives": len(archives)
        }

    except Exception as e:
        logger.error(f"Snapshot collection failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()
