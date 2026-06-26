"""
Custom Celery task base class with enhanced error logging and retry handling.

Also hosts the durable dead-letter sink (RH-07 / REQ-CEL-2): when a task reaches
its FINAL failure path, ``LoggingTask.on_failure`` persists the give-up payload to
the ``failed_tasks`` table so it can be inspected and redriven, instead of merely
logging it and letting the message be acked and dropped.
"""

import logging

from celery import Task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded

from app.db.session import SessionLocal
from app.models.failed_task import MAX_FIELD_CHARS, FailedTaskModel

logger = logging.getLogger(__name__)


def _bounded(value: object) -> str:
    """Serialize ``value`` to a length-bounded string for durable storage.

    A failure payload (e.g. a large validation request) must never blow up the
    dead-letter row, so the ``repr`` is truncated to ``MAX_FIELD_CHARS`` with an
    explicit marker (RH-07 key consideration: "huge args"). ``repr`` is used so
    the value never has to be JSON-serializable to be recorded.
    """
    text = repr(value)
    if len(text) > MAX_FIELD_CHARS:
        return text[:MAX_FIELD_CHARS] + "…[truncated]"
    return text


class LoggingTask(Task):
    """
    Custom task base class that provides enhanced logging for retries and failures.

    This class logs:
    - Retry attempts with queue information and retry count
    - Final failures with full context
    - Structured logging fields for monitoring and alerting
    """

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """
        Called when a task is retried.

        Logs structured information about the retry including:
        - Task name and ID
        - Queue name
        - Retry count
        - Exception details
        - Task arguments
        """
        retry_count = self.request.retries if hasattr(self, "request") else 0
        queue_name = (
            self.request.queue
            if hasattr(self, "request") and hasattr(self.request, "queue")
            else "unknown"
        )

        # Structured logging for retry
        log_data = {
            "event": "task_retry",
            "task_name": self.name,
            "task_id": task_id,
            "queue_name": queue_name,
            "retry_count": retry_count,
            "max_retries": self.max_retries,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "args": str(args)[:500],  # Truncate long args
            "kwargs": str(kwargs)[:500],  # Truncate long kwargs
        }

        logger.warning(
            f"Task {self.name} [{task_id}] retrying (attempt {retry_count + 1}/{self.max_retries + 1}) "
            f"in queue '{queue_name}' due to {type(exc).__name__}: {exc}",
            extra={"structured_log": log_data},
        )

        # Call parent implementation
        super().on_retry(exc, task_id, args, kwargs, einfo)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Called when a task fails after all retries are exhausted.

        Logs structured information about the failure including:
        - Task name and ID
        - Queue name
        - Total retry attempts
        - Exception details with traceback
        - Task arguments
        - Whether this is going to dead letter queue
        """
        retry_count = self.request.retries if hasattr(self, "request") else 0
        queue_name = (
            self.request.queue
            if hasattr(self, "request") and hasattr(self.request, "queue")
            else "unknown"
        )

        # Check if this is a max retries exceeded error
        is_max_retries = isinstance(exc, MaxRetriesExceededError)
        is_soft_timeout = isinstance(exc, SoftTimeLimitExceeded)

        # Determine if task is going to dead letter queue
        dead_letter = is_max_retries or is_soft_timeout or retry_count >= self.max_retries

        # Structured logging for failure
        log_data = {
            "event": "task_failure",
            "task_name": self.name,
            "task_id": task_id,
            "queue_name": queue_name,
            "retry_count": retry_count,
            "max_retries": self.max_retries,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "is_max_retries_exceeded": is_max_retries,
            "is_soft_timeout": is_soft_timeout,
            "dead_letter_queue": dead_letter,
            "args": str(args)[:500],  # Truncate long args
            "kwargs": str(kwargs)[:500],  # Truncate long kwargs
            "traceback": str(einfo)[:2000] if einfo else None,  # Include traceback
        }

        # Log at ERROR level for final failures
        logger.error(
            f"Task {self.name} [{task_id}] FAILED after {retry_count} retries "
            f"in queue '{queue_name}' due to {type(exc).__name__}: {exc}"
            f"{' - Sending to dead letter queue' if dead_letter else ''}",
            extra={"structured_log": log_data},
            exc_info=True,
        )

        # If going to dead letter queue, log additional information for monitoring
        if dead_letter:
            logger.critical(
                f"DEAD LETTER QUEUE: Task {self.name} [{task_id}] from queue '{queue_name}' "
                f"exceeded maximum retries or timed out. Manual intervention may be required.",
                extra={
                    "alert": True,  # Flag for alerting systems
                    "dead_letter_details": {
                        "task_name": self.name,
                        "task_id": task_id,
                        "queue_name": queue_name,
                        "failure_reason": "max_retries"
                        if is_max_retries
                        else "timeout"
                        if is_soft_timeout
                        else "unknown",
                    },
                },
            )

        # Durable dead-letter sink (RH-07 / REQ-CEL-2): persist the give-up
        # payload so it can be inspected and redriven. Celery calls on_failure
        # ONLY on the final give-up path (a retry goes through on_retry), so every
        # on_failure is a give-up — persist unconditionally. The previous
        # behaviour logged-then-acked-and-dropped, losing the payload entirely.
        self._persist_dead_letter(exc, task_id, args, kwargs)

        # Call parent implementation
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def _persist_dead_letter(self, exc, task_id, args, kwargs) -> None:
        """Persist a final-failure payload to the durable ``failed_tasks`` sink.

        Stores a bounded record of ``{task_id, task_name, args, kwargs, last
        exception}`` (the timestamp is the row's ``created_at`` default). If the
        persistence itself fails the worker must NOT crash on the failure path
        (RH-07 key consideration: "store unavailable") — we log loudly and let
        the ORIGINAL exception propagate via ``super().on_failure``.
        """
        try:
            session = SessionLocal()
            try:
                record = FailedTaskModel(
                    task_id=task_id,
                    task_name=self.name,
                    args=_bounded(args),
                    kwargs=_bounded(kwargs),
                    exception=_bounded(f"{type(exc).__name__}: {exc}"),
                )
                session.add(record)
                session.commit()
            finally:
                session.close()
        except Exception:
            # Never let a dead-letter write failure mask or replace the original
            # exception. Log loudly and swallow — the original failure is already
            # being propagated by the caller (super().on_failure).
            logger.exception(
                "Failed to persist dead-letter record for task %s [%s]; the "
                "original task failure still propagates.",
                self.name,
                task_id,
            )

    def on_success(self, retval, task_id, args, kwargs):
        """
        Called when a task succeeds.

        Logs successful completion with retry information if task was retried.
        """
        retry_count = self.request.retries if hasattr(self, "request") else 0
        queue_name = (
            self.request.queue
            if hasattr(self, "request") and hasattr(self.request, "queue")
            else "unknown"
        )

        if retry_count > 0:
            # Log success after retries
            log_data = {
                "event": "task_success_after_retry",
                "task_name": self.name,
                "task_id": task_id,
                "queue_name": queue_name,
                "retry_count": retry_count,
                "result_preview": str(retval)[:200] if retval else None,
            }

            logger.info(
                f"Task {self.name} [{task_id}] succeeded after {retry_count} retries in queue '{queue_name}'",
                extra={"structured_log": log_data},
            )

        # Call parent implementation
        super().on_success(retval, task_id, args, kwargs)

    def apply_async(self, args=None, kwargs=None, **options):
        """
        Override apply_async to log task submission.
        """
        queue_name = options.get("queue", "default")

        # Log task submission
        logger.debug(
            f"Submitting task {self.name} to queue '{queue_name}'",
            extra={
                "structured_log": {
                    "event": "task_submitted",
                    "task_name": self.name,
                    "queue_name": queue_name,
                    "args_preview": str(args)[:200] if args else None,
                    "kwargs_preview": str(kwargs)[:200] if kwargs else None,
                }
            },
        )

        # Call parent implementation
        return super().apply_async(args=args, kwargs=kwargs, **options)


def _literal_or_empty(text: str | None, empty):
    """Reconstruct args/kwargs stored as a bounded ``repr`` for redrive.

    The dead-letter row stores ``repr(args)`` / ``repr(kwargs)``; for the common
    case (plain literals such as ``(42,)`` or ``{'force': True}``) this round-trips
    via ``ast.literal_eval``. A truncated or non-literal payload (e.g. an object
    repr) cannot be reconstructed safely, so redrive falls back to ``empty`` and
    the operator re-supplies arguments — never executing arbitrary code.
    """
    import ast

    if not text:
        return empty
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return empty


def redrive(task_id: str):
    """Re-submit a previously dead-lettered task by its stored ``task_id``.

    Looks up the most recent ``failed_tasks`` row for ``task_id`` and re-submits
    the named task with its reconstructed args/kwargs (RH-07 / REQ-CEL-2 — a real
    dead-letter sink must be redrivable). Returns the new ``AsyncResult``, or
    ``None`` if no record exists or the task is not registered.
    """
    # Imported lazily to avoid importing the Celery app at module load time.
    from app.core.celery_app import celery_app

    session = SessionLocal()
    try:
        record = (
            session.query(FailedTaskModel)
            .filter(FailedTaskModel.task_id == task_id)
            .order_by(FailedTaskModel.id.desc())
            .first()
        )
    finally:
        session.close()

    if record is None:
        logger.warning("redrive: no dead-letter record found for task_id=%s", task_id)
        return None

    task = celery_app.tasks.get(record.task_name)
    if task is None:
        logger.error(
            "redrive: task %s is not registered; cannot redrive task_id=%s",
            record.task_name,
            task_id,
        )
        return None

    args = _literal_or_empty(record.args, ())
    kwargs = _literal_or_empty(record.kwargs, {})
    logger.info("redrive: re-submitting task %s (original task_id=%s)", record.task_name, task_id)
    return task.apply_async(args=args, kwargs=kwargs)
