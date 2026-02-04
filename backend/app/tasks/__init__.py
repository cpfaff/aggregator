# Import all task modules to ensure they are registered with Celery
from . import snapshot_tasks, validator_tasks
