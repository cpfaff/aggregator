"""Durable dead-letter sink for tasks that exhaust retries or are rejected.

This is the real give-up store behind RH-07 / REQ-CEL-2. When a Celery task
reaches its FINAL failure path (``LoggingTask.on_failure``), its payload is
persisted here so it can be inspected and redriven — replacing the old phantom
``task_dead_letter_queue_config`` key (which was inert) and the
log-then-ack-and-drop behaviour that lost the payload (RH-07 / REQ-CEL-2b).

This is an append-only audit table: one row per final task failure.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.models.base import Base

# Bound on the serialized args / kwargs / exception text stored per row. A
# validation payload may be large; the dead-letter sink must stay cheap to write
# and must never let a single failure blow up the table, so each free-form field
# is truncated to this many characters before insert (RH-07 key consideration:
# "huge args").
MAX_FIELD_CHARS = 4000


class FailedTaskModel(Base):
    """A single Celery task's final-failure payload, persisted for redrive.

    Attributes:
        id: Primary key.
        task_id: Celery task id (may be ``None`` if the request had none).
        task_name: Registered task name (e.g. ``validator.validate_archive``).
        args: Bounded ``repr`` of the task positional args.
        kwargs: Bounded ``repr`` of the task keyword args.
        exception: Bounded text of the last exception (``type: message``).
        created_at: When the failure was recorded (UTC).
    """

    __tablename__ = "failed_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, nullable=True, index=True)
    task_name = Column(String, nullable=False, index=True)
    args = Column(Text, nullable=True)
    kwargs = Column(Text, nullable=True)
    exception = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<FailedTask(id={self.id}, task_name={self.task_name!r}, task_id={self.task_id!r})>"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "args": self.args,
            "kwargs": self.kwargs,
            "exception": self.exception,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
