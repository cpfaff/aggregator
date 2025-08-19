"""remove deprecated statistics metrics

Revision ID: 6af81fd1122b
Revises: eeee34d2629a
Create Date: 2025-08-19 12:02:43.127150

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6af81fd1122b'
down_revision: Union[str, None] = 'eeee34d2629a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Delete old data for deprecated metrics
    op.execute("""
        DELETE FROM statistics 
        WHERE metric_type IN ('citation_completeness', 'geographic_coverage', 'provider_unit_count', 'system_unit_count')
    """)
    
    # Drop the old constraint
    op.drop_constraint('valid_metric_type', 'statistics', type_='check')
    
    # Add the new constraint without deprecated metrics
    op.create_check_constraint(
        'valid_metric_type',
        'statistics',
        "metric_type IN ('dataset_count', 'dataset_registration_rate', 'dataset_modification_rate', "
        "'dataset_unit_count', 'provider_count', 'provider_dataset_count', 'provider_activity_score', "
        "'provider_biological_units', 'validation_success_rate', 'validation_error_rate', 'validation_processing_time', "
        "'validation_job_count', 'abcd_compliance_rate', 'xml_archive_count', "
        "'system_storage_size', 'system_processing_load', 'system_api_response_time')"
    )


def downgrade() -> None:
    # Drop the new constraint
    op.drop_constraint('valid_metric_type', 'statistics', type_='check')
    
    # Restore the old constraint with deprecated metrics
    op.create_check_constraint(
        'valid_metric_type',
        'statistics',
        "metric_type IN ('dataset_count', 'dataset_registration_rate', 'dataset_modification_rate', "
        "'dataset_unit_count', 'provider_count', 'provider_dataset_count', 'provider_activity_score', "
        "'provider_unit_count', 'provider_biological_units', 'validation_success_rate', 'validation_error_rate', 'validation_processing_time', "
        "'validation_job_count', 'abcd_compliance_rate', 'xml_archive_count', 'citation_completeness', "
        "'geographic_coverage', 'system_storage_size', 'system_processing_load', 'system_api_response_time', "
        "'system_unit_count')"
    )
    # Note: We don't restore the deleted data in downgrade
