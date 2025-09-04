"""
Celery tasks for statistics collection and aggregation.
"""

import logging
import requests
import xml.etree.ElementTree as ET
import zipfile
import io
import tempfile
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
from collections import defaultdict

from celery import shared_task
from sqlalchemy import func, and_, distinct, Integer
from sqlalchemy.orm import Session

from app.models import (
    StatisticModel, 
    DataProviderModel, 
    DatasetModel, 
    XmlArchiveModel,
    ValidationJobModel,
    MetricType,
    EntityType,
    Period
)
from app.db.session import SessionLocal
from app.core.task_base import LoggingTask

logger = logging.getLogger(__name__)


class XMLParsingError(Exception):
    """Custom exception for XML parsing errors."""
    pass


def _process_single_xml_root(root, filename: str) -> Dict[str, Any]:
    """
    Process a single XML root element and extract unit count only.
    Implements memory-efficient streaming processing for large unit collections.
    
    Args:
        root: XML root element
        filename: Name of XML file being processed (for logging)
        
    Returns:
        Dictionary containing unit count from this XML file
    """
    # Common ABCD namespaces
    namespaces = {
        'abcd': 'http://www.tdwg.org/schemas/abcd/2.06',
        'abcd21': 'http://rs.tdwg.org/abcd/2.1',
        'abcd3': 'http://rs.tdwg.org/abcd/3.0'
    }
    
    # Try to detect namespace
    detected_ns = None
    for prefix, uri in namespaces.items():
        if uri in root.tag or any(uri in elem.tag for elem in root.iter()):
            # Map the different ABCD versions to a consistent prefix
            if prefix in ['abcd', 'abcd21', 'abcd3']:
                detected_ns = {'abcd': uri}
            break
    
    if not detected_ns:
        # Fallback: use default namespace if present
        if root.tag.startswith('{'):
            ns_uri = root.tag.split('}')[0][1:]
            detected_ns = {'abcd': ns_uri}
    
    # Count units only - no need to extract other information
    unit_count = 0
    
    if detected_ns:
        ns_uri = detected_ns['abcd']
        
        # Find Units - different paths for different versions
        unit_paths = [
            f".//{{{ns_uri}}}Unit",
            f".//{{{ns_uri}}}DataSet/{{{ns_uri}}}Units/{{{ns_uri}}}Unit",
            f".//{{{ns_uri}}}DataSets/{{{ns_uri}}}DataSet/{{{ns_uri}}}Units/{{{ns_uri}}}Unit",
            f".//{{{ns_uri}}}Units/{{{ns_uri}}}Unit"
        ]
        
        for path in unit_paths:
            unit_elements = root.findall(path, detected_ns)
            if unit_elements:
                units = unit_elements
                break
    else:
        # Try without namespace
        unit_elements = root.findall(".//Unit")
        if unit_elements:
            units = unit_elements
    
    unit_count = len(units)
    
    # Only return unit count - skip all other extraction
    logger.debug(f"Found {unit_count} units in {filename}")
    
    return {
        'unit_count': unit_count
    }


def parse_abcd_xml(xml_url: str) -> Dict[str, Any]:
    """
    Parse ABCD XML file and extract unit counts only.
    Handles both direct XML files and ZIP archives containing XML files.
    For ZIP archives, processes ALL XML files to get complete unit counts.
    
    Args:
        xml_url: URL of the XML file or ZIP archive to parse
        
    Returns:
        Dictionary containing unit count aggregated across all XML files in archive
        
    Raises:
        XMLParsingError: If XML parsing fails
    """
    try:
        # Download content with streaming to avoid memory issues
        response = requests.get(xml_url, timeout=300, stream=True)
        response.raise_for_status()
        
        # Initialize aggregated results - only unit count now
        total_unit_count = 0
        xml_files_processed = 0
        
        # Use a temporary file to avoid loading entire content into memory
        # SpooledTemporaryFile keeps small files in memory, large files on disk
        with tempfile.SpooledTemporaryFile(max_size=10*1024*1024) as temp_file:  # 10MB threshold
            # Stream download to temp file
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_file.write(chunk)
            
            # Reset to beginning for reading
            temp_file.seek(0)
            
            # Check if content starts with ZIP file signature (PK)
            first_bytes = temp_file.read(2)
            temp_file.seek(0)  # Reset again
            
            if first_bytes == b'PK':
                logger.debug(f"Detected ZIP archive for URL: {xml_url}")
                
                # Handle ZIP file - process ALL XML files
                try:
                    with zipfile.ZipFile(temp_file) as zip_file:
                        # Look for XML files in the ZIP
                        xml_files = [f for f in zip_file.namelist() 
                                   if f.lower().endswith('.xml') and not f.startswith('__MACOSX/')]
                        
                        if not xml_files:
                            raise XMLParsingError("No XML files found in ZIP archive")
                        
                        logger.debug(f"Found {len(xml_files)} XML files in archive, processing all")
                        
                        # Process ALL XML files in the archive
                        for xml_filename in xml_files:
                            try:
                                logger.debug(f"Processing XML file: {xml_filename}")
                                
                                # Extract and parse the XML file
                                with zip_file.open(xml_filename) as xml_file:
                                    xml_content = xml_file.read()
                                    root = ET.fromstring(xml_content)
                                    
                                    # Process this XML file and aggregate unit count only
                                    file_results = _process_single_xml_root(root, xml_filename)
                                    
                                    # Aggregate unit count only
                                    total_unit_count += file_results['unit_count']
                                    xml_files_processed += 1
                                    
                            except ET.ParseError as e:
                                logger.warning(f"Failed to parse XML file {xml_filename} in archive: {e}")
                                continue
                            except Exception as e:
                                logger.warning(f"Error processing XML file {xml_filename} in archive: {e}")
                                continue
                            
                except zipfile.BadZipFile:
                    # Not a valid ZIP file, treat as direct XML
                    logger.debug(f"Invalid ZIP file, attempting direct XML parsing for: {xml_url}")
                    temp_file.seek(0)
                    xml_content = temp_file.read()
                    root = ET.fromstring(xml_content)
                    file_results = _process_single_xml_root(root, "direct_xml")
                    total_unit_count = file_results['unit_count']
                    xml_files_processed = 1
            else:
                # Try direct XML parsing
                logger.debug(f"Attempting direct XML parsing for: {xml_url}")
                temp_file.seek(0)
                xml_content = temp_file.read()
                root = ET.fromstring(xml_content)
                file_results = _process_single_xml_root(root, "direct_xml")
                total_unit_count = file_results['unit_count']
                xml_files_processed = 1
        
        logger.info(f"Archive processing complete: {total_unit_count} total units from {xml_files_processed} XML files")
        
        return {
            'unit_count': total_unit_count,
            'xml_files_processed': xml_files_processed
        }
        
    except requests.RequestException as e:
        logger.error(f"Failed to download content from {xml_url}: {e}")
        raise XMLParsingError(f"Download failed: {e}")
    except zipfile.BadZipFile as e:
        logger.error(f"Invalid ZIP file format for {xml_url}: {e}")
        raise XMLParsingError(f"Invalid ZIP file: {e}")
    except ET.ParseError as e:
        logger.error(f"Failed to parse XML from {xml_url}: {e}")
        raise XMLParsingError(f"XML parsing failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error processing {xml_url}: {e}")
        raise XMLParsingError(f"Unexpected error: {e}")

def is_archive_first_processing(db: Session, archive_id: int, metric_type: MetricType = MetricType.DATASET_UNIT_COUNT) -> bool:
    """
    Check if an archive is being processed for the first time.
    
    This function determines whether an archive has been successfully processed before
    by checking for the presence of a 'first_processed_at' marker in the statistics
    extra_data field. Archives with processing_failed=true are treated as never 
    processed to ensure they use the correct anchor date on retry.
    
    The function is critical for the timeline enhancement feature, as it determines
    which anchor date to use:
    - First processing: Dataset's created_at date (historical anchor)
    - Subsequent processing: Current date (real-time updates)
    - Failed archives: Treated as first processing for anchor date consistency
    
    Args:
        db: Database session for querying statistics
        archive_id: ID of the archive to check processing status for
        metric_type: The metric type to check for processing history (default: DATASET_UNIT_COUNT)
        
    Returns:
        bool: True if this is the first processing (or if it previously failed), 
              False if the archive has been successfully processed before
              
    Example:
        >>> is_first = is_archive_first_processing(db, archive_id=123)
        >>> if is_first:
        ...     anchor_date = dataset.created_at.date()
        ... else:
        ...     anchor_date = date.today()
    """
    from sqlalchemy import and_, cast, String
    from sqlalchemy.dialects.postgresql import JSONB
    
    # First check if this archive has a failure record
    failure_stat = db.query(StatisticModel).filter(
        and_(
            StatisticModel.metric_type == metric_type,
            cast(StatisticModel.extra_data["archive_id"], String) == str(archive_id),
            StatisticModel.extra_data["processing_failed"].astext == "true"
        )
    ).first()
    
    if failure_stat:
        # Archive has failed before, treat as first processing for anchor date purposes
        return True
    
    # Look for any existing successful statistic that references this archive_id
    existing_stat = db.query(StatisticModel).filter(
        and_(
            StatisticModel.metric_type == metric_type,
            cast(StatisticModel.extra_data["archive_id"], String) == str(archive_id)
        )
    ).first()
    
    if existing_stat:
        # Check if it has the first_processed_at marker
        extra_data = existing_stat.extra_data or {}
        # If processing_failed is present and true, treat as first processing
        if extra_data.get('processing_failed', False):
            return True
        return 'first_processed_at' not in extra_data
    
    return True  # No existing statistics, so this is first processing  # No existing statistics, so this is first processing  # No existing statistics, so this is first processing


def mark_archive_processed(db: Session, archive_id: int, dataset_id: int, 
                          process_date: date, metric_type: MetricType = MetricType.DATASET_UNIT_COUNT) -> None:
    """
    Mark an archive as successfully processed by adding first_processed_at timestamp.
    
    This function adds a 'first_processed_at' marker to the statistics extra_data field
    when an archive is successfully processed for the first time. This marker is used
    by is_archive_first_processing() to determine whether future processing should use
    the historical anchor date or the current date.
    
    The function is idempotent - if the marker already exists, it won't be overwritten,
    preserving the original first processing timestamp for audit purposes.
    
    Args:
        db: Database session for updating statistics
        archive_id: ID of the archive being marked as processed
        dataset_id: ID of the dataset this archive belongs to
        process_date: The date used for processing (anchor date)
        metric_type: The metric type being processed (default: DATASET_UNIT_COUNT)
        
    Side Effects:
        - Updates the extra_data field of the matching StatisticModel record
        - Commits the change to the database
        - Logs the successful marking with timestamp
        
    Example:
        >>> # After successful XML processing
        >>> mark_archive_processed(db, archive_id=123, dataset_id=456, 
        ...                       process_date=date(2024, 1, 15))
        >>> # Statistics now has first_processed_at marker
        
    Note:
        This function assumes a statistic record already exists for the given
        parameters. If no matching record is found, the function returns silently
        to handle edge cases gracefully.
    """
    from sqlalchemy import and_
    
    # Find the statistic for this archive and update its extra_data
    stat = db.query(StatisticModel).filter(
        and_(
            StatisticModel.metric_type == metric_type,
            StatisticModel.entity_type == EntityType.DATASET,
            StatisticModel.entity_id == dataset_id,
            StatisticModel.date == process_date
        )
    ).first()
    
    if stat and stat.extra_data:
        # Only add first_processed_at if it doesn't exist
        if 'first_processed_at' not in stat.extra_data:
            stat.extra_data['first_processed_at'] = datetime.utcnow().isoformat()
            stat.extra_data['dataset_id'] = dataset_id  # Store dataset_id for reference
            # Mark the object as modified so SQLAlchemy knows to update it
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(stat, 'extra_data')
            logger.info(f"Marked archive {archive_id} as first processed at {stat.extra_data['first_processed_at']}")
    
    db.commit()


def get_archive_anchor_date(db: Session, archive: XmlArchiveModel) -> date:
    """
    Determine the appropriate anchor date for processing an archive's biological units.
    
    This function implements the timeline enhancement's anchor date strategy:
    - First-time processing: Uses the dataset's created_at date to place statistics
      at the historical point when the dataset was created
    - Failed archives: Uses the dataset's created_at date on retry to maintain
      consistency with the original intended timeline position
    - Subsequent processing: Uses today's date for real-time updates reflecting
      current state of the biological units
    
    The anchor date is critical for maintaining accurate historical timelines,
    especially during backfill operations where datasets may be processed long
    after their creation date.
    
    Args:
        db: Database session for checking processing status
        archive: The XmlArchiveModel instance being processed, must have a
                related dataset with created_at timestamp
        
    Returns:
        date: The anchor date to use for statistics generation
              - Dataset's created_at date for first processing/retries
              - Today's date for subsequent processing
              
    Example:
        >>> archive = db.query(XmlArchiveModel).filter_by(id=123).first()
        >>> anchor_date = get_archive_anchor_date(db, archive)
        >>> # Use anchor_date for statistics target_date
        >>> create_statistics(target_date=anchor_date, ...)
        
    Note:
        If the dataset's created_at is None (edge case), falls back to today's date
        to ensure processing can continue.
    """
    is_first = is_archive_first_processing(db, archive.id)
    failure_info = get_archive_failure_info(db, archive.id)
    
    if is_first:
        # For first processing or retries after failure, use dataset's created_at date as anchor
        anchor_date = archive.dataset.created_at.date() if archive.dataset.created_at else date.today()
        if failure_info:
            logger.info(f"Archive {archive.id} retry after {failure_info['failure_count']} failure(s): using dataset created_at {anchor_date} as anchor")
        else:
            logger.info(f"Archive {archive.id} first-time processing: using dataset created_at {anchor_date} as anchor")
    else:
        # For subsequent processing, use current date
        anchor_date = date.today()
        logger.info(f"Archive {archive.id} subsequent processing: using current date {anchor_date} as anchor")
    
    return anchor_date

def mark_archive_failed(db: Session, archive_id: int, error_message: str, 
                        metric_type: MetricType = MetricType.DATASET_UNIT_COUNT) -> None:
    """
    Mark an archive as failed and track comprehensive failure metadata.
    
    This function implements failure tracking for the resilient retry mechanism.
    It maintains a failure record with count, reason, and timestamp to support:
    - Exponential backoff calculations (based on failure_count)
    - Circuit breaker pattern (max_retries checking)
    - Time-based reset (using last_failure_at timestamp)
    
    For first failures, creates a special statistic record with a marker date (1970-01-01)
    to indicate failure state. For subsequent failures, increments the failure count
    and updates the timestamp and reason.
    
    Args:
        db: Database session for creating/updating failure records
        archive_id: ID of the archive that failed processing
        error_message: Description of the failure (e.g., "Network timeout", "Parse error")
        metric_type: The metric type being processed (default: DATASET_UNIT_COUNT)
        
    Side Effects:
        - Creates or updates a StatisticModel record with failure metadata
        - Commits the change to the database
        - Logs warning with failure count and reason
        
    Failure Tracking Fields in extra_data:
        - processing_failed: bool - Flag indicating failure state
        - failure_count: int - Number of consecutive failures
        - last_failure_reason: str - Most recent error message
        - last_failure_at: str - ISO timestamp of last failure
        
    Example:
        >>> try:
        ...     parse_abcd_xml(archive.url)
        ... except XMLParsingError as e:
        ...     mark_archive_failed(db, archive.id, str(e))
        ...     # Archive now tracked for retry with exponential backoff
        
    Note:
        Failed archives are excluded from provider aggregation totals to prevent
        corruption of timeline data. The failure_count is used to calculate
        exponential backoff delays: delay = min(60 * 2^(count-1), 3600) seconds
    """
    from sqlalchemy import and_, cast, String
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.orm.attributes import flag_modified
    
    # Find or create a failure tracking record
    # We look for a failure marker using archive_id as entity_id and special date
    existing_stat = db.query(StatisticModel).filter(
        and_(
            StatisticModel.metric_type == metric_type,
            StatisticModel.entity_type == EntityType.DATASET,
            StatisticModel.entity_id == archive_id,
            StatisticModel.date == date(1970, 1, 1)  # Failure marker date
        )
    ).first()
    
    if existing_stat:
        # Update existing failure record
        failure_count = existing_stat.extra_data.get('failure_count', 0) + 1
        existing_stat.extra_data['failure_count'] = failure_count
        existing_stat.extra_data['last_failure_reason'] = error_message[:1000]  # Truncate very long errors
        existing_stat.extra_data['last_failure_at'] = datetime.utcnow().isoformat()
        flag_modified(existing_stat, 'extra_data')
        logger.warning(f"Archive {archive_id} failed again (attempt #{failure_count}): {error_message}")
    else:
        # Create a new failure tracking record with minimal data
        # We'll use a special date far in the past to indicate failure state
        failure_marker_date = date(1970, 1, 1)
        
        failure_data = {
            'archive_id': archive_id,
            'processing_failed': True,
            'failure_count': 1,
            'last_failure_reason': error_message[:1000],  # Truncate very long errors
            'last_failure_at': datetime.utcnow().isoformat()
        }
        
        failure_stat = StatisticModel(
            metric_type=metric_type,
            entity_type=EntityType.DATASET,
            entity_id=archive_id,  # Use archive_id to ensure uniqueness
            date=failure_marker_date,
            period=Period.DAILY,
            value=0,
            extra_data=failure_data
        )
        db.add(failure_stat)
        logger.warning(f"Archive {archive_id} marked as failed (first failure): {error_message}")
    
    db.commit()


def reset_archive_failure(db: Session, archive_id: int, 
                          metric_type: MetricType = MetricType.DATASET_UNIT_COUNT) -> None:
    """
    Clear failure state for an archive after successful processing.
    
    This function removes the failure tracking record when an archive that previously
    failed is successfully processed. This is part of the resilient retry mechanism,
    allowing archives to recover from transient failures.
    
    The function is called after successful XML parsing and statistics generation
    to clean up the failure state and reset the archive for normal processing.
    
    Args:
        db: Database session for deleting failure records
        archive_id: ID of the archive that succeeded after previous failures
        metric_type: The metric type being processed (default: DATASET_UNIT_COUNT)
        
    Side Effects:
        - Deletes the failure tracking StatisticModel record if it exists
        - Commits the deletion to the database
        - Logs successful recovery with previous failure count
        
    Example:
        >>> # After successful retry
        >>> try:
        ...     result = parse_abcd_xml(archive.url)
        ...     create_statistics(result)
        ...     reset_archive_failure(db, archive.id)  # Clear failure state
        ... except Exception as e:
        ...     mark_archive_failed(db, archive.id, str(e))
        
    Note:
        This function is idempotent - calling it multiple times or when no
        failure record exists has no adverse effects. The failure record uses
        a special marker date (1970-01-01) and is completely removed rather
        than just updated to maintain database cleanliness.
    """
    from sqlalchemy import and_, cast, String
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.orm.attributes import flag_modified
    
    # Find the failure tracking record using archive_id as entity_id and special date
    failure_stat = db.query(StatisticModel).filter(
        and_(
            StatisticModel.metric_type == metric_type,
            StatisticModel.entity_type == EntityType.DATASET,
            StatisticModel.entity_id == archive_id,
            StatisticModel.date == date(1970, 1, 1)  # Failure marker date
        )
    ).first()
    
    if failure_stat:
        failure_count = failure_stat.extra_data.get('failure_count', 0)
        last_failure = failure_stat.extra_data.get('last_failure_reason', 'Unknown')
        logger.info(f"Archive {archive_id} recovered after {failure_count} failure(s). Last error was: {last_failure}")
        db.delete(failure_stat)
        db.commit()
    else:
        # No failure record exists - this is normal for archives that never failed
        logger.debug(f"No failure record found for archive {archive_id} - normal successful processing")


def get_archive_failure_info(db: Session, archive_id: int, 
                             metric_type: MetricType = MetricType.DATASET_UNIT_COUNT) -> Optional[Dict[str, Any]]:
    """
    Retrieve comprehensive failure information for an archive if it exists.
    
    This function queries the failure tracking record to get detailed information
    about an archive's failure history. The information is used to:
    - Calculate exponential backoff delays
    - Determine if max retries have been exceeded
    - Check if time-based reset period has elapsed
    - Provide debugging information in logs and API responses
    
    Args:
        db: Database session for querying failure records
        archive_id: ID of the archive to check for failure information
        metric_type: The metric type to check (default: DATASET_UNIT_COUNT)
        
    Returns:
        Optional[Dict[str, Any]]: Dictionary containing failure information or None if no failures
        
        Dictionary structure when failures exist:
        {
            'failure_count': int,          # Number of consecutive failures (1-based)
            'last_failure_reason': str,     # Error message from most recent failure
            'last_failure_at': str          # ISO timestamp of last failure
        }
        
    Example:
        >>> failure_info = get_archive_failure_info(db, archive_id=123)
        >>> if failure_info:
        ...     if failure_info['failure_count'] >= 5:
        ...         print("Max retries exceeded")
        ...     else:
        ...         # Calculate backoff delay
        ...         delay = min(60 * (2 ** (failure_info['failure_count'] - 1)), 3600)
        
    Note:
        Returns None for archives that have never failed or have been reset after
        successful processing. The last_failure_at timestamp can be parsed to
        determine if the 24-hour reset period has elapsed for circuit breaker reset.
    """
    from sqlalchemy import and_, cast, String
    
    # Query for failure tracking record with processing_failed=true
    failure_stat = db.query(StatisticModel).filter(
        and_(
            StatisticModel.metric_type == metric_type,
            cast(StatisticModel.extra_data["archive_id"], String) == str(archive_id),
            StatisticModel.extra_data["processing_failed"].astext == "true"
        )
    ).first()
    
    if failure_stat:
        return {
            'failure_count': failure_stat.extra_data.get('failure_count', 0),
            'last_failure_reason': failure_stat.extra_data.get('last_failure_reason'),
            'last_failure_at': failure_stat.extra_data.get('last_failure_at')
        }
    return None


def should_retry_failed_archive(db: Session, archive_id: int, 
                                max_retries: int = 5,
                                reset_after_hours: int = 24) -> bool:
    """
    Determine if a failed archive should be retried based on failure count and time elapsed.
    
    This function implements a sophisticated retry policy combining:
    1. **Exponential Backoff**: Retry delays increase exponentially with failure count
    2. **Circuit Breaker Pattern**: Hard stop at max_retries to prevent infinite loops
    3. **Time-Based Reset**: Allows retry after reset_after_hours even if max_retries exceeded
    
    The time-based reset ensures that archives aren't permanently abandoned due to
    temporary issues (e.g., network outages, service maintenance) while still protecting
    against persistent problems that could cause resource exhaustion.
    
    Retry Decision Logic:
    - No failures → Always retry (return True)
    - Failures < max_retries → Always retry (return True)  
    - Failures >= max_retries AND time < reset_after_hours → Skip (return False)
    - Failures >= max_retries AND time >= reset_after_hours → Allow retry (return True)
    
    Args:
        db: Database session for querying failure information
        archive_id: ID of the archive to check retry eligibility for
        max_retries: Maximum number of consecutive retries before requiring time-based reset
                    (default: 5, which with 60s base delay = max 16 min total delay)
        reset_after_hours: Hours to wait before allowing retry of max-failed archives
                          (default: 24 hours, allowing daily retry attempts)
        
    Returns:
        bool: True if the archive should be retried, False if it should be skipped
        
    Example:
        >>> # In analyze_xml_archives task
        >>> if not should_retry_failed_archive(db, archive.id):
        ...     logger.info(f"Skipping archive {archive.id} - max retries exceeded")
        ...     continue
        >>> # Proceed with processing
        
    Exponential Backoff Calculation:
        The actual retry delay (implemented elsewhere) follows:
        delay = min(60 * (2 ** (failure_count - 1)), 3600) seconds
        
        Examples:
        - 1st retry: 60 seconds
        - 2nd retry: 120 seconds
        - 3rd retry: 240 seconds
        - 4th retry: 480 seconds
        - 5th retry: 960 seconds
        - 6th+ retry: 3600 seconds (capped at 1 hour)
        
    Note:
        This function only determines eligibility for retry. The actual retry delay
        is implemented in the task execution layer using the failure_count from
        get_archive_failure_info().
    """
    failure_info = get_archive_failure_info(db, archive_id)
    
    if not failure_info:
        # No failure record, can process
        return True
    
    failure_count = failure_info['failure_count']
    
    # If under max retries, always allow retry
    if failure_count < max_retries:
        return True
    
    # Check if enough time has passed for a reset
    if failure_info['last_failure_at']:
        try:
            last_failure = datetime.fromisoformat(failure_info['last_failure_at'])
            hours_since_failure = (datetime.utcnow() - last_failure).total_seconds() / 3600
            
            if hours_since_failure >= reset_after_hours:
                logger.info(
                    f"Archive {archive_id} failed {failure_count} times but "
                    f"{hours_since_failure:.1f} hours have passed (>= {reset_after_hours}h) - allowing retry"
                )
                return True
            else:
                logger.debug(
                    f"Archive {archive_id} failed {failure_count} times and only "
                    f"{hours_since_failure:.1f} hours have passed (< {reset_after_hours}h) - skipping"
                )
                return False
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse last_failure_at for archive {archive_id}: {e}")
            # If we can't parse the timestamp, err on the side of allowing retry
            return True
    
    # No timestamp available, be conservative and skip
    return False


def check_statistics_exist(
    db: Session,
    metric_type: str,
    entity_type: str,
    entity_id: Optional[int],
    period: str
) -> bool:
    """
    Check if statistics exist for a given metric/entity combination.
    
    Args:
        db: Database session
        metric_type: Type of metric from MetricType enum
        entity_type: Type of entity from EntityType enum
        entity_id: ID of the specific entity (None for system-level)
        period: Time period from Period enum
        
    Returns:
        Boolean indicating if any statistics exist for this combination
    """
    exists = db.query(StatisticModel).filter(
        StatisticModel.metric_type == metric_type,
        StatisticModel.entity_type == entity_type,
        StatisticModel.entity_id == entity_id,
        StatisticModel.period == period
    ).first() is not None
    
    logger.debug(
        f"Statistics exist check - metric: {metric_type}, entity: {entity_type}, "
        f"entity_id: {entity_id}, period: {period} - Result: {exists}"
    )
    
    return exists


def generate_backfill_dates(
    entity_created_at: datetime,
    target_date: date
) -> List[date]:
    """
    Generate a list of dates from entity creation to target date for backfilling.
    
    Args:
        entity_created_at: The creation timestamp of the entity
        target_date: The current collection date
        
    Returns:
        List of dates from entity creation to target date (inclusive)
    """
    start_date = entity_created_at.date() if isinstance(entity_created_at, datetime) else entity_created_at
    dates = []
    current = start_date
    
    while current <= target_date:
        dates.append(current)
        current += timedelta(days=1)
    
    logger.info(
        f"Generated {len(dates)} backfill dates from {start_date} to {target_date}"
    )
    
    return dates

def get_cumulative_count(
    db: Session,
    model,
    target_date: date,
    filter_conditions=None
) -> int:
    """
    Get cumulative count of entities up to and including target date.
    
    Args:
        db: Database session
        model: SQLAlchemy model to count
        target_date: The date to count up to (inclusive)
        filter_conditions: Additional filter conditions
        
    Returns:
        Count of entities created up to target date
    """
    # Convert target_date to end of day datetime for proper comparison
    end_of_day = datetime.combine(target_date, datetime.max.time())
    
    query = db.query(func.count(model.id)).filter(
        model.created_at <= end_of_day
    )
    
    if filter_conditions is not None:
        query = query.filter(filter_conditions)
    
    return query.scalar() or 0

def get_cumulative_xml_archive_count(
    db: Session,
    target_date: date
) -> int:
    """
    Get cumulative count of XML archives up to and including target date.
    Since XmlArchiveModel doesn't have created_at, we count based on the 
    dataset's created_at date.
    
    Args:
        db: Database session
        target_date: The date to count up to (inclusive)
        
    Returns:
        Count of XML archives whose datasets were created up to target date
    """
    # Convert target_date to end of day datetime for proper comparison
    end_of_day = datetime.combine(target_date, datetime.max.time())
    
    # Join with DatasetModel to access created_at
    count = db.query(func.count(XmlArchiveModel.id)).join(
        DatasetModel, XmlArchiveModel.dataset_id == DatasetModel.id
    ).filter(
        DatasetModel.created_at <= end_of_day
    ).scalar()
    
    return count or 0


def perform_statistics_upsert(
    db: Session,
    metric_type: str,
    entity_type: str,
    entity_id: Optional[int],
    period: str,
    date_value: date,
    value: float,
    extra_data: Dict[str, Any],
    log_message: str = None
) -> None:
    """
    Perform an upsert operation for a statistic entry.
    
    Args:
        db: Database session
        metric_type: Type of metric from MetricType enum
        entity_type: Type of entity from EntityType enum
        entity_id: ID of the specific entity (None for system-level)
        period: Time period from Period enum
        date_value: The date this statistic represents
        value: The numeric value of the metric
        extra_data: Additional context data
        log_message: Optional log message for debugging
    """
    from sqlalchemy.dialects.postgresql import insert
    
    stmt = insert(StatisticModel).values(
        metric_type=metric_type,
        entity_type=entity_type,
        entity_id=entity_id,
        period=period,
        date=date_value,
        value=value,
        extra_data=extra_data,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    stmt = stmt.on_conflict_do_update(
        constraint='uq_statistics_unique_entry',
        set_={
            'value': stmt.excluded.value,
            'extra_data': stmt.excluded.extra_data,
            'updated_at': datetime.utcnow()
        }
    )
    
    db.execute(stmt)
    
    if log_message:
        logger.debug(log_message)

def detect_statistics_gaps(
    db: Session,
    target_date: date,
    max_gap_days: int = 30
) -> List[date]:
    """
    Detect ALL gaps in daily statistics up to and including the target date.
    
    This function identifies all missing dates where statistics should exist but don't,
    including both trailing gaps (at the end) and intermittent gaps (in the middle).
    
    Args:
        db: Database session
        target_date: The date up to which we want statistics (inclusive)
        max_gap_days: Maximum number of days to backfill at once (safety limit)
        
    Returns:
        List of dates that are missing statistics, ordered from oldest to newest
    """
    from sqlalchemy import and_, func, distinct
    
    # Find the earliest date we should have statistics for
    earliest_dataset = db.query(func.min(DatasetModel.created_at)).scalar()
    earliest_provider = db.query(func.min(DataProviderModel.created_at)).scalar()
    earliest_archive = db.query(func.min(DatasetModel.created_at)).join(
        XmlArchiveModel, XmlArchiveModel.dataset_id == DatasetModel.id
    ).scalar()
    
    earliest_dates = [d for d in [earliest_dataset, earliest_provider, earliest_archive] if d]
    
    if not earliest_dates:
        logger.debug("No data exists yet for gap detection")
        return []
    
    earliest_date = min(earliest_dates).date()
    
    # Get all dates that currently have system-level statistics
    existing_dates = db.query(distinct(StatisticModel.date)).filter(
        and_(
            StatisticModel.entity_type == EntityType.SYSTEM,
            StatisticModel.period == Period.DAILY,
            StatisticModel.metric_type.in_([
                MetricType.DATASET_COUNT,
                MetricType.PROVIDER_COUNT,
                MetricType.XML_ARCHIVE_COUNT
            ]),
            StatisticModel.date >= earliest_date,
            StatisticModel.date <= target_date
        )
    ).all()
    
    existing_dates_set = {row[0] for row in existing_dates}
    
    # Generate all dates that should have statistics
    expected_dates = []
    current = earliest_date
    while current <= target_date:
        expected_dates.append(current)
        current += timedelta(days=1)
    
    # Find missing dates
    missing_dates = [d for d in expected_dates if d not in existing_dates_set]
    
    if not missing_dates:
        logger.debug(f"No gaps found in statistics up to {target_date}")
        return []
    
    # Apply safety limit to prevent processing too many days at once
    if len(missing_dates) > max_gap_days:
        logger.warning(
            f"Found {len(missing_dates)} missing dates, exceeds maximum of {max_gap_days}. "
            f"Limiting to most recent {max_gap_days} days."
        )
        # Sort by date and take the most recent ones
        missing_dates.sort()
        missing_dates = missing_dates[-max_gap_days:]
    
    # Sort chronologically for processing
    missing_dates.sort()
    
    logger.info(
        f"Detected {len(missing_dates)} missing dates in statistics: "
        f"from {missing_dates[0]} to {missing_dates[-1]}"
    )
    
    return missing_dates

@shared_task(
    bind=True,
    base=LoggingTask,  # Use custom base class for enhanced logging
    name="statistics.collect_daily_stats",
    queue='light_tasks',
    max_retries=3,
    soft_time_limit=1800,  # 30 minutes timeout
    retry_backoff=True,
    retry_backoff_max=120,  # Maximum backoff in seconds (2 minutes)
    retry_jitter=True,  # Add randomization to prevent thundering herd
    autoretry_for=(Exception,),  # Auto-retry on all exceptions
    task_time_limit=1900,  # Hard time limit (31min 40s)
)
def collect_daily_statistics(self, target_date: str = None) -> Dict[str, Any]:
    """
    Collect daily statistics for datasets, providers, and validation jobs.
    Implements backfill-then-update pattern using model timestamps.
    Now includes automatic gap detection and filling.
    
    Queue Assignment: Routes to 'light_tasks' queue for lightweight statistical
    calculations using prefork worker pool optimized for CPU-bound operations.
    
    Args:
        target_date: Date string in YYYY-MM-DD format (defaults to yesterday)
        
    Returns:
        Dictionary with collection results
    """
    db = SessionLocal()
    
    try:
        # Parse target date
        if target_date:
            primary_target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            primary_target_date = date.today() - timedelta(days=1)
        
        logger.info(f"Starting statistics collection with target date: {primary_target_date}")
        
        # Collect all dates that need processing
        dates_to_process = []
        gap_dates = []
        is_initial_backfill = False
        
        # Check if this is an initial backfill scenario (no statistics exist)
        stats_exist = check_statistics_exist(
            db, MetricType.DATASET_COUNT, EntityType.SYSTEM, None, Period.DAILY
        )
        
        if not stats_exist:
            # Initial backfill scenario - process from beginning to target date
            is_initial_backfill = True
            logger.info("No existing statistics found - performing initial backfill")
            
            # Get the earliest creation dates
            earliest_dataset = db.query(func.min(DatasetModel.created_at)).scalar()
            earliest_provider = db.query(func.min(DataProviderModel.created_at)).scalar()
            earliest_archive = db.query(func.min(DatasetModel.created_at)).join(
                XmlArchiveModel, XmlArchiveModel.dataset_id == DatasetModel.id
            ).scalar()
            
            system_start_dates = [d for d in [earliest_dataset, earliest_provider, earliest_archive] if d]
            system_start_date = min(system_start_dates).date() if system_start_dates else primary_target_date
            
            # Generate all dates for initial backfill
            dates_to_process = generate_backfill_dates(system_start_date, primary_target_date)
            logger.info(f"Initial backfill will process {len(dates_to_process)} dates from {system_start_date} to {primary_target_date}")
            
        else:
            # Statistics exist - check for gaps
            gap_dates = detect_statistics_gaps(db, primary_target_date)
            
            if gap_dates:
                logger.info(f"Detected {len(gap_dates)} missing dates to fill before processing target date")
                dates_to_process.extend(gap_dates)
            
            # Always process the primary target date last
            dates_to_process.append(primary_target_date)
        
        # Process statistics collection for each date
        total_collected_stats = []
        total_backfill_info = []
        dates_processed = []
        
        for stat_date in dates_to_process:
            logger.info(f"Processing statistics for date: {stat_date}")
            collected_stats = []
            backfill_performed = []
            
            # Get the earliest creation date for system-wide metrics
            earliest_dataset = db.query(func.min(DatasetModel.created_at)).scalar()
            earliest_provider = db.query(func.min(DataProviderModel.created_at)).scalar()
            earliest_archive = db.query(func.min(DatasetModel.created_at)).join(
                XmlArchiveModel, XmlArchiveModel.dataset_id == DatasetModel.id
            ).scalar()
            
            system_start_dates = [d for d in [earliest_dataset, earliest_provider, earliest_archive] if d]
            system_start_date = min(system_start_dates).date() if system_start_dates else stat_date
            
            # System-wide statistics
            
            # 1. Total datasets
            count = get_cumulative_count(db, DatasetModel, stat_date)
            perform_statistics_upsert(
                db=db,
                metric_type=MetricType.DATASET_COUNT,
                entity_type=EntityType.SYSTEM,
                entity_id=None,
                period=Period.DAILY,
                date_value=stat_date,
                value=count,
                extra_data={
                    'collection_timestamp': datetime.utcnow().isoformat(),
                    'gap_fill': stat_date in gap_dates,
                    'initial_backfill': is_initial_backfill
                },
                log_message=f"{'Gap-fill' if stat_date in gap_dates else 'Updated'} DATASET_COUNT for {stat_date}: {count}"
            )
            collected_stats.append(f"System dataset count: {count}")
            
            # 2. Total providers
            count = get_cumulative_count(db, DataProviderModel, stat_date)
            perform_statistics_upsert(
                db=db,
                metric_type=MetricType.PROVIDER_COUNT,
                entity_type=EntityType.SYSTEM,
                entity_id=None,
                period=Period.DAILY,
                date_value=stat_date,
                value=count,
                extra_data={
                    'collection_timestamp': datetime.utcnow().isoformat(),
                    'gap_fill': stat_date in gap_dates,
                    'initial_backfill': is_initial_backfill
                },
                log_message=f"{'Gap-fill' if stat_date in gap_dates else 'Updated'} PROVIDER_COUNT for {stat_date}: {count}"
            )
            collected_stats.append(f"System provider count: {count}")
            
            # 3. Total XML archives
            count = get_cumulative_xml_archive_count(db, stat_date)
            perform_statistics_upsert(
                db=db,
                metric_type=MetricType.XML_ARCHIVE_COUNT,
                entity_type=EntityType.SYSTEM,
                entity_id=None,
                period=Period.DAILY,
                date_value=stat_date,
                value=count,
                extra_data={
                    'collection_timestamp': datetime.utcnow().isoformat(),
                    'gap_fill': stat_date in gap_dates,
                    'initial_backfill': is_initial_backfill
                },
                log_message=f"{'Gap-fill' if stat_date in gap_dates else 'Updated'} XML_ARCHIVE_COUNT for {stat_date}: {count}"
            )
            collected_stats.append(f"System XML archive count: {count}")
            
            # Validation statistics (rolling window - always current)
            week_ago = stat_date - timedelta(days=7)
            validation_jobs = db.query(ValidationJobModel).filter(
                ValidationJobModel.created_at >= week_ago
            ).all()
            
            if validation_jobs:
                total_jobs = len(validation_jobs)
                successful_jobs = len([job for job in validation_jobs 
                                     if job.status == 'completed' and job.valid_files == job.total_files and job.total_files > 0])
                success_rate = (successful_jobs / total_jobs) * 100 if total_jobs > 0 else 0
                
                avg_processing_time = 0
                completed_jobs = [job for job in validation_jobs if job.status == 'completed']
                if completed_jobs:
                    processing_times = [job.validation_time for job in completed_jobs 
                                      if job.validation_time is not None]
                    if processing_times:
                        avg_processing_time = sum(processing_times) / len(processing_times)
                
                perform_statistics_upsert(
                    db=db,
                    metric_type=MetricType.VALIDATION_SUCCESS_RATE,
                    entity_type=EntityType.SYSTEM,
                    entity_id=None,
                    period=Period.DAILY,
                    date_value=stat_date,
                    value=success_rate,
                    extra_data={
                        'total_jobs': total_jobs,
                        'successful_jobs': successful_jobs,
                        'period_days': 7,
                        'collection_timestamp': datetime.utcnow().isoformat(),
                        'gap_fill': stat_date in gap_dates
                    },
                    log_message=f"{'Gap-fill' if stat_date in gap_dates else 'Updated'} VALIDATION_SUCCESS_RATE for {stat_date}: {success_rate:.1f}%"
                )
                collected_stats.append(f"System validation success rate: {success_rate:.1f}%")
                
                perform_statistics_upsert(
                    db=db,
                    metric_type=MetricType.VALIDATION_PROCESSING_TIME,
                    entity_type=EntityType.SYSTEM,
                    entity_id=None,
                    period=Period.DAILY,
                    date_value=stat_date,
                    value=avg_processing_time,
                    extra_data={
                        'jobs_included': len([j for j in validation_jobs if j.validation_time is not None]),
                        'collection_timestamp': datetime.utcnow().isoformat(),
                        'gap_fill': stat_date in gap_dates
                    },
                    log_message=f"{'Gap-fill' if stat_date in gap_dates else 'Updated'} VALIDATION_PROCESSING_TIME for {stat_date}: {avg_processing_time:.2f}s"
                )
                collected_stats.append(f"System avg processing time: {avg_processing_time:.2f}s")
            
            # Provider-specific statistics
            providers = db.query(DataProviderModel).all()
            
            for provider in providers:
                provider_start_date = provider.created_at.date() if provider.created_at else stat_date
                
                # Skip if provider didn't exist on this date
                if provider_start_date > stat_date:
                    continue
                
                # Provider dataset count
                count = get_cumulative_count(
                    db, DatasetModel, stat_date,
                    filter_conditions=(DatasetModel.provider_id == provider.id)
                )
                perform_statistics_upsert(
                    db=db,
                    metric_type=MetricType.PROVIDER_DATASET_COUNT,
                    entity_type=EntityType.PROVIDER,
                    entity_id=provider.id,
                    period=Period.DAILY,
                    date_value=stat_date,
                    value=count,
                    extra_data={
                        'provider_name': provider.name,
                        'provider_datacenter': provider.datacenter,
                        'collection_timestamp': datetime.utcnow().isoformat(),
                        'gap_fill': stat_date in gap_dates,
                        'initial_backfill': is_initial_backfill
                    },
                    log_message=f"{'Gap-fill' if stat_date in gap_dates else 'Updated'} PROVIDER_DATASET_COUNT for provider {provider.id} on {stat_date}: {count}"
                )
                
                # Provider biological units
                dataset_ids = db.query(DatasetModel.id).filter(
                    and_(
                        DatasetModel.provider_id == provider.id,
                        DatasetModel.created_at <= datetime.combine(stat_date, datetime.max.time())
                    )
                ).all()
                
                if not dataset_ids:
                    provider_biological_units = 0
                else:
                    dataset_id_list = [dataset_id[0] for dataset_id in dataset_ids]
                    
                    subquery = db.query(
                        StatisticModel.entity_id,
                        func.max(StatisticModel.date).label('max_date')
                    ).filter(
                        and_(
                            StatisticModel.metric_type == MetricType.DATASET_UNIT_COUNT,
                            StatisticModel.entity_type == EntityType.DATASET,
                            StatisticModel.entity_id.in_(dataset_id_list),
                            StatisticModel.date <= stat_date
                        )
                    ).group_by(StatisticModel.entity_id).subquery()
                    
                    recent_unit_counts = db.query(StatisticModel.value).join(
                        subquery,
                        and_(
                            StatisticModel.entity_id == subquery.c.entity_id,
                            StatisticModel.date == subquery.c.max_date
                        )
                    ).filter(
                        StatisticModel.metric_type == MetricType.DATASET_UNIT_COUNT
                    ).all()
                    
                    provider_biological_units = sum(count[0] for count in recent_unit_counts if count[0] is not None)
                
                perform_statistics_upsert(
                    db=db,
                    metric_type=MetricType.PROVIDER_BIOLOGICAL_UNITS,
                    entity_type=EntityType.PROVIDER,
                    entity_id=provider.id,
                    period=Period.DAILY,
                    date_value=stat_date,
                    value=provider_biological_units,
                    extra_data={
                        'provider_name': provider.name,
                        'provider_datacenter': provider.datacenter,
                        'dataset_count': len(dataset_ids),
                        'collection_timestamp': datetime.utcnow().isoformat(),
                        'gap_fill': stat_date in gap_dates,
                        'initial_backfill': is_initial_backfill
                    },
                    log_message=f"{'Gap-fill' if stat_date in gap_dates else 'Updated'} PROVIDER_BIOLOGICAL_UNITS for provider {provider.id} on {stat_date}: {provider_biological_units}"
                )
            
            # Dataset registration and modification rates
            start_of_day = datetime.combine(stat_date, datetime.min.time())
            end_of_day = datetime.combine(stat_date, datetime.max.time())
            
            new_datasets_count = db.query(func.count(DatasetModel.id)).filter(
                and_(
                    DatasetModel.created_at >= start_of_day,
                    DatasetModel.created_at <= end_of_day
                )
            ).scalar()
            
            perform_statistics_upsert(
                db=db,
                metric_type=MetricType.DATASET_REGISTRATION_RATE,
                entity_type=EntityType.SYSTEM,
                entity_id=None,
                period=Period.DAILY,
                date_value=stat_date,
                value=new_datasets_count,
                extra_data={
                    'period_start': start_of_day.isoformat(),
                    'period_end': end_of_day.isoformat(),
                    'collection_timestamp': datetime.utcnow().isoformat(),
                    'gap_fill': stat_date in gap_dates
                },
                log_message=f"Dataset registration rate for {stat_date}: {new_datasets_count}"
            )
            collected_stats.append(f"New datasets on {stat_date}: {new_datasets_count}")
            
            modified_datasets_count = db.query(func.count(distinct(DatasetModel.id))).filter(
                and_(
                    DatasetModel.updated_at >= start_of_day,
                    DatasetModel.updated_at <= end_of_day,
                    DatasetModel.created_at < start_of_day  # Exclude new datasets
                )
            ).scalar()
            
            perform_statistics_upsert(
                db=db,
                metric_type=MetricType.DATASET_MODIFICATION_RATE,
                entity_type=EntityType.SYSTEM,
                entity_id=None,
                period=Period.DAILY,
                date_value=stat_date,
                value=modified_datasets_count,
                extra_data={
                    'period_start': start_of_day.isoformat(),
                    'period_end': end_of_day.isoformat(),
                    'collection_timestamp': datetime.utcnow().isoformat(),
                    'gap_fill': stat_date in gap_dates
                },
                log_message=f"Dataset modification rate for {stat_date}: {modified_datasets_count}"
            )
            collected_stats.append(f"Modified datasets on {stat_date}: {modified_datasets_count}")
            
            # Track what we did for this date
            dates_processed.append(stat_date)
            total_collected_stats.extend(collected_stats)
            
            if stat_date in gap_dates:
                logger.info(f"Successfully filled gap for date: {stat_date}")
        
        # Commit all statistics
        db.commit()
        
        # Log comprehensive summary
        summary_message = f"Successfully collected statistics for {len(dates_processed)} date(s)"
        if gap_dates:
            summary_message += f" (including {len(gap_dates)} gap-filled dates)"
        if is_initial_backfill:
            summary_message += " (initial backfill completed)"
        
        logger.info(summary_message)
        
        return {
            'status': 'completed',
            'primary_target_date': primary_target_date.isoformat(),
            'dates_processed': [d.isoformat() for d in dates_processed],
            'gap_dates_filled': [d.isoformat() for d in gap_dates],
            'initial_backfill': is_initial_backfill,
            'total_dates_processed': len(dates_processed),
            'statistics_collected': len(total_collected_stats),
            'task_id': self.request.id,
            'completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception(f"Error collecting daily statistics: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    base=LoggingTask,  # Use custom base class for enhanced logging
    name="statistics.analyze_xml_archives",
    queue='light_tasks',
    max_retries=2,
    soft_time_limit=3600,  # 1 hour timeout
    retry_backoff=True,
    retry_backoff_max=120,  # Maximum backoff in seconds (2 minutes)
    retry_jitter=True,  # Add randomization to prevent thundering herd
    autoretry_for=(Exception,),  # Auto-retry on all exceptions
    task_time_limit=3700,  # Hard time limit (1h 1min 40s)
)
def analyze_xml_archives(self, batch_size: int = 50, offset: int = 0, dataset_ids: Optional[List[int]] = None, target_date: str = None) -> Dict[str, Any]:
    """
    Analyze XML archives to extract unit counts and metadata.
    Processes archives in batches to avoid memory issues.
    
    Queue Assignment: Routes to 'light_tasks' queue for statistical data extraction
    using prefork worker pool optimized for CPU-bound operations.
    
    Args:
        batch_size: Number of archives to process in this batch
        offset: Starting offset for the batch
        dataset_ids: Optional list of specific dataset IDs to process
        target_date: Optional date string in YYYY-MM-DD format for override (mainly for testing)
        
    Returns:
        Dictionary with analysis results
    """
    from sqlalchemy.dialects.postgresql import insert
    
    db = SessionLocal()
    
    try:
        if dataset_ids:
            logger.info(f"Analyzing XML archives for specific datasets: {dataset_ids}")
        else:
            logger.info(f"Analyzing XML archives - batch size: {batch_size}, offset: {offset}")
        logger.info(f"[DB-DEBUG] Created new database session: is_active={db.is_active}")
        
        # Parse target date if provided (mainly for testing/backfill scenarios)
        override_date = None
        if target_date:
            override_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            logger.info(f"Using override date: {override_date}")
        
        # Get batch of LATEST archives to analyze (respecting system constraint)
        query = db.query(XmlArchiveModel).filter(
            XmlArchiveModel.isLatest == True
        )
        
        # If specific dataset IDs are provided, filter by them
        if dataset_ids:
            query = query.filter(XmlArchiveModel.dataset_id.in_(dataset_ids))
            archives = query.order_by(XmlArchiveModel.id).all()
        else:
            # Use offset/limit for batch processing of all archives
            archives = query.order_by(XmlArchiveModel.id).offset(offset).limit(batch_size).all()
        
        logger.info(f"[DB-DEBUG] Found {len(archives)} archives to process in this batch")
        
        if not archives:
            return {
                'status': 'completed',
                'message': 'No more archives to process',
                'processed': 0,
                'batch_size': batch_size,
                'offset': offset
            }
        
        processed_count = 0
        error_count = 0
        skipped_count = 0
        results = []
        max_retries = 5
        
        for archive in archives:
            # Check if this archive should be retried (time-based circuit breaker)
            if not should_retry_failed_archive(db, archive.id, max_retries=max_retries, reset_after_hours=24):
                failure_info = get_archive_failure_info(db, archive.id)
                skipped_count += 1
                logger.warning(
                    f"Skipping archive {archive.id} - exceeded max retries ({max_retries}) "
                    f"and waiting period not elapsed (24h)"
                )
                results.append({
                    'archive_id': archive.id,
                    'dataset_id': archive.dataset_id,
                    'status': 'skipped',
                    'reason': f"Exceeded max retries ({max_retries}), retry after 24h",
                    'failure_count': failure_info['failure_count'] if failure_info else 0,
                    'last_failure': failure_info['last_failure_reason'] if failure_info else None,
                    'last_failure_at': failure_info['last_failure_at'] if failure_info else None
                })
                continue
            try:
                logger.info(f"[DB-DEBUG] Starting analysis of archive {archive.id} (dataset {archive.dataset_id})")
                
                # Determine anchor date for this archive
                if override_date:
                    # Use override date if provided (for testing/backfill)
                    anchor_date = override_date
                    logger.info(f"Using override date {anchor_date} for archive {archive.id}")
                else:
                    # Use anchor date logic based on first-time vs subsequent processing
                    anchor_date = get_archive_anchor_date(db, archive)
                
                # Parse XML and extract information
                xml_data = parse_abcd_xml(archive.url)
                logger.info(f"[DB-DEBUG] Parsed XML data for archive {archive.id}: unit_count={xml_data['unit_count']}, files_processed={xml_data.get('xml_files_processed', 1)}")
                
                # Store unit count statistic - use proper upsert with ON CONFLICT
                if xml_data['unit_count'] > 0:
                    logger.info(f"[DB-DEBUG] DB session state before unit count insert: is_active={db.is_active}")
                    
                    # Check if this is first processing to include in extra_data
                    is_first = is_archive_first_processing(db, archive.id)
                    
                    extra_data = {
                        'archive_id': archive.id,
                        'archive_url': archive.url,
                        'xml_files_processed': xml_data.get('xml_files_processed', 1),
                        'anchor_date_used': anchor_date.isoformat()
                    }
                    
                    # Add first_processed_at if this is the first processing
                    if is_first:
                        extra_data['first_processed_at'] = datetime.utcnow().isoformat()
                        logger.info(f"Archive {archive.id} marked as first processed at {extra_data['first_processed_at']}")
                    
                    stmt = insert(StatisticModel).values(
                        metric_type=MetricType.DATASET_UNIT_COUNT,
                        entity_type=EntityType.DATASET,
                        entity_id=archive.dataset_id,
                        period=Period.DAILY,
                        date=anchor_date,  # Use anchor date instead of date.today()
                        value=xml_data['unit_count'],
                        extra_data=extra_data,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    stmt = stmt.on_conflict_do_update(
                        constraint='uq_statistics_unique_entry',
                        set_={
                            'value': stmt.excluded.value,
                            'extra_data': stmt.excluded.extra_data,
                            'updated_at': datetime.utcnow()
                        }
                    )
                    
                    logger.info(f"[DB-DEBUG] Executing unit count upsert for archive {archive.id}, dataset {archive.dataset_id}, value={xml_data['unit_count']}, date={anchor_date}")
                    logger.info(f"[DB-DEBUG] Using constraint 'uq_statistics_unique_entry' for upsert")
                    result = db.execute(stmt)
                    logger.info(f"[DB-DEBUG] Unit count upsert result: {result}, rowcount={getattr(result, 'rowcount', 'N/A')}")
                    logger.info(f"[DB-DEBUG] DB session state after unit count execute: is_active={db.is_active}, dirty={len(db.dirty)}, new={len(db.new)}")
                else:
                    logger.warning(f"[DB-DEBUG] Skipping unit count insert for archive {archive.id} - unit_count is {xml_data['unit_count']}")
                
                # Citation completeness and geographic coverage have been removed
                # We now only extract and store unit counts for performance
                
                # Clear any previous failure state on successful processing
                reset_archive_failure(db, archive.id)
                
                results.append({
                    'archive_id': archive.id,
                    'dataset_id': archive.dataset_id,
                    'unit_count': xml_data['unit_count'],
                    'anchor_date': anchor_date.isoformat(),
                    'is_first_processing': is_archive_first_processing(db, archive.id),
                    'status': 'success'
                })
                
                processed_count += 1
                logger.info(f"Successfully analyzed archive {archive.id}: {xml_data['unit_count']} units from {xml_data.get('xml_files_processed', 1)} XML files using anchor date {anchor_date}")
                
            except XMLParsingError as e:
                error_count += 1
                error_message = str(e)
                
                # Track the failure
                mark_archive_failed(db, archive.id, error_message)
                failure_info = get_archive_failure_info(db, archive.id)
                failure_count = failure_info['failure_count'] if failure_info else 1
                
                logger.warning(f"[DB-DEBUG] XMLParsingError for archive {archive.id} (attempt #{failure_count}): {error_message}")
                logger.info(f"[DB-DEBUG] DB session state after XMLParsingError: is_active={db.is_active}, dirty={len(db.dirty)}, new={len(db.new)}")
                
                # Check if we should retry with exponential backoff
                max_retries = 5
                if failure_count < max_retries:
                    # Calculate exponential backoff delay
                    base_delay = 60  # Start with 1 minute
                    retry_delay = min(base_delay * (2 ** (failure_count - 1)), 3600)  # Cap at 1 hour
                    
                    logger.info(f"Archive {archive.id} will be retried (attempt #{failure_count + 1}/{max_retries}) after {retry_delay} seconds")
                    # Note: The retry will happen in the next scheduled run with the correct anchor date
                else:
                    logger.error(f"Archive {archive.id} exceeded max retries ({max_retries}), marking as permanently failed")
                
                results.append({
                    'archive_id': archive.id,
                    'dataset_id': archive.dataset_id,
                    'error': error_message,
                    'status': 'error',
                    'failure_count': failure_count,
                    'will_retry': failure_count < max_retries
                })
                
            except Exception as e:
                error_count += 1
                error_message = str(e)
                
                # Track the failure
                mark_archive_failed(db, archive.id, error_message)
                failure_info = get_archive_failure_info(db, archive.id)
                failure_count = failure_info['failure_count'] if failure_info else 1
                
                logger.error(f"[DB-DEBUG] Unexpected error processing archive {archive.id} (attempt #{failure_count}): {error_message}")
                logger.error(f"[DB-DEBUG] Exception type: {type(e).__name__}")
                logger.info(f"[DB-DEBUG] DB session state after unexpected error: is_active={db.is_active}, dirty={len(db.dirty)}, new={len(db.new)}")
                
                # Check if this is a database-related exception
                if hasattr(e, 'statement') or 'database' in str(e).lower() or 'postgresql' in str(e).lower():
                    logger.error(f"[DB-DEBUG] DATABASE-RELATED EXCEPTION DETECTED: {e}")
                
                # Check if we should retry with exponential backoff
                max_retries = 5
                if failure_count < max_retries:
                    # Calculate exponential backoff delay
                    base_delay = 60  # Start with 1 minute
                    retry_delay = min(base_delay * (2 ** (failure_count - 1)), 3600)  # Cap at 1 hour
                    
                    logger.info(f"Archive {archive.id} will be retried (attempt #{failure_count + 1}/{max_retries}) after {retry_delay} seconds")
                    # Note: The retry will happen in the next scheduled run with the correct anchor date
                else:
                    logger.error(f"Archive {archive.id} exceeded max retries ({max_retries}), marking as permanently failed")
                
                results.append({
                    'archive_id': archive.id,
                    'dataset_id': archive.dataset_id,
                    'error': error_message,
                    'status': 'error',
                    'failure_count': failure_count,
                    'will_retry': failure_count < max_retries
                })
        
        # Commit statistics
        logger.info(f"[DB-DEBUG] Pre-commit DB session state: is_active={db.is_active}, dirty={len(db.dirty)}, new={len(db.new)}")
        logger.info(f"[DB-DEBUG] Attempting to commit {processed_count} processed archives with statistics to database")
        
        try:
            db.commit()
            logger.info(f"[DB-DEBUG] Successfully committed database transaction")
            logger.info(f"[DB-DEBUG] Post-commit DB session state: is_active={db.is_active}, dirty={len(db.dirty)}, new={len(db.new)}")
            
            # Verify data was actually persisted by querying it back
            if processed_count > 0:
                from sqlalchemy import and_
                # Note: We can't easily verify by date anymore since we use different anchor dates
                # Instead verify by checking for our specific archives
                for result in results[:3]:  # Check first few successful results
                    if result['status'] == 'success':
                        specific_stat = db.query(StatisticModel).filter(
                            and_(
                                StatisticModel.metric_type == MetricType.DATASET_UNIT_COUNT,
                                StatisticModel.entity_type == EntityType.DATASET,
                                StatisticModel.entity_id == result['dataset_id'],
                                StatisticModel.date == datetime.strptime(result['anchor_date'], "%Y-%m-%d").date()
                            )
                        ).first()
                        if specific_stat:
                            logger.info(f"[DB-DEBUG] Verification successful: Found statistic for dataset {result['dataset_id']} with value {specific_stat.value} at date {result['anchor_date']}")
                        else:
                            logger.error(f"[DB-DEBUG] VERIFICATION FAILED: No statistic found for dataset {result['dataset_id']} at date {result['anchor_date']} that we just processed!")
                        
        except Exception as commit_error:
            logger.error(f"[DB-DEBUG] COMMIT FAILED: {commit_error}")
            logger.error(f"[DB-DEBUG] DB session state during commit failure: is_active={db.is_active}, dirty={len(db.dirty)}, new={len(db.new)}")
            raise
        
        logger.info(f"XML analysis batch completed - processed: {processed_count}, errors: {error_count}, skipped: {skipped_count}")
        
        # Log a summary of failed archives for monitoring
        failed_archives = [r for r in results if r['status'] == 'error']
        if failed_archives:
            logger.warning(f"Failed archives in this batch: {len(failed_archives)} - IDs: {[r['archive_id'] for r in failed_archives]}")
        
        # Schedule next batch if there were results (but not when processing specific datasets)
        if len(archives) == batch_size and not dataset_ids:
            # There might be more archives to process
            analyze_xml_archives.delay(batch_size=batch_size, offset=offset + batch_size, target_date=target_date)
        
        return {
            'status': 'completed',
            'batch_size': batch_size,
            'offset': offset,
            'processed': processed_count,
            'errors': error_count,
            'skipped': skipped_count,
            'has_more': len(archives) == batch_size,
            'results': results,
            'task_id': self.request.id,
            'completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception(f"[DB-DEBUG] CRITICAL ERROR in XML analysis batch: {e}")
        logger.error(f"[DB-DEBUG] Exception type: {type(e).__name__}")
        logger.error(f"[DB-DEBUG] DB session state during critical error: is_active={db.is_active}, dirty={len(db.dirty)}, new={len(db.new)}")
        
        try:
            logger.info(f"[DB-DEBUG] Attempting rollback due to critical error")
            db.rollback()
            logger.info(f"[DB-DEBUG] Rollback successful")
        except Exception as rollback_error:
            logger.error(f"[DB-DEBUG] ROLLBACK FAILED: {rollback_error}")
        
        raise
    finally:
        logger.debug(f"[DB-DEBUG] Closing database session")
        try:
            db.close()
            logger.debug(f"[DB-DEBUG] Database session closed successfully")
        except Exception as close_error:
            logger.error(f"[DB-DEBUG] Error closing database session: {close_error}")


@shared_task(
    bind=True,
    base=LoggingTask,  # Use custom base class for enhanced logging
    name="statistics.aggregate_weekly_stats",
    queue='light_tasks',
    max_retries=3,
    soft_time_limit=1800,  # 30 minutes timeout
    retry_backoff=True,
    retry_backoff_max=120,  # Maximum backoff in seconds (2 minutes)
    retry_jitter=True,  # Add randomization to prevent thundering herd
    autoretry_for=(Exception,),  # Auto-retry on all exceptions
    task_time_limit=1900,  # Hard time limit (31min 40s)
)
def aggregate_weekly_statistics(self, target_date: str = None) -> Dict[str, Any]:
    """
    Aggregate weekly statistics from daily data.
    
    Queue Assignment: Routes to 'light_tasks' queue for lightweight aggregation
    calculations using prefork worker pool optimized for CPU-bound operations.
    
    Args:
        target_date: Date string in YYYY-MM-DD format (defaults to last Sunday)
        
    Returns:
        Dictionary with aggregation results
    """
    db = SessionLocal()
    
    try:
        # Calculate target week ending date (Sunday)
        if target_date:
            end_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            today = date.today()
            days_since_sunday = today.weekday() + 1  # Monday = 0, Sunday = 6
            if days_since_sunday == 7:  # Today is Sunday
                days_since_sunday = 0
            end_date = today - timedelta(days=days_since_sunday)
        
        start_date = end_date - timedelta(days=6)  # Week starts on Monday
        
        logger.info(f"Aggregating weekly statistics for week {start_date} to {end_date}")
        
        aggregated_stats = []
        
        # Aggregate system-wide metrics
        system_metrics = [
            MetricType.DATASET_COUNT,
            MetricType.PROVIDER_COUNT,
            MetricType.XML_ARCHIVE_COUNT,
            MetricType.VALIDATION_SUCCESS_RATE,
            MetricType.VALIDATION_PROCESSING_TIME,
            MetricType.DATASET_REGISTRATION_RATE,
            MetricType.DATASET_MODIFICATION_RATE
        ]
        
        for metric_type in system_metrics:
            # Get daily stats for this week
            daily_stats = db.query(StatisticModel).filter(
                and_(
                    StatisticModel.metric_type == metric_type,
                    StatisticModel.entity_type == EntityType.SYSTEM,
                    StatisticModel.period == Period.DAILY,
                    StatisticModel.date >= start_date,
                    StatisticModel.date <= end_date
                )
            ).all()
            
            if daily_stats:
                if metric_type in [MetricType.DATASET_REGISTRATION_RATE, MetricType.DATASET_MODIFICATION_RATE]:
                    # Sum for rate metrics
                    weekly_value = sum(stat.value for stat in daily_stats)
                else:
                    # Average for other metrics
                    weekly_value = sum(stat.value for stat in daily_stats) / len(daily_stats)
                
                stat = StatisticModel(
                    metric_type=metric_type,
                    entity_type=EntityType.SYSTEM,
                    entity_id=None,
                    period=Period.WEEKLY,
                    date=end_date,
                    value=weekly_value,
                    extra_data={
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat(),
                        'daily_values': [s.value for s in daily_stats],
                        'aggregation_type': 'sum' if 'rate' in metric_type.value else 'average',
                        'collection_timestamp': datetime.utcnow().isoformat()
                    }
                )
                db.add(stat)
                aggregated_stats.append(f"Weekly {metric_type.value}: {weekly_value:.2f}")
        
        # Aggregate provider-specific metrics
        providers = db.query(DataProviderModel).all()
        
        for provider in providers:
            # Aggregate provider dataset count
            daily_provider_stats = db.query(StatisticModel).filter(
                and_(
                    StatisticModel.metric_type == MetricType.PROVIDER_DATASET_COUNT,
                    StatisticModel.entity_type == EntityType.PROVIDER,
                    StatisticModel.entity_id == provider.id,
                    StatisticModel.period == Period.DAILY,
                    StatisticModel.date >= start_date,
                    StatisticModel.date <= end_date
                )
            ).all()
            
            if daily_provider_stats:
                weekly_avg = sum(stat.value for stat in daily_provider_stats) / len(daily_provider_stats)
                
                stat = StatisticModel(
                    metric_type=MetricType.PROVIDER_DATASET_COUNT,
                    entity_type=EntityType.PROVIDER,
                    entity_id=provider.id,
                    period=Period.WEEKLY,
                    date=end_date,
                    value=weekly_avg,
                    extra_data={
                        'provider_name': provider.name,
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat(),
                        'daily_values': [s.value for s in daily_provider_stats],
                        'collection_timestamp': datetime.utcnow().isoformat()
                    }
                )
                db.add(stat)
                aggregated_stats.append(f"Weekly provider {provider.id} dataset count: {weekly_avg:.2f}")
            
            # Aggregate provider biological units
            daily_bio_units_stats = db.query(StatisticModel).filter(
                and_(
                    StatisticModel.metric_type == MetricType.PROVIDER_BIOLOGICAL_UNITS,
                    StatisticModel.entity_type == EntityType.PROVIDER,
                    StatisticModel.entity_id == provider.id,
                    StatisticModel.period == Period.DAILY,
                    StatisticModel.date >= start_date,
                    StatisticModel.date <= end_date
                )
            ).all()
            
            if daily_bio_units_stats:
                weekly_avg_bio_units = sum(stat.value for stat in daily_bio_units_stats) / len(daily_bio_units_stats)
                
                bio_units_stat = StatisticModel(
                    metric_type=MetricType.PROVIDER_BIOLOGICAL_UNITS,
                    entity_type=EntityType.PROVIDER,
                    entity_id=provider.id,
                    period=Period.WEEKLY,
                    date=end_date,
                    value=weekly_avg_bio_units,
                    extra_data={
                        'provider_name': provider.name,
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat(),
                        'daily_values': [s.value for s in daily_bio_units_stats],
                        'collection_timestamp': datetime.utcnow().isoformat()
                    }
                )
                db.add(bio_units_stat)
                aggregated_stats.append(f"Weekly provider {provider.id} biological units: {weekly_avg_bio_units:.2f}")
        
        # Commit aggregated statistics
        db.commit()
        
        logger.info(f"Successfully aggregated {len(aggregated_stats)} weekly statistics")
        
        return {
            'status': 'completed',
            'week_start': start_date.isoformat(),
            'week_end': end_date.isoformat(),
            'statistics_aggregated': len(aggregated_stats),
            'details': aggregated_stats,
            'task_id': self.request.id,
            'completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception(f"Error aggregating weekly statistics: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    base=LoggingTask,  # Use custom base class for enhanced logging
    name="statistics.collect_provider_biological_units",
    queue='light_tasks',
    priority=10,
    max_retries=3,
    soft_time_limit=1800,  # 30 minutes timeout
    retry_backoff=True,
    retry_backoff_max=120,  # Maximum backoff in seconds (2 minutes)
    retry_jitter=True,  # Add randomization to prevent thundering herd
    autoretry_for=(Exception,),  # Auto-retry on all exceptions
    task_time_limit=1900,  # Hard time limit (31min 40s)
)
def collect_provider_biological_units(self, target_date: str = None) -> Dict[str, Any]:
    """
    Collect provider-level biological units by aggregating dataset unit counts.
    
    This function now respects anchor dates - it will aggregate the most recent
    unit count for each dataset that is at or before the target date, regardless
    of what date that unit count was recorded at (could be dataset created_at for
    first-time processing or a more recent date for updates).
    
    Queue Assignment: Routes to 'light_tasks' queue with priority=10 for higher
    priority execution using prefork worker pool optimized for CPU-bound operations.
    
    Args:
        target_date: Date string in YYYY-MM-DD format (defaults to yesterday)
        
    Returns:
        Dictionary with collection results
    """
    from sqlalchemy.dialects.postgresql import insert
    
    db = SessionLocal()
    
    try:
        # Parse target date
        if target_date:
            stat_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            stat_date = date.today() - timedelta(days=1)
        
        logger.info(f"Collecting provider biological units for {stat_date}")
        logger.info(f"Note: Will aggregate dataset unit counts recorded at or before {stat_date}, which may include historical anchor dates")
        
        collected_stats = []
        
        # Get all providers
        providers = db.query(DataProviderModel).all()
        
        for provider in providers:
            # Get all datasets for this provider
            dataset_ids = db.query(DatasetModel.id).filter(
                DatasetModel.provider_id == provider.id
            ).all()
            
            if not dataset_ids:
                # Provider has no datasets, set biological units to 0
                provider_biological_units = 0
                logger.info(f"Provider {provider.id} has no datasets, setting biological units to 0")
            else:
                dataset_id_list = [dataset_id[0] for dataset_id in dataset_ids]
                
                # Calculate total biological units by summing the most recent dataset unit counts
                # for each dataset belonging to this provider
                # IMPORTANT: We look for counts at or before stat_date, which may be at different
                # dates due to anchor date logic
                
                # First, check for any failed archives that are excluded from aggregation
                from sqlalchemy import cast, String
                failed_archives = db.query(StatisticModel).filter(
                    and_(
                        StatisticModel.metric_type == MetricType.DATASET_UNIT_COUNT,
                        StatisticModel.extra_data["processing_failed"].astext == "true",
                        StatisticModel.extra_data["failure_count"].astext.cast(String).cast(Integer) >= 5  # max_retries
                    )
                ).all()
                
                excluded_datasets = set()
                if failed_archives:
                    # Get dataset IDs for failed archives
                    for failed in failed_archives:
                        # Find the dataset for this archive
                        archive_id = failed.extra_data.get('archive_id')
                        if archive_id:
                            archive = db.query(XmlArchiveModel).filter(
                                XmlArchiveModel.id == int(archive_id)
                            ).first()
                            if archive and archive.dataset_id in dataset_id_list:
                                excluded_datasets.add(archive.dataset_id)
                    
                    if excluded_datasets:
                        logger.warning(f"Provider {provider.id}: Excluding {len(excluded_datasets)} datasets with failed archives from aggregation: {excluded_datasets}")
                
                # Filter out excluded datasets
                active_dataset_ids = [did for did in dataset_id_list if did not in excluded_datasets]
                
                if not active_dataset_ids:
                    provider_biological_units = 0
                    logger.warning(f"Provider {provider.id}: All datasets have failed archives, setting biological units to 0")
                else:
                    subquery = db.query(
                        StatisticModel.entity_id,
                        func.max(StatisticModel.date).label('max_date')
                    ).filter(
                        and_(
                            StatisticModel.metric_type == MetricType.DATASET_UNIT_COUNT,
                            StatisticModel.entity_type == EntityType.DATASET,
                            StatisticModel.entity_id.in_(active_dataset_ids),
                            StatisticModel.date <= stat_date
                        )
                    ).group_by(StatisticModel.entity_id).subquery()
                    
                    # Get the actual values using the max date for each dataset
                    recent_unit_counts = db.query(
                        StatisticModel.value,
                        StatisticModel.date,
                        StatisticModel.entity_id
                    ).join(
                        subquery,
                        and_(
                            StatisticModel.entity_id == subquery.c.entity_id,
                            StatisticModel.date == subquery.c.max_date
                        )
                    ).filter(
                        StatisticModel.metric_type == MetricType.DATASET_UNIT_COUNT
                    ).all()
                    
                    provider_biological_units = sum(count[0] for count in recent_unit_counts if count[0] is not None)
                    
                    # Log details about the aggregation
                    if recent_unit_counts:
                        date_range = set(count[1] for count in recent_unit_counts)
                        logger.info(f"Provider {provider.id}: Aggregated {len(recent_unit_counts)} dataset counts from dates: {sorted(date_range)}")
                        logger.info(f"Provider {provider.id}: Total biological units = {provider_biological_units} (excluded {len(excluded_datasets)} failed datasets)")
            
            # Use proper upsert for provider biological units
            stmt = insert(StatisticModel).values(
                metric_type=MetricType.PROVIDER_BIOLOGICAL_UNITS,
                entity_type=EntityType.PROVIDER,
                entity_id=provider.id,
                period=Period.DAILY,
                date=stat_date,
                value=provider_biological_units,
                extra_data={
                    'provider_name': provider.name,
                    'provider_datacenter': provider.datacenter,
                    'dataset_count': len(dataset_ids),
                    'collection_timestamp': datetime.utcnow().isoformat(),
                    'aggregation_note': 'Respects anchor dates from initial archive processing'
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            stmt = stmt.on_conflict_do_update(
                constraint='uq_statistics_unique_entry',
                set_={
                    'value': stmt.excluded.value,
                    'extra_data': stmt.excluded.extra_data,
                    'updated_at': datetime.utcnow()
                }
            )
            db.execute(stmt)
            collected_stats.append(f"Provider {provider.id} biological units (upserted): {provider_biological_units}")
        
        # Commit all statistics
        db.commit()
        
        logger.info(f"Successfully collected {len(collected_stats)} provider biological unit statistics for {stat_date}")
        
        return {
            'status': 'completed',
            'date': stat_date.isoformat(),
            'statistics_collected': len(collected_stats),
            'details': collected_stats,
            'task_id': self.request.id,
            'completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception(f"Error collecting provider biological units: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    base=LoggingTask,  # Use custom base class for enhanced logging
    name="statistics.aggregate_monthly_stats",
    queue='light_tasks',
    max_retries=3,
    soft_time_limit=1800,  # 30 minutes timeout
    retry_backoff=True,
    retry_backoff_max=120,  # Maximum backoff in seconds (2 minutes)
    retry_jitter=True,  # Add randomization to prevent thundering herd
    autoretry_for=(Exception,),  # Auto-retry on all exceptions
    task_time_limit=1900,  # Hard time limit (31min 40s)
)
def aggregate_monthly_statistics(self, target_month: str = None) -> Dict[str, Any]:
    """
    Aggregate monthly statistics from weekly data.
    
    Queue Assignment: Routes to 'light_tasks' queue for lightweight aggregation
    calculations using prefork worker pool optimized for CPU-bound operations.
    
    Args:
        target_month: Month string in YYYY-MM format (defaults to last month)
        
    Returns:
        Dictionary with aggregation results
    """
    db = SessionLocal()
    
    try:
        # Calculate target month
        if target_month:
            year, month = map(int, target_month.split('-'))
            start_date = date(year, month, 1)
        else:
            today = date.today()
            if today.month == 1:
                start_date = date(today.year - 1, 12, 1)
            else:
                start_date = date(today.year, today.month - 1, 1)
        
        # Calculate end date (last day of month)
        if start_date.month == 12:
            end_date = date(start_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(start_date.year, start_date.month + 1, 1) - timedelta(days=1)
        
        logger.info(f"Aggregating monthly statistics for {start_date.strftime('%Y-%m')}")
        
        aggregated_stats = []
        
        # Aggregate from weekly data
        system_metrics = [
            MetricType.DATASET_COUNT,
            MetricType.PROVIDER_COUNT,
            MetricType.XML_ARCHIVE_COUNT,
            MetricType.VALIDATION_SUCCESS_RATE,
            MetricType.VALIDATION_PROCESSING_TIME,
            MetricType.DATASET_REGISTRATION_RATE,
            MetricType.DATASET_MODIFICATION_RATE
        ]
        
        for metric_type in system_metrics:
            weekly_stats = db.query(StatisticModel).filter(
                and_(
                    StatisticModel.metric_type == metric_type,
                    StatisticModel.entity_type == EntityType.SYSTEM,
                    StatisticModel.period == Period.WEEKLY,
                    StatisticModel.date >= start_date,
                    StatisticModel.date <= end_date
                )
            ).all()
            
            if weekly_stats:
                if metric_type in [MetricType.DATASET_REGISTRATION_RATE, MetricType.DATASET_MODIFICATION_RATE]:
                    # Sum for rate metrics
                    monthly_value = sum(stat.value for stat in weekly_stats)
                else:
                    # Average for other metrics
                    monthly_value = sum(stat.value for stat in weekly_stats) / len(weekly_stats)
                
                stat = StatisticModel(
                    metric_type=metric_type,
                    entity_type=EntityType.SYSTEM,
                    entity_id=None,
                    period=Period.MONTHLY,
                    date=end_date,
                    value=monthly_value,
                    extra_data={
                        'month': start_date.strftime('%Y-%m'),
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat(),
                        'weekly_values': [s.value for s in weekly_stats],
                        'aggregation_type': 'sum' if 'rate' in metric_type.value else 'average',
                        'collection_timestamp': datetime.utcnow().isoformat()
                    }
                )
                db.add(stat)
                aggregated_stats.append(f"Monthly {metric_type.value}: {monthly_value:.2f}")
        
        # Commit aggregated statistics
        db.commit()
        
        logger.info(f"Successfully aggregated {len(aggregated_stats)} monthly statistics")
        
        return {
            'status': 'completed',
            'month': start_date.strftime('%Y-%m'),
            'month_start': start_date.isoformat(),
            'month_end': end_date.isoformat(),
            'statistics_aggregated': len(aggregated_stats),
            'details': aggregated_stats,
            'task_id': self.request.id,
            'completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception(f"Error aggregating monthly statistics: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    base=LoggingTask,  # Use custom base class for enhanced logging
    name="statistics.update_dataset_statistics",
    queue='light_tasks',
    max_retries=3,
    soft_time_limit=300,  # 5 minutes timeout
    retry_backoff=True,
    retry_backoff_max=120,  # Maximum backoff in seconds (2 minutes)
    retry_jitter=True,  # Add randomization to prevent thundering herd
    autoretry_for=(Exception,),  # Auto-retry on all exceptions
    task_time_limit=400,  # Hard time limit (6min 40s)
)
def update_dataset_statistics(self, dataset_id: int, trigger_type: str = "manual") -> Dict[str, Any]:
    """
    Update statistics for a specific dataset in real-time.
    
    Queue Assignment: Routes to 'light_tasks' queue for real-time statistical
    updates using prefork worker pool optimized for CPU-bound operations.
    
    Args:
        dataset_id: ID of the dataset to update statistics for
        trigger_type: What triggered this update (e.g., "creation", "validation", "archive_analysis")
        
    Returns:
        Dictionary with update results
    """
    from sqlalchemy.dialects.postgresql import insert
    
    db = SessionLocal()
    
    try:
        logger.info(f"Updating statistics for dataset {dataset_id} (trigger: {trigger_type})")
        
        # Get dataset and its provider
        dataset = db.query(DatasetModel).filter(DatasetModel.id == dataset_id).first()
        if not dataset:
            logger.warning(f"Dataset {dataset_id} not found")
            return {
                'status': 'error',
                'message': f'Dataset {dataset_id} not found',
                'dataset_id': dataset_id,
                'trigger_type': trigger_type
            }
        
        provider_id = dataset.provider_id
        stat_date = date.today()
        collected_stats = []
        
        # 1. Update system-wide dataset count
        total_datasets = db.query(func.count(DatasetModel.id)).scalar()
        
        stmt = insert(StatisticModel).values(
            metric_type=MetricType.DATASET_COUNT,
            entity_type=EntityType.SYSTEM,
            entity_id=None,
            period=Period.DAILY,
            date=stat_date,
            value=total_datasets,
            extra_data={
                'collection_timestamp': datetime.utcnow().isoformat(),
                'trigger_type': trigger_type,
                'trigger_dataset_id': dataset_id
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        stmt = stmt.on_conflict_do_update(
            constraint='uq_statistics_unique_entry',
            set_={
                'value': stmt.excluded.value,
                'extra_data': stmt.excluded.extra_data,
                'updated_at': datetime.utcnow()
            }
        )
        db.execute(stmt)
        collected_stats.append(f"System dataset count updated: {total_datasets}")
        
        # 2. Update provider-specific dataset count
        provider_dataset_count = db.query(func.count(DatasetModel.id)).filter(
            DatasetModel.provider_id == provider_id
        ).scalar()
        
        stmt = insert(StatisticModel).values(
            metric_type=MetricType.PROVIDER_DATASET_COUNT,
            entity_type=EntityType.PROVIDER,
            entity_id=provider_id,
            period=Period.DAILY,
            date=stat_date,
            value=provider_dataset_count,
            extra_data={
                'provider_name': dataset.provider.name if dataset.provider else 'Unknown',
                'provider_datacenter': dataset.provider.datacenter if dataset.provider else 'Unknown',
                'collection_timestamp': datetime.utcnow().isoformat(),
                'trigger_type': trigger_type,
                'trigger_dataset_id': dataset_id
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        stmt = stmt.on_conflict_do_update(
            constraint='uq_statistics_unique_entry',
            set_={
                'value': stmt.excluded.value,
                'extra_data': stmt.excluded.extra_data,
                'updated_at': datetime.utcnow()
            }
        )
        db.execute(stmt)
        collected_stats.append(f"Provider {provider_id} dataset count updated: {provider_dataset_count}")
        
        # 3. If dataset has XML archives, analyze them and update unit counts
        latest_archive = db.query(XmlArchiveModel).filter(
            and_(
                XmlArchiveModel.dataset_id == dataset_id,
                XmlArchiveModel.isLatest == True
            )
        ).first()
        
        if latest_archive:
            try:
                # Parse XML and extract unit information
                xml_data = parse_abcd_xml(latest_archive.url)
                
                # Store unit count statistic for this dataset
                if xml_data['unit_count'] > 0:
                    stmt = insert(StatisticModel).values(
                        metric_type=MetricType.DATASET_UNIT_COUNT,
                        entity_type=EntityType.DATASET,
                        entity_id=dataset_id,
                        period=Period.DAILY,
                        date=stat_date,
                        value=xml_data['unit_count'],
                        extra_data={
                            'archive_id': latest_archive.id,
                            'archive_url': latest_archive.url,
                            'parsing_metadata': {
                                'schema_detected': xml_data.get('schema_detected', 'unknown'),
                                'parsing_date': xml_data.get('parsing_date', datetime.utcnow().isoformat()),
                                'xml_files_processed': xml_data.get('xml_files_processed', 1),
                                'comprehensive_counting': True
                            },
                            'trigger_type': trigger_type,
                            'collection_timestamp': datetime.utcnow().isoformat()
                        },
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    stmt = stmt.on_conflict_do_update(
                        constraint='uq_statistics_unique_entry',
                        set_={
                            'value': stmt.excluded.value,
                            'extra_data': stmt.excluded.extra_data,
                            'updated_at': datetime.utcnow()
                        }
                    )
                    db.execute(stmt)
                    collected_stats.append(f"Dataset {dataset_id} unit count updated: {xml_data['unit_count']}")
                
            except XMLParsingError as e:
                logger.warning(f"Failed to parse archive for dataset {dataset_id}: {e}")
                collected_stats.append(f"Archive parsing failed: {str(e)}")
            except Exception as e:
                logger.error(f"Error analyzing archive for dataset {dataset_id}: {e}")
                collected_stats.append(f"Archive analysis error: {str(e)}")
        
        # 4. Update provider biological units (sum of all dataset units for this provider)
        # This should be called after updating dataset unit counts
        update_provider_biological_units.delay(provider_id, stat_date.isoformat(), trigger_type)
        
        # Commit changes
        db.commit()
        
        logger.info(f"Successfully updated {len(collected_stats)} statistics for dataset {dataset_id}")
        
        return {
            'status': 'completed',
            'dataset_id': dataset_id,
            'provider_id': provider_id,
            'trigger_type': trigger_type,
            'date': stat_date.isoformat(),
            'statistics_updated': len(collected_stats),
            'details': collected_stats,
            'task_id': self.request.id,
            'completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception(f"Error updating dataset statistics for {dataset_id}: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    base=LoggingTask,  # Use custom base class for enhanced logging
    name="statistics.update_provider_biological_units",
    queue='light_tasks',
    max_retries=3,
    soft_time_limit=300,  # 5 minutes timeout
    retry_backoff=True,
    retry_backoff_max=120,  # Maximum backoff in seconds (2 minutes)
    retry_jitter=True,  # Add randomization to prevent thundering herd
    autoretry_for=(Exception,),  # Auto-retry on all exceptions
    task_time_limit=400,  # Hard time limit (6min 40s)
)
def update_provider_biological_units(self, provider_id: int, target_date: str = None, trigger_type: str = "manual") -> Dict[str, Any]:
    """
    Update biological units statistics for a specific provider.
    
    This function now respects anchor dates - it will aggregate the most recent
    unit count for each dataset that is at or before the target date, regardless
    of what date that unit count was recorded at (could be dataset created_at for
    first-time processing or a more recent date for updates).
    
    Queue Assignment: Routes to 'light_tasks' queue for real-time biological unit
    calculations using prefork worker pool optimized for CPU-bound operations.
    
    Args:
        provider_id: ID of the provider to update
        target_date: Date string in YYYY-MM-DD format (defaults to today)
        trigger_type: What triggered this update
        
    Returns:
        Dictionary with update results
    """
    from sqlalchemy.dialects.postgresql import insert
    
    db = SessionLocal()
    
    try:
        # Parse target date
        if target_date:
            stat_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            stat_date = date.today()
        
        logger.info(f"Updating provider {provider_id} biological units for {stat_date} (trigger: {trigger_type})")
        logger.info(f"Note: Will aggregate dataset unit counts recorded at or before {stat_date}, which may include historical anchor dates")
        
        # Get provider
        provider = db.query(DataProviderModel).filter(DataProviderModel.id == provider_id).first()
        if not provider:
            logger.warning(f"Provider {provider_id} not found")
            return {
                'status': 'error',
                'message': f'Provider {provider_id} not found',
                'provider_id': provider_id,
                'trigger_type': trigger_type
            }
        
        # Get all datasets for this provider
        dataset_ids = db.query(DatasetModel.id).filter(
            DatasetModel.provider_id == provider_id
        ).all()
        
        if not dataset_ids:
            provider_biological_units = 0
            logger.info(f"Provider {provider_id} has no datasets, setting biological units to 0")
        else:
            dataset_id_list = [dataset_id[0] for dataset_id in dataset_ids]
            
            # Get the most recent unit count for each dataset
            # IMPORTANT: We look for counts at or before stat_date, which may be at different
            # dates due to anchor date logic
            subquery = db.query(
                StatisticModel.entity_id,
                func.max(StatisticModel.date).label('max_date')
            ).filter(
                and_(
                    StatisticModel.metric_type == MetricType.DATASET_UNIT_COUNT,
                    StatisticModel.entity_type == EntityType.DATASET,
                    StatisticModel.entity_id.in_(dataset_id_list),
                    StatisticModel.date <= stat_date
                )
            ).group_by(StatisticModel.entity_id).subquery()
            
            # Get the actual values using the max date for each dataset
            recent_unit_counts = db.query(
                StatisticModel.value,
                StatisticModel.date,
                StatisticModel.entity_id
            ).join(
                subquery,
                and_(
                    StatisticModel.entity_id == subquery.c.entity_id,
                    StatisticModel.date == subquery.c.max_date
                )
            ).filter(
                StatisticModel.metric_type == MetricType.DATASET_UNIT_COUNT
            ).all()
            
            provider_biological_units = sum(count[0] for count in recent_unit_counts if count[0] is not None)
            
            # Log details about the aggregation
            if recent_unit_counts:
                date_range = set(count[1] for count in recent_unit_counts)
                logger.info(f"Provider {provider_id}: Aggregated {len(recent_unit_counts)} dataset counts from dates: {sorted(date_range)}")
                logger.info(f"Provider {provider_id}: Total biological units = {provider_biological_units}")
        
        # Use proper upsert for provider biological units
        stmt = insert(StatisticModel).values(
            metric_type=MetricType.PROVIDER_BIOLOGICAL_UNITS,
            entity_type=EntityType.PROVIDER,
            entity_id=provider_id,
            period=Period.DAILY,
            date=stat_date,
            value=provider_biological_units,
            extra_data={
                'provider_name': provider.name,
                'provider_datacenter': provider.datacenter,
                'dataset_count': len(dataset_ids),
                'trigger_type': trigger_type,
                'collection_timestamp': datetime.utcnow().isoformat(),
                'aggregation_note': 'Respects anchor dates from initial archive processing'
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        stmt = stmt.on_conflict_do_update(
            constraint='uq_statistics_unique_entry',
            set_={
                'value': stmt.excluded.value,
                'extra_data': stmt.excluded.extra_data,
                'updated_at': datetime.utcnow()
            }
        )
        db.execute(stmt)
        
        # Commit changes
        db.commit()
        
        logger.info(f"Successfully updated provider {provider_id} biological units: {provider_biological_units}")
        
        return {
            'status': 'completed',
            'provider_id': provider_id,
            'date': stat_date.isoformat(),
            'biological_units': provider_biological_units,
            'dataset_count': len(dataset_ids),
            'trigger_type': trigger_type,
            'task_id': self.request.id,
            'completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception(f"Error updating provider {provider_id} biological units: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    base=LoggingTask,  # Use custom base class for enhanced logging
    name="statistics.update_validation_statistics",
    queue='light_tasks',
    max_retries=3,
    soft_time_limit=300,  # 5 minutes timeout
    retry_backoff=True,
    retry_backoff_max=120,  # Maximum backoff in seconds (2 minutes)
    retry_jitter=True,  # Add randomization to prevent thundering herd
    autoretry_for=(Exception,),  # Auto-retry on all exceptions
    task_time_limit=400,  # Hard time limit (6min 40s)
)
def update_validation_statistics(self, validation_job_id: int = None, trigger_type: str = "completion") -> Dict[str, Any]:
    """
    Update validation statistics when a validation job completes.
    
    Queue Assignment: Routes to 'light_tasks' queue for validation metric
    calculations using prefork worker pool optimized for CPU-bound operations.
    
    Args:
        validation_job_id: ID of the validation job that completed (optional)
        trigger_type: What triggered this update
        
    Returns:
        Dictionary with update results
    """
    from sqlalchemy.dialects.postgresql import insert
    
    db = SessionLocal()
    
    try:
        stat_date = date.today()
        logger.info(f"Updating validation statistics for {stat_date} (trigger: {trigger_type})")
        
        # Calculate validation statistics for the last 7 days
        week_ago = stat_date - timedelta(days=7)
        validation_jobs = db.query(ValidationJobModel).filter(
            ValidationJobModel.created_at >= week_ago
        ).all()
        
        collected_stats = []
        
        if validation_jobs:
            total_jobs = len(validation_jobs)
            successful_jobs = len([job for job in validation_jobs 
                                 if job.status == 'completed' and job.valid_files == job.total_files and job.total_files > 0])
            success_rate = (successful_jobs / total_jobs) * 100 if total_jobs > 0 else 0
            
            avg_processing_time = 0
            completed_jobs = [job for job in validation_jobs if job.status == 'completed']
            if completed_jobs:
                processing_times = [job.validation_time for job in completed_jobs 
                                  if job.validation_time is not None]
                if processing_times:
                    avg_processing_time = sum(processing_times) / len(processing_times)
            
            # Update validation success rate
            stmt = insert(StatisticModel).values(
                metric_type=MetricType.VALIDATION_SUCCESS_RATE,
                entity_type=EntityType.SYSTEM,
                entity_id=None,
                period=Period.DAILY,
                date=stat_date,
                value=success_rate,
                extra_data={
                    'total_jobs': total_jobs,
                    'successful_jobs': successful_jobs,
                    'period_days': 7,
                    'trigger_type': trigger_type,
                    'trigger_job_id': validation_job_id,
                    'collection_timestamp': datetime.utcnow().isoformat()
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            stmt = stmt.on_conflict_do_update(
                constraint='uq_statistics_unique_entry',
                set_={
                    'value': stmt.excluded.value,
                    'extra_data': stmt.excluded.extra_data,
                    'updated_at': datetime.utcnow()
                }
            )
            db.execute(stmt)
            collected_stats.append(f"Validation success rate updated: {success_rate:.1f}%")
            
            # Update average processing time
            stmt = insert(StatisticModel).values(
                metric_type=MetricType.VALIDATION_PROCESSING_TIME,
                entity_type=EntityType.SYSTEM,
                entity_id=None,
                period=Period.DAILY,
                date=stat_date,
                value=avg_processing_time,
                extra_data={
                    'jobs_included': len([j for j in validation_jobs if j.validation_time is not None]),
                    'trigger_type': trigger_type,
                    'trigger_job_id': validation_job_id,
                    'collection_timestamp': datetime.utcnow().isoformat()
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            stmt = stmt.on_conflict_do_update(
                constraint='uq_statistics_unique_entry',
                set_={
                    'value': stmt.excluded.value,
                    'extra_data': stmt.excluded.extra_data,
                    'updated_at': datetime.utcnow()
                }
            )
            db.execute(stmt)
            collected_stats.append(f"Validation avg processing time updated: {avg_processing_time:.2f}s")
        
        # Commit changes
        db.commit()
        
        logger.info(f"Successfully updated {len(collected_stats)} validation statistics")
        
        return {
            'status': 'completed',
            'date': stat_date.isoformat(),
            'validation_job_id': validation_job_id,
            'trigger_type': trigger_type,
            'statistics_updated': len(collected_stats),
            'details': collected_stats,
            'task_id': self.request.id,
            'completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception(f"Error updating validation statistics: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    base=LoggingTask,  # Use custom base class for enhanced logging
    name="statistics.update_provider_dataset_count_after_deletion",
    queue='light_tasks',
    max_retries=3,
    soft_time_limit=300,  # 5 minutes timeout
    retry_backoff=True,
    retry_backoff_max=120,  # Maximum backoff in seconds (2 minutes)
    retry_jitter=True,  # Add randomization to prevent thundering herd
    autoretry_for=(Exception,),  # Auto-retry on all exceptions
    task_time_limit=400,  # Hard time limit (6min 40s)
)
def update_provider_dataset_count_after_deletion(self, provider_id: int, trigger_type: str = "dataset_deletion") -> Dict[str, Any]:
    """
    Update provider dataset count timeline after a dataset deletion.
    This ensures the Dataset Registration Timeline reflects deletions immediately.
    
    Queue Assignment: Routes to 'light_tasks' queue for real-time count updates
    using prefork worker pool optimized for CPU-bound operations.
    
    Args:
        provider_id: ID of the provider to update
        trigger_type: What triggered this update
        
    Returns:
        Dictionary with update results
    """
    from sqlalchemy.dialects.postgresql import insert
    
    db = SessionLocal()
    
    try:
        stat_date = date.today()
        logger.info(f"Updating provider {provider_id} dataset count for {stat_date} (trigger: {trigger_type})")
        
        # Get provider
        provider = db.query(DataProviderModel).filter(DataProviderModel.id == provider_id).first()
        if not provider:
            logger.warning(f"Provider {provider_id} not found")
            return {
                'status': 'error',
                'message': f'Provider {provider_id} not found',
                'provider_id': provider_id,
                'trigger_type': trigger_type
            }
        
        # Get current dataset count for this provider (after deletion)
        provider_dataset_count = db.query(func.count(DatasetModel.id)).filter(
            DatasetModel.provider_id == provider_id
        ).scalar()
        
        # Update the provider dataset count statistic for today
        # This will create a new timeline point or update the existing one for today
        stmt = insert(StatisticModel).values(
            metric_type=MetricType.PROVIDER_DATASET_COUNT,
            entity_type=EntityType.PROVIDER,
            entity_id=provider_id,
            period=Period.DAILY,
            date=stat_date,
            value=provider_dataset_count,
            extra_data={
                'provider_name': provider.name,
                'provider_datacenter': provider.datacenter,
                'trigger_type': trigger_type,
                'collection_timestamp': datetime.utcnow().isoformat(),
                'real_time_update': True
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        stmt = stmt.on_conflict_do_update(
            constraint='uq_statistics_unique_entry',
            set_={
                'value': stmt.excluded.value,
                'extra_data': stmt.excluded.extra_data,
                'updated_at': datetime.utcnow()
            }
        )
        db.execute(stmt)
        
        # Also update system-wide dataset count to keep everything in sync
        total_datasets = db.query(func.count(DatasetModel.id)).scalar()
        
        stmt = insert(StatisticModel).values(
            metric_type=MetricType.DATASET_COUNT,
            entity_type=EntityType.SYSTEM,
            entity_id=None,
            period=Period.DAILY,
            date=stat_date,
            value=total_datasets,
            extra_data={
                'collection_timestamp': datetime.utcnow().isoformat(),
                'trigger_type': trigger_type,
                'trigger_provider_id': provider_id,
                'real_time_update': True
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        stmt = stmt.on_conflict_do_update(
            constraint='uq_statistics_unique_entry',
            set_={
                'value': stmt.excluded.value,
                'extra_data': stmt.excluded.extra_data,
                'updated_at': datetime.utcnow()
            }
        )
        db.execute(stmt)
        
        # Commit changes
        db.commit()
        
        logger.info(f"Successfully updated provider {provider_id} dataset count: {provider_dataset_count}")
        
        return {
            'status': 'completed',
            'provider_id': provider_id,
            'date': stat_date.isoformat(),
            'dataset_count': provider_dataset_count,
            'system_dataset_count': total_datasets,
            'trigger_type': trigger_type,
            'task_id': self.request.id,
            'completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception(f"Error updating provider {provider_id} dataset count after deletion: {e}")
        db.rollback()
        raise
    finally:
        db.close()