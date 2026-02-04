"""
Custom Celery task base class with enhanced error logging and retry handling.
"""

import json
import logging
from typing import Any, Dict, Optional

from celery import Task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded

logger = logging.getLogger(__name__)


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
        retry_count = self.request.retries if hasattr(self, 'request') else 0
        queue_name = self.request.queue if hasattr(self, 'request') and hasattr(self.request, 'queue') else 'unknown'
        
        # Structured logging for retry
        log_data = {
            'event': 'task_retry',
            'task_name': self.name,
            'task_id': task_id,
            'queue_name': queue_name,
            'retry_count': retry_count,
            'max_retries': self.max_retries,
            'error_type': type(exc).__name__,
            'error_message': str(exc),
            'args': str(args)[:500],  # Truncate long args
            'kwargs': str(kwargs)[:500],  # Truncate long kwargs
        }
        
        logger.warning(
            f"Task {self.name} [{task_id}] retrying (attempt {retry_count + 1}/{self.max_retries + 1}) "
            f"in queue '{queue_name}' due to {type(exc).__name__}: {exc}",
            extra={'structured_log': log_data}
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
        retry_count = self.request.retries if hasattr(self, 'request') else 0
        queue_name = self.request.queue if hasattr(self, 'request') and hasattr(self.request, 'queue') else 'unknown'
        
        # Check if this is a max retries exceeded error
        is_max_retries = isinstance(exc, MaxRetriesExceededError)
        is_soft_timeout = isinstance(exc, SoftTimeLimitExceeded)
        
        # Determine if task is going to dead letter queue
        dead_letter = is_max_retries or is_soft_timeout or retry_count >= self.max_retries
        
        # Structured logging for failure
        log_data = {
            'event': 'task_failure',
            'task_name': self.name,
            'task_id': task_id,
            'queue_name': queue_name,
            'retry_count': retry_count,
            'max_retries': self.max_retries,
            'error_type': type(exc).__name__,
            'error_message': str(exc),
            'is_max_retries_exceeded': is_max_retries,
            'is_soft_timeout': is_soft_timeout,
            'dead_letter_queue': dead_letter,
            'args': str(args)[:500],  # Truncate long args
            'kwargs': str(kwargs)[:500],  # Truncate long kwargs
            'traceback': str(einfo)[:2000] if einfo else None,  # Include traceback
        }
        
        # Log at ERROR level for final failures
        logger.error(
            f"Task {self.name} [{task_id}] FAILED after {retry_count} retries "
            f"in queue '{queue_name}' due to {type(exc).__name__}: {exc}"
            f"{' - Sending to dead letter queue' if dead_letter else ''}",
            extra={'structured_log': log_data},
            exc_info=True
        )
        
        # If going to dead letter queue, log additional information for monitoring
        if dead_letter:
            logger.critical(
                f"DEAD LETTER QUEUE: Task {self.name} [{task_id}] from queue '{queue_name}' "
                f"exceeded maximum retries or timed out. Manual intervention may be required.",
                extra={
                    'alert': True,  # Flag for alerting systems
                    'dead_letter_details': {
                        'task_name': self.name,
                        'task_id': task_id,
                        'queue_name': queue_name,
                        'failure_reason': 'max_retries' if is_max_retries else 'timeout' if is_soft_timeout else 'unknown',
                    }
                }
            )
        
        # Call parent implementation
        super().on_failure(exc, task_id, args, kwargs, einfo)
    
    def on_success(self, retval, task_id, args, kwargs):
        """
        Called when a task succeeds.
        
        Logs successful completion with retry information if task was retried.
        """
        retry_count = self.request.retries if hasattr(self, 'request') else 0
        queue_name = self.request.queue if hasattr(self, 'request') and hasattr(self.request, 'queue') else 'unknown'
        
        if retry_count > 0:
            # Log success after retries
            log_data = {
                'event': 'task_success_after_retry',
                'task_name': self.name,
                'task_id': task_id,
                'queue_name': queue_name,
                'retry_count': retry_count,
                'result_preview': str(retval)[:200] if retval else None,
            }
            
            logger.info(
                f"Task {self.name} [{task_id}] succeeded after {retry_count} retries in queue '{queue_name}'",
                extra={'structured_log': log_data}
            )
        
        # Call parent implementation
        super().on_success(retval, task_id, args, kwargs)
    
    def apply_async(self, args=None, kwargs=None, **options):
        """
        Override apply_async to log task submission.
        """
        queue_name = options.get('queue', 'default')
        
        # Log task submission
        logger.debug(
            f"Submitting task {self.name} to queue '{queue_name}'",
            extra={
                'structured_log': {
                    'event': 'task_submitted',
                    'task_name': self.name,
                    'queue_name': queue_name,
                    'args_preview': str(args)[:200] if args else None,
                    'kwargs_preview': str(kwargs)[:200] if kwargs else None,
                }
            }
        )
        
        # Call parent implementation
        return super().apply_async(args=args, kwargs=kwargs, **options)