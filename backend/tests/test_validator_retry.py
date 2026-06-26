"""Retry-classification tests for the validate_archive Celery task (RH-09).

A deterministic failure (archive-not-found) must NOT consume the retry budget:
the autoretry must fire only for transient infrastructure errors. These exercise
the task body directly against the Postgres testcontainer, with SessionLocal
patched to a per-attempt session factory on the shared engine (mirroring how
Celery opens a fresh session per run) and ValidatorService mocked so we drive
the failure class deterministically. ``validate_archive.retry`` is spied so we
observe whether Celery's autoretry machinery decided to retry.
"""

from unittest.mock import patch

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models import XmlArchiveModel
from app.tasks import validator_tasks
from app.tasks.validator_tasks import PermanentTaskError, validate_archive

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


def test_archive_not_found_is_not_retried(sync_engine, sync_db_session):
    """A missing archive is deterministic: it is missing on every retry, so the
    retry budget must never be spent on it. With no archive row seeded, calling
    the task must surface the not-found error WITHOUT Celery's autoretry firing
    (retry spy untouched)."""
    with (
        patch.object(validator_tasks, "SessionLocal", _session_factory(sync_engine)),
        patch.object(validate_archive, "retry") as retry_spy,
        pytest.raises(PermanentTaskError, match="not found"),
    ):
        validate_archive(999999)  # no archive row with this id

    assert retry_spy.call_count == 0


def test_transient_error_is_retried(sync_engine, sync_db_session):
    """A transient infrastructure error (e.g. a DB OperationalError raised while
    validating) IS retriable: Celery's autoretry must invoke retry so the work
    is re-attempted."""
    archive_id = _seed_archive(sync_db_session)

    def _reraise_retry(*args, exc=None, **kwargs):
        raise exc if exc is not None else Exception("retry")

    with (
        patch.object(validator_tasks, "SessionLocal", _session_factory(sync_engine)),
        patch.object(validator_tasks, "ValidatorService") as mock_vs,
        patch.object(validate_archive, "retry", side_effect=_reraise_retry) as retry_spy,
    ):
        mock_vs.return_value.validate_archive.side_effect = OperationalError(
            "SELECT 1", {}, Exception("connection reset")
        )
        with pytest.raises(OperationalError):
            validate_archive(archive_id)

    assert retry_spy.call_count >= 1
