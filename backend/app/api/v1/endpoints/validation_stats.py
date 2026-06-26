"""Public batch validation-stats endpoint for the GFBio search interface.

The search index never carries validation results (the data centers declined to
bind validation to harvesting), so the search backend enriches each result page
at render time by POSTing the page's ``abcdDatasetIdentifier`` values here and
merging the returned headline numbers onto each card.

This endpoint is the **public, read-only** sibling of the harvest feed
(``/legacy-data-sets``): unauthenticated and server-to-server, it exposes only
*aggregate* quality (file counts, weighted quality score, mandatory / recommended
valid percentages) — never the per-rule defect report, which stays behind the
authenticated DPM endpoints (B12 provider-scope). It performs **no writes** and
needs **no Elasticsearch** (validation lives entirely in Postgres), so it is
unaffected by the harvest-status ES wiring.

Identifiers are parsed back to dataset ids via :func:`parse_dataset_urn` (the
inverse of the URN the aggregator stamps), the DB is read once for the whole
batch, and the per-dataset summaries are re-keyed onto the exact identifier
strings the caller sent. Malformed identifiers and datasets with no validation
record are silently skipped, so one bad id never fails the page.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import limiter
from app.core.config import settings
from app.db import get_db
from app.services.es_gateway import parse_dataset_urn
from app.services.validation_service import ValidationService

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]

# Bound the per-request work. A search page is small (tens of hits); this cap
# protects the public endpoint without ever clipping a real result page.
MAX_IDENTIFIERS = 500


class ValidationStatsRequest(BaseModel):
    """Batch request: the ``abcdDatasetIdentifier`` values from one result page."""

    identifiers: list[Annotated[str, StringConstraints(max_length=512)]] = Field(
        default_factory=list,
        max_length=MAX_IDENTIFIERS,
        description="abcdDatasetIdentifier term values (dataset or unit URNs).",
    )


class DatasetValidationSummary(BaseModel):
    """Aggregate, public-safe validation numbers for a single dataset."""

    identifier: str
    dataset_id: int
    archive_id: int | None = None
    validation_status: str | None = None
    last_validated_at: datetime | None = None
    is_valid: bool | None = None
    quality_score: float | None = None
    mandatory_percentage: float | None = None
    recommended_percentage: float | None = None
    total_files: int | None = None
    valid_files: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ValidationStatsResponse(BaseModel):
    """Map of inbound identifier -> its validation summary (unknowns omitted)."""

    results: dict[str, DatasetValidationSummary] = Field(default_factory=dict)


@router.post("/validation-stats", response_model=ValidationStatsResponse)
@limiter.limit(settings.PUBLIC_STATS_RATE_LIMIT)
async def get_validation_stats(
    request: Request, payload: ValidationStatsRequest, db: DbSession
) -> ValidationStatsResponse:
    """Return validation summaries for a page of ``abcdDatasetIdentifier`` values."""
    # Parse each identifier to its dataset id; skip anything malformed.
    identifier_to_dataset: dict[str, int] = {}
    for identifier in payload.identifiers:
        parsed = parse_dataset_urn(identifier)
        if parsed is not None:
            identifier_to_dataset[identifier] = parsed[1]  # (provider, dataset, archive)

    # One batched DB read for the deduplicated set of dataset ids.
    dataset_ids = sorted(set(identifier_to_dataset.values()))
    service = ValidationService(db)
    stats_by_dataset = await service.get_validation_stats_for_datasets(dataset_ids)

    # Re-key onto the exact identifiers the caller holds; omit unknown datasets.
    results: dict[str, DatasetValidationSummary] = {}
    for identifier, dataset_id in identifier_to_dataset.items():
        stats = stats_by_dataset.get(dataset_id)
        if stats is not None:
            results[identifier] = DatasetValidationSummary(identifier=identifier, **stats)

    return ValidationStatsResponse(results=results)
