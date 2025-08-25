"""
Test dataset cascade deletion functionality.
"""
import asyncio
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func

from app.services.dataset_deletion import DatasetDeletionService
from app.models.dataset import DatasetModel, XmlArchiveModel, UsefulLinkModel
from app.models.validation import ValidationJobModel
from app.models.statistics import StatisticModel, EntityType, MetricType, Period
from app.models.provider import DataProviderModel


async def test_cascade_deletion():
    """Test that deleting a dataset removes all associated data."""
    
    # Create async engine and session for testing
    DATABASE_URL = "postgresql+asyncpg://user:password@postgres:5432/dbname"
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as db:
        try:
            # First, find a test dataset we can work with
            result = await db.execute(
                select(DatasetModel)
                .where(DatasetModel.title.like('%test%'))
                .limit(1)
            )
            test_dataset = result.scalar_one_or_none()
            
            if not test_dataset:
                print("❌ No test dataset found. Creating one...")
                
                # Find a provider to use
                provider_result = await db.execute(
                    select(DataProviderModel).limit(1)
                )
                provider = provider_result.scalar_one()
                
                # Create a test dataset
                test_dataset = DatasetModel(
                    provider_id=provider.id,
                    source="test_source",
                    title="Test Dataset for Deletion",
                    landingPageUrl="https://example.com/test"
                )
                db.add(test_dataset)
                await db.flush()
                
                # Add some test data
                # Add XML archive
                xml_archive = XmlArchiveModel(
                    dataset_id=test_dataset.id,
                    url="https://example.com/test.xml",
                    isLatest=True
                )
                db.add(xml_archive)
                await db.flush()
                
                # Add validation job
                validation_job = ValidationJobModel(
                    archive_id=xml_archive.id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(validation_job)
                
                # Add useful link
                useful_link = UsefulLinkModel(
                    dataset_id=test_dataset.id,
                    title="Test Link",
                    url="https://example.com/link",
                    isLatest=True
                )
                db.add(useful_link)
                
                # Add statistics
                for period in [Period.DAILY, Period.WEEKLY, Period.MONTHLY]:
                    stat = StatisticModel(
                        entity_type=EntityType.DATASET,
                        entity_id=test_dataset.id,
                        metric_type=MetricType.DATASET_UNIT_COUNT,
                        period=period,
                        date=date.today(),
                        value=100,
                        extra_data={"test": True}
                    )
                    db.add(stat)
                
                await db.commit()
                print(f"✅ Created test dataset with ID {test_dataset.id}")
            
            dataset_id = test_dataset.id
            provider_id = test_dataset.provider_id
            
            # Check what data exists before deletion
            print(f"\n📊 Checking data for dataset {dataset_id} before deletion...")
            
            # Count statistics
            stats_count_result = await db.execute(
                select(func.count(StatisticModel.id))
                .where(
                    StatisticModel.entity_type == EntityType.DATASET,
                    StatisticModel.entity_id == dataset_id
                )
            )
            stats_count = stats_count_result.scalar()
            print(f"  - Statistics records: {stats_count}")
            
            # Count XML archives
            archives_count_result = await db.execute(
                select(func.count(XmlArchiveModel.id))
                .where(XmlArchiveModel.dataset_id == dataset_id)
            )
            archives_count = archives_count_result.scalar()
            print(f"  - XML archives: {archives_count}")
            
            # Get archive IDs for validation job check
            archive_ids_result = await db.execute(
                select(XmlArchiveModel.id)
                .where(XmlArchiveModel.dataset_id == dataset_id)
            )
            archive_ids = [row[0] for row in archive_ids_result.fetchall()]
            
            # Count validation jobs
            validation_count = 0
            if archive_ids:
                validation_count_result = await db.execute(
                    select(func.count(ValidationJobModel.id))
                    .where(ValidationJobModel.archive_id.in_(archive_ids))
                )
                validation_count = validation_count_result.scalar()
            print(f"  - Validation jobs: {validation_count}")
            
            # Count useful links
            links_count_result = await db.execute(
                select(func.count(UsefulLinkModel.id))
                .where(UsefulLinkModel.dataset_id == dataset_id)
            )
            links_count = links_count_result.scalar()
            print(f"  - Useful links: {links_count}")
            
            # Now perform cascade deletion
            print(f"\n🗑️  Performing cascade deletion of dataset {dataset_id}...")
            deletion_service = DatasetDeletionService(db)
            result = await deletion_service.delete_dataset_cascade(
                dataset_id=dataset_id,
                provider_id=provider_id
            )
            
            print(f"\n📝 Deletion summary:")
            print(f"  Status: {result['status']}")
            for entity_type, count in result['deleted_counts'].items():
                print(f"  - {entity_type}: {count} deleted")
            
            # Verify all data is gone
            print(f"\n✅ Verifying data is deleted...")
            
            # Check dataset is gone
            dataset_check = await db.execute(
                select(DatasetModel).where(DatasetModel.id == dataset_id)
            )
            if dataset_check.scalar_one_or_none():
                print("  ❌ Dataset still exists!")
            else:
                print("  ✅ Dataset deleted")
            
            # Check statistics are gone
            stats_check = await db.execute(
                select(func.count(StatisticModel.id))
                .where(
                    StatisticModel.entity_type == EntityType.DATASET,
                    StatisticModel.entity_id == dataset_id
                )
            )
            remaining_stats = stats_check.scalar()
            if remaining_stats > 0:
                print(f"  ❌ {remaining_stats} statistics records still exist!")
            else:
                print("  ✅ All statistics deleted")
            
            # Check XML archives are gone
            archives_check = await db.execute(
                select(func.count(XmlArchiveModel.id))
                .where(XmlArchiveModel.dataset_id == dataset_id)
            )
            remaining_archives = archives_check.scalar()
            if remaining_archives > 0:
                print(f"  ❌ {remaining_archives} XML archives still exist!")
            else:
                print("  ✅ All XML archives deleted")
            
            # Check validation jobs are gone
            if archive_ids:
                validation_check = await db.execute(
                    select(func.count(ValidationJobModel.id))
                    .where(ValidationJobModel.archive_id.in_(archive_ids))
                )
                remaining_validation = validation_check.scalar()
                if remaining_validation > 0:
                    print(f"  ❌ {remaining_validation} validation jobs still exist!")
                else:
                    print("  ✅ All validation jobs deleted")
            
            # Check useful links are gone
            links_check = await db.execute(
                select(func.count(UsefulLinkModel.id))
                .where(UsefulLinkModel.dataset_id == dataset_id)
            )
            remaining_links = links_check.scalar()
            if remaining_links > 0:
                print(f"  ❌ {remaining_links} useful links still exist!")
            else:
                print("  ✅ All useful links deleted")
            
            print("\n✅ Cascade deletion test completed!")
            
        except Exception as e:
            print(f"\n❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_cascade_deletion())