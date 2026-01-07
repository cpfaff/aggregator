# Import all task modules to ensure they are registered with Celery
from . import snapshot_tasks
from . import validator_tasks