"""REQ-SH-DEAD-1/2: no dead Celery route; no always-null field shown as live.

Discovery F-F: a stale ``statistics.*`` route glob matched no registered task (the
real tasks live under the ``snapshots.`` namespace and are pinned at the decorator).
Discovery F-E: ``abcd_compliance_rate`` (quality) and ``activity_score`` (provider)
are hardcoded ``None`` yet advertised as live metrics.

* DEAD-1 — the Celery routing config contains no route pattern matching no task.
* DEAD-2 — the always-null fields are not presented as live metrics. Per Q3
  (deprecate-in-place, to keep the public response shape stable) they remain in the
  schema but are marked ``deprecated`` so consumers are told not to rely on them.
"""

import fnmatch

import app.tasks.snapshot_tasks  # noqa: F401  (register snapshots.* tasks)
import app.tasks.validator_tasks  # noqa: F401  (register validator.* tasks)
from app.core.celery_app import celery_app


def _registered_task_names() -> list[str]:
    return [name for name in celery_app.tasks.keys() if not name.startswith("celery.")]


# ---------------------------------------------------------------------------
# DEAD-1 — no orphan Celery route
# ---------------------------------------------------------------------------


def test_no_celery_route_pattern_matches_no_task():
    """REQ-SH-DEAD-1: every task_routes pattern matches at least one registered task."""
    registered = _registered_task_names()
    routes = celery_app.conf.task_routes or {}
    orphans = [
        pattern
        for pattern in routes
        if not any(fnmatch.fnmatch(name, pattern) for name in registered)
    ]
    assert not orphans, f"Celery route patterns matching no registered task: {orphans}"


def test_stale_statistics_glob_route_removed():
    """REQ-SH-DEAD-1: the specific stale ``statistics.*`` route (F-F) is gone."""
    routes = celery_app.conf.task_routes or {}
    assert "statistics.*" not in routes


# ---------------------------------------------------------------------------
# DEAD-2 — always-null fields marked deprecated (Q3: kept in shape, not live)
# ---------------------------------------------------------------------------


def _openapi_property(schema_name: str, field: str) -> dict:
    from main import app

    schema = app.openapi()["components"]["schemas"][schema_name]
    return schema["properties"][field]


def test_abcd_compliance_rate_present_but_deprecated():
    """REQ-SH-DEAD-2: abcd_compliance_rate stays in QualityMetrics (shape stable, Q3)
    but is flagged deprecated so it is not presented as a live metric (F-E)."""
    prop = _openapi_property("QualityMetrics", "abcd_compliance_rate")
    assert prop.get("deprecated") is True


def test_activity_score_present_but_deprecated():
    """REQ-SH-DEAD-2: activity_score stays in ProviderStats (shape stable, Q3) but is
    flagged deprecated so it is not presented as a live metric (F-E)."""
    prop = _openapi_property("ProviderStats", "activity_score")
    assert prop.get("deprecated") is True
