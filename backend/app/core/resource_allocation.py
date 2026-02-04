"""Dynamic resource allocation module for Celery workers."""

import logging
import multiprocessing

logger = logging.getLogger(__name__)


def get_validator_cpu_count(cpu_percent: int = 75) -> int:
    """
    Calculate CPU count for validator worker based on percentage.

    Args:
        cpu_percent: Percentage of CPUs to allocate (1-100), default 75%

    Returns:
        Number of CPUs to allocate, minimum 1
    """
    if not 1 <= cpu_percent <= 100:
        logger.warning(f"Invalid CPU percentage {cpu_percent}, using default 75%")
        cpu_percent = 75

    total_cpus = multiprocessing.cpu_count()
    calculated_cpus = int(total_cpus * cpu_percent / 100)
    validator_cpus = max(1, calculated_cpus)

    logger.info(
        f"Validator CPU allocation: {validator_cpus} CPUs "
        f"({cpu_percent}% of {total_cpus} total CPUs)"
    )

    return validator_cpus


def get_stats_worker_concurrency(
    concurrency_setting: str | int, validator_cpus: int = None
) -> int:
    """
    Calculate concurrency for statistics worker.

    Args:
        concurrency_setting: Either 'auto' or explicit integer value
        validator_cpus: Number of CPUs allocated to validator (for auto mode)

    Returns:
        Worker concurrency value, minimum 2
    """
    if isinstance(concurrency_setting, int):
        if concurrency_setting < 2:
            logger.warning(f"Stats concurrency {concurrency_setting} below minimum, using 2")
            return 2
        logger.info(f"Stats worker concurrency: {concurrency_setting} (explicit)")
        return concurrency_setting

    if concurrency_setting == "auto":
        total_cpus = multiprocessing.cpu_count()

        if validator_cpus is None:
            validator_cpus = get_validator_cpu_count()

        remaining_cpus = total_cpus - validator_cpus
        stats_concurrency = max(2, remaining_cpus)

        logger.info(
            f"Stats worker concurrency: {stats_concurrency} "
            f"(auto - {total_cpus} total, {validator_cpus} for validator)"
        )

        return stats_concurrency

    logger.warning(f"Invalid concurrency setting '{concurrency_setting}', using auto mode")
    return get_stats_worker_concurrency("auto", validator_cpus)
