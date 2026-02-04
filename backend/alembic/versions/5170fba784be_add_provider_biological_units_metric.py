"""add_provider_biological_units_metric

Revision ID: 5170fba784be
Revises: 92bd2a56238f
Create Date: 2025-08-14 08:45:31.703907

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5170fba784be"
down_revision: str | None = "92bd2a56238f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop the existing constraint
    op.drop_constraint("valid_metric_type", "statistics", type_="check")

    # Add the new constraint with the additional metric type
    op.create_check_constraint(
        "valid_metric_type",
        "statistics",
        "metric_type IN ('dataset_count', 'dataset_registration_rate', 'dataset_modification_rate', "
        "'dataset_unit_count', 'provider_count', 'provider_dataset_count', 'provider_activity_score', "
        "'provider_unit_count', 'provider_biological_units', 'validation_success_rate', 'validation_error_rate', 'validation_processing_time', "
        "'validation_job_count', 'abcd_compliance_rate', 'xml_archive_count', 'citation_completeness', "
        "'geographic_coverage', 'system_storage_size', 'system_processing_load', 'system_api_response_time', "
        "'system_unit_count')",
    )


def downgrade() -> None:
    # Drop the updated constraint
    op.drop_constraint("valid_metric_type", "statistics", type_="check")

    # Restore the original constraint without provider_biological_units
    op.create_check_constraint(
        "valid_metric_type",
        "statistics",
        "metric_type IN ('dataset_count', 'dataset_registration_rate', 'dataset_modification_rate', "
        "'dataset_unit_count', 'provider_count', 'provider_dataset_count', 'provider_activity_score', "
        "'provider_unit_count', 'validation_success_rate', 'validation_error_rate', 'validation_processing_time', "
        "'validation_job_count', 'abcd_compliance_rate', 'xml_archive_count', 'citation_completeness', "
        "'geographic_coverage', 'system_storage_size', 'system_processing_load', 'system_api_response_time', "
        "'system_unit_count')",
    )
