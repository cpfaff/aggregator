"""A task that gives up must land in a durable, redrivable dead-letter sink (RH-07).

Two defects, one requirement pair (REQ-CEL-2 + REQ-CEL-2b):

* ``test_no_phantom_dead_letter_setting`` — ``celery_app.py`` sets
  ``task_dead_letter_queue_config={...}``, which is NOT a real Celery setting; it
  is stored inertly in ``conf.table()`` and misleads the reader (REQ-CEL-2b).
  Pre-fix the key IS present (RED); after removal it is gone.

* ``test_failed_task_payload_is_persisted`` — the only give-up behaviour today is
  a ``logger.critical``; the message is then acked and the payload is lost. The
  fix persists ``{task_id, task_name, args, kwargs, exception, timestamp}`` to a
  new ``failed_tasks`` table on ``LoggingTask.on_failure`` (REQ-CEL-2). Pre-fix
  there is no sink (RED) — driving ``on_failure`` writes no row.

* ``test_successful_task_not_dead_lettered`` — a normal success path must write
  NO ``failed_tasks`` row (the sink is the give-up path only).

The persistence tests drive the base-class hook directly against the Postgres
testcontainer with ``SessionLocal`` patched to a per-call session factory on the
shared engine (mirroring how a Celery worker opens a fresh session per task).
"""

from unittest.mock import patch

from sqlalchemy.orm import Session

from app.core import task_base
from app.core.celery_app import celery_app
from app.core.task_base import LoggingTask
from app.models.failed_task import FailedTaskModel


def _session_factory(engine):
    def make():
        return Session(engine, expire_on_commit=False)

    return make


def test_no_phantom_dead_letter_setting():
    """The config must carry no setting that silently does nothing (REQ-CEL-2b).

    ``task_dead_letter_queue_config`` is not a real Celery key; an inert key in
    ``conf.table()`` misleads the next reader into believing a DLQ exists.
    Pre-fix this key IS present (RED).
    """
    assert "task_dead_letter_queue_config" not in celery_app.conf.table()


def test_failed_task_payload_is_persisted(sync_engine, sync_db_session):
    """A final task failure persists exactly one redrivable ``failed_tasks`` row.

    Drives ``LoggingTask.on_failure`` (the give-up path) with a real DB session
    and asserts the row carries the task name, the args, and the exception text.
    Pre-fix no sink exists, so zero rows are written (RED).
    """
    task = LoggingTask()
    task.name = "tests.boom_task"
    exc = ValueError("archive 42 exploded")

    with patch.object(task_base, "SessionLocal", _session_factory(sync_engine)):
        task.on_failure(
            exc,
            "task-id-abc",
            args=("archive-42",),
            kwargs={"force": True},
            einfo=None,
        )

    rows = sync_db_session.query(FailedTaskModel).all()
    assert len(rows) == 1, f"expected exactly one dead-letter row, got {len(rows)}"
    row = rows[0]
    assert row.task_name == "tests.boom_task"
    assert row.task_id == "task-id-abc"
    assert "archive-42" in (row.args or "")
    assert "force" in (row.kwargs or "")
    assert "archive 42 exploded" in (row.exception or "")


def test_successful_task_not_dead_lettered(sync_engine, sync_db_session):
    """A normal success path writes NO ``failed_tasks`` row.

    The dead-letter sink is the give-up path only; ``on_success`` must never
    persist a failure record.
    """
    task = LoggingTask()
    task.name = "tests.happy_task"

    with patch.object(task_base, "SessionLocal", _session_factory(sync_engine)):
        task.on_success("ok", "task-id-ok", args=(), kwargs={})

    rows = sync_db_session.query(FailedTaskModel).all()
    assert len(rows) == 0, f"a successful task wrote {len(rows)} dead-letter rows, expected 0"
