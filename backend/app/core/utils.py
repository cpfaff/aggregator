from pydantic import AnyUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_cache
from app.models.dataset import DatasetModel


async def apply_entity_updates(
    db: AsyncSession,
    entity_list,
    new_entities,
    entity_class,
    dataset_id,
    entity_field="dataset_id",
):
    """
    Generic function to update relationships (XML archives, useful links, etc.)

    Args:
        db: Database session
        entity_list: Current list of entities
        new_entities: New entities from request
        entity_class: Model class of entity
        dataset_id: ID of parent dataset
        entity_field: Name of field referencing dataset ID

    Returns:
        List of updated entities
    """
    # Fetch the dataset to get provider_id for cache invalidation
    result = await db.execute(select(DatasetModel).where(DatasetModel.id == dataset_id))
    dataset = result.scalar_one_or_none()
    provider_id = dataset.provider_id if dataset else None

    # Map existing entities by ID
    existing_entities = {entity.id: entity for entity in entity_list if entity.id is not None}

    # Process entities with IDs
    processed_ids = set()
    updated_entities = []

    for new_entity in new_entities:
        if new_entity.id is not None and new_entity.id in existing_entities:
            entity = existing_entities[new_entity.id]
            processed_ids.add(new_entity.id)

            # Extract data from new entity
            entity_data = new_entity.model_dump(exclude={"id"}, exclude_unset=True)

            # Handle URL fields conversion
            for field, value in entity_data.items():
                if isinstance(value, AnyUrl):
                    entity_data[field] = str(value)

            # Update fields
            for key, value in entity_data.items():
                setattr(entity, key, value)

            updated_entities.append(entity)
        else:
            # Create new entity
            entity_data = new_entity.model_dump(exclude={"id"}, exclude_unset=True)

            # Handle URL fields conversion
            for field, value in entity_data.items():
                if isinstance(value, AnyUrl):
                    entity_data[field] = str(value)

            # Create and add new entity
            kwargs = {entity_field: dataset_id, **entity_data}
            new_entity_obj = entity_class(**kwargs)
            db.add(new_entity_obj)
            updated_entities.append(new_entity_obj)

    # Delete entities not in the update
    for entity_id, entity in existing_entities.items():
        if entity_id not in processed_ids:
            await db.delete(entity)

    await db.flush()

    # Invalidate related caches
    entity_type = entity_class.__tablename__.replace("_", "-")
    invalidate_cache(f"{entity_type}")
    invalidate_cache(f"dataset:{dataset_id}")
    invalidate_cache("datasets")
    if provider_id:
        invalidate_cache(f"provider:{provider_id}")
        invalidate_cache("providers")

    return updated_entities
