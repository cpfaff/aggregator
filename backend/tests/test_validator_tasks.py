"""Regression tests for the validate_archive Celery task (B24, B25).

These exercise the task body directly against the Postgres testcontainer.
SessionLocal is patched to a factory that hands each "attempt" its own session
on the shared engine (mirroring how Celery opens a fresh session per run), and
ValidatorService is mocked so we drive success/failure deterministically.
"""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models import ValidationJobModel, XmlArchiveModel
from app.tasks import validator_tasks
from app.tasks.validator_tasks import validate_archive

_REPORT = {"summary": {"total_files": 1, "valid_files": 1, "total_time": 0.1}}


def _seed_archive(session) -> int:
    archive = XmlArchiveModel(url="http://example.com/a.xml", isLatest=True)
    session.add(archive)
    session.commit()
    return archive.id


def _session_factory(engine):
    def make():
        return Session(engine, expire_on_commit=False)

    return make


def _reraise_retry(*args, exc=None, **kwargs):
    """Stand-in for Task.retry: re-raise the original exception instead of
    Celery's autoretry re-executing the body, so each __call__ is one attempt."""
    raise exc if exc is not None else Exception("retry")


def test_retry_without_job_id_reuses_single_job_row(sync_engine, sync_db_session):
    """An autoretry re-enters with job_id=None; it must reuse the job created on
    the prior attempt instead of inserting a duplicate row each time (B24)."""
    archive_id = _seed_archive(sync_db_session)

    with (
        patch.object(validator_tasks, "SessionLocal", _session_factory(sync_engine)),
        patch.object(validator_tasks, "ValidatorService") as mock_vs,
        patch.object(validate_archive, "retry", side_effect=_reraise_retry),
    ):
        mock_vs.return_value.validate_archive.side_effect = [
            Exception("transient network error"),
            _REPORT,
        ]
        with pytest.raises(Exception):  # noqa: B017 - attempt 1 fails
            validate_archive(archive_id)
        validate_archive(archive_id)  # attempt 2 (the retry) succeeds

    sync_db_session.expire_all()
    rows = (
        sync_db_session.query(ValidationJobModel)
        .filter(ValidationJobModel.archive_id == archive_id)
        .all()
    )
    assert len(rows) == 1
    assert rows[0].status == "completed"
