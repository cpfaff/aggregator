"""
Celery tasks for statistics collection and aggregation.
"""

import logging
import requests
import xml.etree.ElementTree as ET
import zipfile
import io
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
from collections import defaultdict

from celery import shared_task
from sqlalchemy import func, and_, distinct

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

logger = logging.getLogger(__name__)


class XMLParsingError(Exception):
    """Custom exception for XML parsing errors."""
    pass


def _process_single_xml_root(root, filename: str) -> Dict[str, Any]:
    """
    Process a single XML root element and extract unit information.
    Implements memory-efficient streaming processing for large unit collections.
    
    Args:
        root: XML root element
        filename: Name of XML file being processed (for logging)
        
    Returns:
        Dictionary containing extracted information from this XML file
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
    
    # Extract unit information
    units = []
    unit_count = 0
    
    if detected_ns:
        ns_uri = detected_ns['abcd']
        
        # Find Units - different paths for different versions
        unit_paths = [
            f".//{{{ns_uri}}}Unit",
            f".//{{{ns_uri}}}DataSet/{{{ns_uri}}}Units/{{{ns_uri}}}Unit"
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
    
    # Extract taxonomic information
    taxonomic_info = {
        'families': set(),
        'genera': set(),
        'species': set()
    }
    
    # Extract geographic information
    geographic_info = {
        'countries': set(),
        'localities': set(),
        'coordinates': []
    }
    
    # Extract citation information
    citation_info = {
        'has_collector': 0,
        'has_collection_date': 0,
        'has_location': 0,
        'has_identification': 0,
        'total_units': unit_count
    }
    
    # Helper function to find elements by tag name substring (case-insensitive)
    def find_elements_by_tag_substring(parent, substring):
        """Find all descendant elements whose tag contains the substring (case-insensitive)."""
        result = []
        for elem in parent.iter():
            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if substring.lower() in tag_name.lower():
                result.append(elem)
        return result
    
    # Process each unit - REMOVED 1000 unit limit for comprehensive counting
    # Use memory-efficient processing by processing units in batches if needed
    batch_size = 5000  # Process units in batches to manage memory
    for i in range(0, len(units), batch_size):
        batch_units = units[i:i + batch_size]
        logger.debug(f"Processing units {i+1} to {min(i+batch_size, len(units))} of {len(units)} in {filename}")
        
        for unit in batch_units:
            # Extract taxonomic data
            for tax_field, field_name in [
                ('Family', 'families'),
                ('Genus', 'genera'),
                ('Species', 'species')
            ]:
                tax_elements = find_elements_by_tag_substring(unit, tax_field)
                for elem in tax_elements:
                    if elem.text and elem.text.strip():
                        taxonomic_info[field_name].add(elem.text.strip())
            
            # Extract geographic data
            country_elements = find_elements_by_tag_substring(unit, 'Country')
            for elem in country_elements:
                if elem.text and elem.text.strip():
                    geographic_info['countries'].add(elem.text.strip())
            
            locality_elements = find_elements_by_tag_substring(unit, 'Locality')
            for elem in locality_elements:
                if elem.text and elem.text.strip():
                    geographic_info['localities'].add(elem.text.strip())
            
            # Extract coordinates
            lat_elements = find_elements_by_tag_substring(unit, 'Latitude')
            lon_elements = find_elements_by_tag_substring(unit, 'Longitude')
            
            for lat_elem, lon_elem in zip(lat_elements, lon_elements):
                try:
                    lat = float(lat_elem.text) if lat_elem.text else None
                    lon = float(lon_elem.text) if lon_elem.text else None
                    if lat is not None and lon is not None:
                        geographic_info['coordinates'].append([lat, lon])
                except (ValueError, TypeError):
                    pass
            
            # Check citation completeness
            if find_elements_by_tag_substring(unit, 'Collector'):
                citation_info['has_collector'] += 1
            if find_elements_by_tag_substring(unit, 'GatheringDate'):
                citation_info['has_collection_date'] += 1
            if find_elements_by_tag_substring(unit, 'Country') or find_elements_by_tag_substring(unit, 'Locality'):
                citation_info['has_location'] += 1
            if find_elements_by_tag_substring(unit, 'Identification'):
                citation_info['has_identification'] += 1
    
    return {
        'unit_count': unit_count,
        'taxonomic_info': taxonomic_info,
        'geographic_info': geographic_info,
        'citation_info': citation_info,
        'schema_detected': detected_ns is not None
    }


def parse_abcd_xml(xml_url: str) -> Dict[str, Any]:
    """
    Parse ABCD XML file and extract unit counts, taxonomic info, and geographic data.
    Handles both direct XML files and ZIP archives containing XML files.
    For ZIP archives, processes ALL XML files to get complete unit counts.
    
    Args:
        xml_url: URL of the XML file or ZIP archive to parse
        
    Returns:
        Dictionary containing extracted information aggregated across all XML files in archive
        
    Raises:
        XMLParsingError: If XML parsing fails
    """
    try:
        # Download content
        response = requests.get(xml_url, timeout=300, stream=True)
        response.raise_for_status()
        
        # Read content into memory
        content = response.content
        
        # Initialize aggregated results
        total_unit_count = 0
        all_taxonomic_info = {
            'families': set(),
            'genera': set(),
            'species': set()
        }
        all_geographic_info = {
            'countries': set(),
            'localities': set(),
            'coordinates': []
        }
        all_citation_info = {
            'has_collector': 0,
            'has_collection_date': 0,
            'has_location': 0,
            'has_identification': 0,
            'total_units': 0
        }
        
        xml_files_processed = 0
        
        # Check if content starts with ZIP file signature (PK)
        if content.startswith(b'PK'):
            logger.debug(f"Detected ZIP archive for URL: {xml_url}")
            
            # Handle ZIP file - process ALL XML files
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
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
                                
                                # Process this XML file and aggregate results
                                file_results = _process_single_xml_root(root, xml_filename)
                                
                                # Aggregate results
                                total_unit_count += file_results['unit_count']
                                all_taxonomic_info['families'].update(file_results['taxonomic_info']['families'])
                                all_taxonomic_info['genera'].update(file_results['taxonomic_info']['genera'])
                                all_taxonomic_info['species'].update(file_results['taxonomic_info']['species'])
                                all_geographic_info['countries'].update(file_results['geographic_info']['countries'])
                                all_geographic_info['localities'].update(file_results['geographic_info']['localities'])
                                all_geographic_info['coordinates'].extend(file_results['geographic_info']['coordinates'])
                                all_citation_info['has_collector'] += file_results['citation_info']['has_collector']
                                all_citation_info['has_collection_date'] += file_results['citation_info']['has_collection_date']
                                all_citation_info['has_location'] += file_results['citation_info']['has_location']
                                all_citation_info['has_identification'] += file_results['citation_info']['has_identification']
                                
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
                root = ET.fromstring(content)
                file_results = _process_single_xml_root(root, "direct_xml")
                total_unit_count = file_results['unit_count']
                all_taxonomic_info = file_results['taxonomic_info']
                all_geographic_info = file_results['geographic_info']
                all_citation_info = file_results['citation_info']
                xml_files_processed = 1
        else:
            # Try direct XML parsing
            logger.debug(f"Attempting direct XML parsing for: {xml_url}")
            root = ET.fromstring(content)
            file_results = _process_single_xml_root(root, "direct_xml")
            total_unit_count = file_results['unit_count']
            all_taxonomic_info = file_results['taxonomic_info']
            all_geographic_info = file_results['geographic_info']
            all_citation_info = file_results['citation_info']
            xml_files_processed = 1
        
        # Update total units
        all_citation_info['total_units'] = total_unit_count
        
        # Calculate aggregated citation completeness score
        if total_unit_count > 0:
            completeness_score = (
                all_citation_info['has_collector'] +
                all_citation_info['has_collection_date'] +
                all_citation_info['has_location'] +
                all_citation_info['has_identification']
            ) / (4 * total_unit_count)  # 4 criteria per unit
        else:
            completeness_score = 0.0
        
        logger.info(f"Archive processing complete: {total_unit_count} total units from {xml_files_processed} XML files")
        
        return {
            'unit_count': total_unit_count,
            'taxonomic_diversity': {
                'families': len(all_taxonomic_info['families']),
                'genera': len(all_taxonomic_info['genera']),
                'species': len(all_taxonomic_info['species'])
            },
            'geographic_coverage': {
                'countries': len(all_geographic_info['countries']),
                'localities': len(all_geographic_info['localities']),
                'coordinates': len(all_geographic_info['coordinates'])
            },
            'citation_completeness': completeness_score,
            'parsing_date': datetime.utcnow().isoformat(),
            'schema_detected': xml_files_processed > 0,  # True if we processed any files
            'xml_files_processed': xml_files_processed,
            'families_list': list(all_taxonomic_info['families'])[:50],  # Limit for storage
            'countries_list': list(all_geographic_info['countries'])[:50]
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


@shared_task(
    bind=True,
    name="statistics.collect_daily_stats",
    max_retries=3,
    soft_time_limit=1800,  # 30 minutes timeout
    retry_backoff=True,
)
def collect_daily_statistics(self, target_date: str = None) -> Dict[str, Any]:
    """
    Collect daily statistics for datasets, providers, and validation jobs.
    
    Args:
        target_date: Date string in YYYY-MM-DD format (defaults to yesterday)
        
    Returns:
        Dictionary with collection results
    """
    db = SessionLocal()
    
    try:
        # Parse target date
        if target_date:
            stat_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            stat_date = date.today() - timedelta(days=1)
        
        logger.info(f"Collecting daily statistics for {stat_date}")
        
        collected_stats = []
        
        # System-wide statistics
        
        # Total datasets - use proper upsert with ON CONFLICT
        total_datasets = db.query(func.count(DatasetModel.id)).scalar()
        
        # Use SQLAlchemy's ON CONFLICT functionality for PostgreSQL upsert
        from sqlalchemy.dialects.postgresql import insert
        from sqlalchemy import text
        
        stmt = insert(StatisticModel).values(
            metric_type=MetricType.DATASET_COUNT,
            entity_type=EntityType.SYSTEM,
            entity_id=None,
            period=Period.DAILY,
            date=stat_date,
            value=total_datasets,
            extra_data={'collection_timestamp': datetime.utcnow().isoformat()},
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
        collected_stats.append(f"System dataset count (upserted): {total_datasets}")
        
        # Total providers - use proper upsert with ON CONFLICT
        total_providers = db.query(func.count(DataProviderModel.id)).scalar()
        
        stmt = insert(StatisticModel).values(
            metric_type=MetricType.PROVIDER_COUNT,
            entity_type=EntityType.SYSTEM,
            entity_id=None,
            period=Period.DAILY,
            date=stat_date,
            value=total_providers,
            extra_data={'collection_timestamp': datetime.utcnow().isoformat()},
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
        collected_stats.append(f"System provider count (upserted): {total_providers}")
        
        # Total XML archives - use proper upsert with ON CONFLICT
        total_archives = db.query(func.count(XmlArchiveModel.id)).scalar()
        
        stmt = insert(StatisticModel).values(
            metric_type=MetricType.XML_ARCHIVE_COUNT,
            entity_type=EntityType.SYSTEM,
            entity_id=None,
            period=Period.DAILY,
            date=stat_date,
            value=total_archives,
            extra_data={'collection_timestamp': datetime.utcnow().isoformat()},
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
        collected_stats.append(f"System XML archive count (upserted): {total_archives}")
        
        # Validation statistics (last 7 days)
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
            
            # Validation success rate - use proper upsert with ON CONFLICT
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
            collected_stats.append(f"System validation success rate (upserted): {success_rate:.1f}%")
            
            # Average processing time - use proper upsert with ON CONFLICT
            stmt = insert(StatisticModel).values(
                metric_type=MetricType.VALIDATION_PROCESSING_TIME,
                entity_type=EntityType.SYSTEM,
                entity_id=None,
                period=Period.DAILY,
                date=stat_date,
                value=avg_processing_time,
                extra_data={
                    'jobs_included': len([j for j in validation_jobs if j.validation_time is not None]),
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
            collected_stats.append(f"System avg processing time (upserted): {avg_processing_time:.2f}s")
        
        # Provider-specific statistics
        providers = db.query(DataProviderModel).all()
        
        for provider in providers:
            # Dataset count per provider
            provider_dataset_count = db.query(func.count(DatasetModel.id)).filter(
                DatasetModel.provider_id == provider.id
            ).scalar()
            
            stmt = insert(StatisticModel).values(
                metric_type=MetricType.PROVIDER_DATASET_COUNT,
                entity_type=EntityType.PROVIDER,
                entity_id=provider.id,
                period=Period.DAILY,
                date=stat_date,
                value=provider_dataset_count,
                extra_data={
                    'provider_name': provider.name,
                    'provider_datacenter': provider.datacenter,
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
            collected_stats.append(f"Provider {provider.id} dataset count (upserted): {provider_dataset_count}")
            
            # Calculate provider biological units by getting the most recent unit count for each dataset
            # Get all datasets for this provider
            dataset_ids = db.query(DatasetModel.id).filter(
                DatasetModel.provider_id == provider.id
            ).all()
            
            if not dataset_ids:
                provider_biological_units = 0
            else:
                dataset_id_list = [dataset_id[0] for dataset_id in dataset_ids]
                
                # Get the most recent unit count for each dataset
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
                    'dataset_count': provider_dataset_count,
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
            collected_stats.append(f"Provider {provider.id} biological units (upserted): {provider_biological_units}")
        
        # Dataset registration rate (new datasets today)
        start_of_day = datetime.combine(stat_date, datetime.min.time())
        end_of_day = datetime.combine(stat_date, datetime.max.time())
        
        new_datasets_count = db.query(func.count(DatasetModel.id)).filter(
            and_(
                DatasetModel.created_at >= start_of_day,
                DatasetModel.created_at <= end_of_day
            )
        ).scalar()
        
        stmt = insert(StatisticModel).values(
            metric_type=MetricType.DATASET_REGISTRATION_RATE,
            entity_type=EntityType.SYSTEM,
            entity_id=None,
            period=Period.DAILY,
            date=stat_date,
            value=new_datasets_count,
            extra_data={
                'period_start': start_of_day.isoformat(),
                'period_end': end_of_day.isoformat(),
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
        collected_stats.append(f"New datasets today (upserted): {new_datasets_count}")
        
        # Dataset modification rate (modified datasets today)
        modified_datasets_count = db.query(func.count(distinct(DatasetModel.id))).filter(
            and_(
                DatasetModel.updated_at >= start_of_day,
                DatasetModel.updated_at <= end_of_day,
                DatasetModel.created_at < start_of_day  # Exclude new datasets
            )
        ).scalar()
        
        stmt = insert(StatisticModel).values(
            metric_type=MetricType.DATASET_MODIFICATION_RATE,
            entity_type=EntityType.SYSTEM,
            entity_id=None,
            period=Period.DAILY,
            date=stat_date,
            value=modified_datasets_count,
            extra_data={
                'period_start': start_of_day.isoformat(),
                'period_end': end_of_day.isoformat(),
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
        collected_stats.append(f"Modified datasets today (upserted): {modified_datasets_count}")
        
        # Commit all statistics
        db.commit()
        
        logger.info(f"Successfully collected {len(collected_stats)} daily statistics for {stat_date}")
        
        return {
            'status': 'completed',
            'date': stat_date.isoformat(),
            'statistics_collected': len(collected_stats),
            'details': collected_stats,
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
    name="statistics.analyze_xml_archives",
    max_retries=2,
    soft_time_limit=3600,  # 1 hour timeout
    retry_backoff=True,
)
def analyze_xml_archives(self, batch_size: int = 50, offset: int = 0) -> Dict[str, Any]:
    """
    Analyze XML archives to extract unit counts and metadata.
    Processes archives in batches to avoid memory issues.
    
    Args:
        batch_size: Number of archives to process in this batch
        offset: Starting offset for the batch
        
    Returns:
        Dictionary with analysis results
    """
    db = SessionLocal()
    
    try:
        logger.info(f"Analyzing XML archives - batch size: {batch_size}, offset: {offset}")
        
        # Get batch of LATEST archives to analyze (respecting system constraint)
        archives = db.query(XmlArchiveModel).filter(
            XmlArchiveModel.isLatest == True
        ).offset(offset).limit(batch_size).all()
        
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
        results = []
        
        for archive in archives:
            try:
                # Parse XML and extract information
                xml_data = parse_abcd_xml(archive.url)
                
                # Store unit count statistic - use proper upsert with ON CONFLICT
                if xml_data['unit_count'] > 0:
                    stmt = insert(StatisticModel).values(
                        metric_type=MetricType.DATASET_UNIT_COUNT,
                        entity_type=EntityType.DATASET,
                        entity_id=archive.dataset_id,
                        period=Period.DAILY,
                        date=date.today(),
                        value=xml_data['unit_count'],
                        extra_data={
                            'archive_id': archive.id,
                            'archive_url': archive.url,
                            'taxonomic_diversity': xml_data['taxonomic_diversity'],
                            'geographic_coverage': xml_data['geographic_coverage'],
                            'parsing_metadata': {
                                'schema_detected': xml_data['schema_detected'],
                                'parsing_date': xml_data['parsing_date'],
                                'xml_files_processed': xml_data.get('xml_files_processed', 1),
                                'comprehensive_counting': True
                            }
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
                
                # Store citation completeness statistic - use proper upsert with ON CONFLICT
                if xml_data['citation_completeness'] is not None:
                    stmt = insert(StatisticModel).values(
                        metric_type=MetricType.CITATION_COMPLETENESS,
                        entity_type=EntityType.DATASET,
                        entity_id=archive.dataset_id,
                        period=Period.DAILY,
                        date=date.today(),
                        value=xml_data['citation_completeness'],
                        extra_data={
                            'archive_id': archive.id,
                            'total_units': xml_data['unit_count']
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
                
                # Store geographic coverage score - use proper upsert with ON CONFLICT
                geo_score = min(100.0, (xml_data['geographic_coverage']['countries'] * 10 +
                                      xml_data['geographic_coverage']['coordinates'] * 0.1))
                
                stmt = insert(StatisticModel).values(
                    metric_type=MetricType.GEOGRAPHIC_COVERAGE,
                    entity_type=EntityType.DATASET,
                    entity_id=archive.dataset_id,
                    period=Period.DAILY,
                    date=date.today(),
                    value=geo_score,
                    extra_data={
                        'archive_id': archive.id,
                        'countries_count': xml_data['geographic_coverage']['countries'],
                        'coordinates_count': xml_data['geographic_coverage']['coordinates'],
                        'countries_sample': xml_data.get('countries_list', [])[:10]
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
                
                processed_count += 1
                results.append({
                    'archive_id': archive.id,
                    'dataset_id': archive.dataset_id,
                    'unit_count': xml_data['unit_count'],
                    'citation_completeness': xml_data['citation_completeness'],
                    'status': 'success'
                })
                
                logger.info(f"Successfully analyzed archive {archive.id}: {xml_data['unit_count']} units from {xml_data.get('xml_files_processed', 1)} XML files")
                
            except XMLParsingError as e:
                error_count += 1
                logger.warning(f"Failed to parse archive {archive.id}: {e}")
                results.append({
                    'archive_id': archive.id,
                    'dataset_id': archive.dataset_id,
                    'error': str(e),
                    'status': 'error'
                })
            except Exception as e:
                error_count += 1
                logger.error(f"Unexpected error processing archive {archive.id}: {e}")
                results.append({
                    'archive_id': archive.id,
                    'dataset_id': archive.dataset_id,
                    'error': str(e),
                    'status': 'error'
                })
        
        # Commit statistics
        db.commit()
        
        logger.info(f"XML analysis batch completed - processed: {processed_count}, errors: {error_count}")
        
        # Schedule next batch if there were results
        if len(archives) == batch_size:
            # There might be more archives to process
            analyze_xml_archives.delay(batch_size=batch_size, offset=offset + batch_size)
        
        return {
            'status': 'completed',
            'batch_size': batch_size,
            'offset': offset,
            'processed': processed_count,
            'errors': error_count,
            'has_more': len(archives) == batch_size,
            'results': results,
            'task_id': self.request.id,
            'completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception(f"Error in XML analysis batch: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    name="statistics.aggregate_weekly_stats",
    max_retries=3,
    soft_time_limit=1800,  # 30 minutes timeout
    retry_backoff=True,
)
def aggregate_weekly_statistics(self, target_date: str = None) -> Dict[str, Any]:
    """
    Aggregate weekly statistics from daily data.
    
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
    name="statistics.collect_provider_biological_units",
    max_retries=3,
    soft_time_limit=1800,  # 30 minutes timeout
    retry_backoff=True,
)
def collect_provider_biological_units(self, target_date: str = None) -> Dict[str, Any]:
    """
    Collect provider-level biological units by aggregating dataset unit counts.
    
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
            else:
                dataset_id_list = [dataset_id[0] for dataset_id in dataset_ids]
                
                # Calculate total biological units by summing the most recent dataset unit counts
                # for each dataset belonging to this provider
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
    name="statistics.aggregate_monthly_stats",
    max_retries=3,
    soft_time_limit=1800,  # 30 minutes timeout
    retry_backoff=True,
)
def aggregate_monthly_statistics(self, target_month: str = None) -> Dict[str, Any]:
    """
    Aggregate monthly statistics from weekly data.
    
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
    name="statistics.update_dataset_statistics",
    max_retries=3,
    soft_time_limit=300,  # 5 minutes timeout
    retry_backoff=True,
)
def update_dataset_statistics(self, dataset_id: int, trigger_type: str = "manual") -> Dict[str, Any]:
    """
    Update statistics for a specific dataset in real-time.
    
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
                            'taxonomic_diversity': xml_data['taxonomic_diversity'],
                            'geographic_coverage': xml_data['geographic_coverage'],
                            'parsing_metadata': {
                                'schema_detected': xml_data['schema_detected'],
                                'parsing_date': xml_data['parsing_date'],
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
                    
                    # Store citation completeness
                    if xml_data['citation_completeness'] is not None:
                        stmt = insert(StatisticModel).values(
                            metric_type=MetricType.CITATION_COMPLETENESS,
                            entity_type=EntityType.DATASET,
                            entity_id=dataset_id,
                            period=Period.DAILY,
                            date=stat_date,
                            value=xml_data['citation_completeness'],
                            extra_data={
                                'archive_id': latest_archive.id,
                                'total_units': xml_data['unit_count'],
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
                        collected_stats.append(f"Dataset {dataset_id} citation completeness updated: {xml_data['citation_completeness']:.3f}")
                    
                    # Store geographic coverage
                    geo_score = min(100.0, (xml_data['geographic_coverage']['countries'] * 10 +
                                          xml_data['geographic_coverage']['coordinates'] * 0.1))
                    
                    stmt = insert(StatisticModel).values(
                        metric_type=MetricType.GEOGRAPHIC_COVERAGE,
                        entity_type=EntityType.DATASET,
                        entity_id=dataset_id,
                        period=Period.DAILY,
                        date=stat_date,
                        value=geo_score,
                        extra_data={
                            'archive_id': latest_archive.id,
                            'countries_count': xml_data['geographic_coverage']['countries'],
                            'coordinates_count': xml_data['geographic_coverage']['coordinates'],
                            'countries_sample': xml_data.get('countries_list', [])[:10],
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
                    collected_stats.append(f"Dataset {dataset_id} geographic coverage updated: {geo_score:.2f}")
                
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
    name="statistics.update_provider_biological_units",
    max_retries=3,
    soft_time_limit=300,  # 5 minutes timeout
    retry_backoff=True,
)
def update_provider_biological_units(self, provider_id: int, target_date: str = None, trigger_type: str = "manual") -> Dict[str, Any]:
    """
    Update biological units statistics for a specific provider.
    
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
        else:
            dataset_id_list = [dataset_id[0] for dataset_id in dataset_ids]
            
            # Get the most recent unit count for each dataset
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
    name="statistics.update_validation_statistics",
    max_retries=3,
    soft_time_limit=300,  # 5 minutes timeout
    retry_backoff=True,
)
def update_validation_statistics(self, validation_job_id: int = None, trigger_type: str = "completion") -> Dict[str, Any]:
    """
    Update validation statistics when a validation job completes.
    
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
    name="statistics.update_provider_dataset_count_after_deletion",
    max_retries=3,
    soft_time_limit=300,  # 5 minutes timeout
    retry_backoff=True,
)
def update_provider_dataset_count_after_deletion(self, provider_id: int, trigger_type: str = "dataset_deletion") -> Dict[str, Any]:
    """
    Update provider dataset count timeline after a dataset deletion.
    This ensures the Dataset Registration Timeline reflects deletions immediately.
    
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