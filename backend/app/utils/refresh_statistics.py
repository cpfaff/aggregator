#!/usr/bin/env python3
"""
Management command to trigger comprehensive statistics collection.
Can be run as: python -m app.utils.refresh_statistics
"""

import sys
import argparse
from datetime import datetime
from typing import Optional, List

# Add the app directory to path
sys.path.insert(0, '/app')

from app.db.session import SessionLocal
from app.tasks.statistics_tasks import (
    analyze_xml_archives,
    collect_daily_statistics,
    collect_provider_biological_units
)
from sqlalchemy import text


def queue_xml_analysis(batch_size: int = 10, specific_datasets: Optional[List[int]] = None):
    """Queue XML archive analysis for unit counting."""
    db = SessionLocal()
    try:
        if specific_datasets:
            # Process specific datasets only
            archive_query = text('''
                SELECT xa.id, xa.dataset_id
                FROM xml_archives xa
                WHERE xa."isLatest" = true 
                AND xa.dataset_id = ANY(:datasets)
                ORDER BY xa.id
            ''')
            result = db.execute(archive_query, {'datasets': specific_datasets})
            archives = result.fetchall()
            total_archives = len(archives)
            
            print(f"Found {total_archives} archives for datasets: {specific_datasets}")
            
            # For specific datasets, queue a single task with the dataset IDs
            if total_archives > 0:
                task = analyze_xml_archives.delay(
                    batch_size=total_archives,  # Process all at once
                    offset=0,
                    dataset_ids=specific_datasets  # Pass the specific dataset IDs
                )
                tasks = [task.id]
                print(f"  Processing {total_archives} specific archives: Task {task.id}")
            else:
                tasks = []
                print("  No archives found for specified datasets")
                
            return tasks
        else:
            # Process all latest archives
            count_result = db.execute(text('''
                SELECT COUNT(*) FROM xml_archives WHERE "isLatest" = true
            '''))
            total_archives = count_result.scalar()
            
            # Check how many already have statistics
            processed_result = db.execute(text('''
                SELECT COUNT(DISTINCT xa.id) as processed
                FROM xml_archives xa
                JOIN statistics s ON s.entity_id = xa.dataset_id
                WHERE xa."isLatest" = true 
                AND s.metric_type = 'dataset_unit_count'
                AND s.date = CURRENT_DATE
            '''))
            already_processed = processed_result.scalar()
            
            print(f"Total archives: {total_archives}")
            print(f"Already processed today: {already_processed}")
            print(f"To process: {total_archives - already_processed}")
        
            # Queue tasks for all archives using offset batching
            tasks = []
            for offset in range(0, total_archives, batch_size):
                task = analyze_xml_archives.delay(batch_size=batch_size, offset=offset)
                tasks.append(task.id)
                end_offset = min(offset + batch_size - 1, total_archives - 1)
                print(f"  Batch {offset:3d}-{end_offset:3d}: Task {task.id}")
        
            return tasks
        
    finally:
        db.close()


def queue_daily_statistics(use_today=False):
    """Queue daily statistics collection."""
    print("\nQueueing daily statistics collection...")
    if use_today:
        from datetime import date
        target_date = date.today().strftime("%Y-%m-%d")
        print(f"  Using TODAY's date: {target_date}")
        task = collect_daily_statistics.delay(target_date=target_date)
    else:
        print(f"  Using default (yesterday)")
        task = collect_daily_statistics.delay()
    print(f"  Task ID: {task.id}")
    return task.id


def queue_biological_units(use_today=False):
    """Queue biological units collection."""
    print("\nQueueing biological units collection...")
    if use_today:
        from datetime import date
        target_date = date.today().strftime("%Y-%m-%d")
        print(f"  Using TODAY's date: {target_date}")
        task = collect_provider_biological_units.delay(target_date=target_date)
    else:
        print(f"  Using default (yesterday)")
        task = collect_provider_biological_units.delay()
    print(f"  Task ID: {task.id}")
    return task.id


def check_statistics_status():
    """Check current statistics status."""
    db = SessionLocal()
    try:
        # Overall statistics
        result = db.execute(text('''
            SELECT 
                metric_type,
                COUNT(DISTINCT entity_id) as entities,
                COUNT(*) as total_records,
                MAX(date) as latest_date
            FROM statistics
            GROUP BY metric_type
            ORDER BY metric_type
        '''))
        
        print("\nCurrent Statistics Status:")
        print("-" * 60)
        for row in result:
            print(f"{row.metric_type:30} | {row.entities:4} entities | {row.total_records:5} records | Latest: {row.latest_date}")
        
        # Dataset coverage
        coverage_result = db.execute(text('''
            SELECT 
                COUNT(DISTINCT d.id) as total_datasets,
                COUNT(DISTINCT CASE WHEN s.entity_id IS NOT NULL THEN d.id END) as with_stats,
                COUNT(DISTINCT CASE WHEN s.entity_id IS NULL THEN d.id END) as without_stats
            FROM datasets d
            LEFT JOIN statistics s ON s.entity_id = d.id 
                AND s.metric_type = 'dataset_unit_count'
                AND s.entity_type = 'dataset'
        '''))
        
        row = coverage_result.fetchone()
        print(f"\nDataset Coverage:")
        print(f"  Total datasets: {row.total_datasets}")
        print(f"  With unit counts: {row.with_stats} ({row.with_stats*100//row.total_datasets}%)")
        print(f"  Without unit counts: {row.without_stats} ({row.without_stats*100//row.total_datasets}%)")
        
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Refresh statistics collection')
    parser.add_argument('--xml', action='store_true', help='Collect XML archive statistics')
    parser.add_argument('--daily', action='store_true', help='Collect daily statistics')
    parser.add_argument('--biological', action='store_true', help='Collect biological units')
    parser.add_argument('--all', action='store_true', help='Collect all statistics')
    parser.add_argument('--status', action='store_true', help='Show statistics status')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for XML processing')
    parser.add_argument('--datasets', type=str, help='Comma-separated dataset IDs to process')
    parser.add_argument('--today', action='store_true', help='Use today instead of yesterday for daily/biological stats (for manual fixes)')
    
    args = parser.parse_args()
    
    # If no specific flags, show status
    if not any([args.xml, args.daily, args.biological, args.all, args.status]):
        args.status = True
    
    print(f"Statistics Refresh Tool - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    if args.today and not (args.daily or args.biological or args.all):
        print("⚠️  Warning: --today flag only affects --daily and --biological stats")
        print("    XML archive processing always uses today's date")
    
    if args.status:
        check_statistics_status()
    
    tasks = []
    
    if args.all or args.xml:
        print("\n📊 Queueing XML Archive Analysis...")
        datasets = None
        if args.datasets:
            datasets = [int(d.strip()) for d in args.datasets.split(',')]
            print(f"  Processing specific datasets: {datasets}")
        xml_tasks = queue_xml_analysis(args.batch_size, datasets)
        tasks.extend(xml_tasks)
    
    if args.all or args.daily:
        if args.today:
            print("\n⚠️  Using TODAY for daily statistics (manual fix mode)")
        daily_task = queue_daily_statistics(use_today=args.today)
        tasks.append(daily_task)
    
    # Only queue biological units if NOT doing XML processing
    # When XML processing is done, it will handle biological units aggregation
    if args.biological and not (args.all or args.xml):
        if args.today:
            print("\n⚠️  Using TODAY for biological units (manual fix mode)")
        bio_task = queue_biological_units(use_today=args.today)
        tasks.append(bio_task)
    elif args.all:
        # For --all, we need to ensure proper sequencing
        print("\n📊 Note: Biological units will be collected after ALL tasks complete")
        print("    This ensures XML archives are fully processed before aggregation")
    elif args.xml:
        print("\n📊 Note: Biological units will be collected after XML archives are processed")
    
    if tasks:
        print(f"\n✓ Queued {len(tasks)} total tasks")
        print("\nMonitor progress with:")
        print('  docker logs -f searchgfbioorg-celery_worker-1 | grep "Successfully"')
        print("\nCheck results with:")
        print("  python -m app.utils.refresh_statistics --status")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())