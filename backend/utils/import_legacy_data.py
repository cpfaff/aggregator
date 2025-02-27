import json
import asyncio
import logging
import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import text
from dotenv import load_dotenv
import os
from main import DataProviderModel, DatasetModel, XmlArchiveModel, UsefulLinkModel, UserModel, Base

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('config.env')

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def create_tables():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Created database tables")
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        raise

async def create_admin_user(session: AsyncSession):
    try:
        # Check if admin user exists
        result = await session.execute(
            select(UserModel).where(UserModel.username == "admin")
        )
        if result.scalar_one_or_none():
            logger.info("Admin user already exists")
            return

        # Create admin user
        hashed_password = bcrypt.hashpw("admin".encode(), bcrypt.gensalt()).decode()
        admin_user = UserModel(
            username="admin",
            hashed_password=hashed_password,
            is_global_admin=True
        )
        session.add(admin_user)
        await session.flush()
        logger.info("Created admin user")
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")
        raise

async def import_provider(session: AsyncSession, provider_data: dict) -> DataProviderModel:
    try:
        # Check if provider already exists
        result = await session.execute(
            select(DataProviderModel).where(DataProviderModel.id == provider_data['id'])
        )
        existing_provider = result.scalar_one_or_none()
        
        if existing_provider:
            logger.info(f"Provider {provider_data['shortName']} already exists, skipping...")
            return existing_provider

        # Create new provider
        provider = DataProviderModel(
            id=provider_data['id'],
            datacenter=provider_data['datacenter'],
            shortName=provider_data['shortName'],
            name=provider_data['name'],
            url=provider_data['url'],
            biocaseUrl=provider_data.get('biocaseUrl')
        )
        session.add(provider)
        await session.flush()
        logger.info(f"Created provider: {provider.shortName}")
        return provider
    except Exception as e:
        logger.error(f"Error importing provider {provider_data.get('shortName')}: {str(e)}")
        raise

async def import_dataset(session: AsyncSession, dataset_data: dict, provider_id: int) -> DatasetModel:
    try:
        # Check if dataset already exists
        result = await session.execute(
            select(DatasetModel).where(DatasetModel.id == dataset_data['id'])
        )
        existing_dataset = result.scalar_one_or_none()
        
        if existing_dataset:
            logger.info(f"Dataset {dataset_data['title']} already exists, skipping...")
            return existing_dataset

        # Create new dataset
        dataset = DatasetModel(
            id=dataset_data['id'],
            provider_id=provider_id,
            source=dataset_data['source'],
            title=dataset_data['title'],
            landingPageUrl=dataset_data.get('landingPageUrl')
        )
        session.add(dataset)
        await session.flush()
        logger.info(f"Created dataset: {dataset.title}")
        return dataset
    except Exception as e:
        logger.error(f"Error importing dataset {dataset_data.get('title')}: {str(e)}")
        raise

async def import_xml_archives(session: AsyncSession, archives_data: list, dataset_id: int):
    try:
        for archive in archives_data:
            # Check if archive already exists
            result = await session.execute(
                select(XmlArchiveModel).where(XmlArchiveModel.id == archive['id'])
            )
            if result.scalar_one_or_none():
                logger.info(f"XML Archive {archive['id']} already exists, skipping...")
                continue

            # Create new archive
            xml_archive = XmlArchiveModel(
                id=archive['id'],
                dataset_id=dataset_id,
                url=archive['url'],
                isLatest=archive['isLatest']
            )
            session.add(xml_archive)
        await session.flush()
        logger.info(f"Created {len(archives_data)} XML archives for dataset {dataset_id}")
    except Exception as e:
        logger.error(f"Error importing XML archives for dataset {dataset_id}: {str(e)}")
        raise

async def import_useful_links(session: AsyncSession, links_data: list, dataset_id: int):
    try:
        for link in links_data:
            # Check if link already exists
            result = await session.execute(
                select(UsefulLinkModel).where(UsefulLinkModel.id == link['id'])
            )
            if result.scalar_one_or_none():
                logger.info(f"Useful Link {link['id']} already exists, skipping...")
                continue

            # Create new link
            useful_link = UsefulLinkModel(
                id=link['id'],
                dataset_id=dataset_id,
                title=link['title'],
                url=link['url'],
                isLatest=link['isLatest']
            )
            session.add(useful_link)
        await session.flush()
        logger.info(f"Created {len(links_data)} useful links for dataset {dataset_id}")
    except Exception as e:
        logger.error(f"Error importing useful links for dataset {dataset_id}: {str(e)}")
        raise

async def clear_existing_data(session: AsyncSession):
    try:
        # Delete in reverse order of dependencies
        await session.execute(text("DELETE FROM useful_links"))
        await session.execute(text("DELETE FROM xml_archives"))
        await session.execute(text("DELETE FROM datasets"))
        await session.execute(text("DELETE FROM data_providers"))
        await session.execute(text("DELETE FROM users"))
        await session.flush()
        logger.info("Cleared existing data from all tables")
    except Exception as e:
        logger.error(f"Error clearing existing data: {str(e)}")
        raise

async def reset_sequences(session: AsyncSession):
    """Reset all sequences to be after the highest existing ID"""
    try:
        # Get maximum IDs from all tables
        provider_max = await session.execute(text("SELECT MAX(id) FROM data_providers"))
        dataset_max = await session.execute(text("SELECT MAX(id) FROM datasets"))
        xml_max = await session.execute(text("SELECT MAX(id) FROM xml_archives"))
        links_max = await session.execute(text("SELECT MAX(id) FROM useful_links"))

        # Get the values, default to 0 if table is empty
        provider_max_id = provider_max.scalar() or 0
        dataset_max_id = dataset_max.scalar() or 0
        xml_max_id = xml_max.scalar() or 0
        links_max_id = links_max.scalar() or 0

        # Reset all sequences
        await session.execute(text(f"ALTER SEQUENCE data_providers_id_seq RESTART WITH {provider_max_id + 1}"))
        await session.execute(text(f"ALTER SEQUENCE datasets_id_seq RESTART WITH {dataset_max_id + 1}"))
        await session.execute(text(f"ALTER SEQUENCE xml_archives_id_seq RESTART WITH {xml_max_id + 1}"))
        await session.execute(text(f"ALTER SEQUENCE useful_links_id_seq RESTART WITH {links_max_id + 1}"))
        
        await session.commit()
        
        logger.info(f"Reset sequences to: providers={provider_max_id + 1}, datasets={dataset_max_id + 1}, "
                    f"xml_archives={xml_max_id + 1}, useful_links={links_max_id + 1}")
    except Exception as e:
        logger.error(f"Error resetting sequences: {str(e)}")
        raise

async def import_all_data():
    """Import all data from the legacy database"""
    async with async_session() as session:
        try:
            logger.info("Starting data import from legacy database")
            
            # First clear existing data if any
            await clear_existing_data(session)
            
            # Read the JSON file from data directory
            json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'providers.json')
            with open(json_path, 'r') as f:
                data = json.load(f)

            # Import providers and their nested resources
            for provider_data in data:
                provider = await import_provider(session, provider_data)
                
                for dataset_data in provider_data.get('datasets', []):
                    dataset = await import_dataset(session, dataset_data, provider.id)
                    
                    if dataset_data.get('xmlArchives'):
                        await import_xml_archives(session, dataset_data['xmlArchives'], dataset.id)
                    
                    if dataset_data.get('usefulLinks'):
                        await import_useful_links(session, dataset_data['usefulLinks'], dataset.id)
            
            # After import, reset sequences to be after the highest IDs
            await reset_sequences(session)
            
            logger.info("Data import completed successfully")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error during import: {str(e)}")
            raise

if __name__ == "__main__":
    asyncio.run(import_all_data())
