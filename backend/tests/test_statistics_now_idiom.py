"""REQ-SH-NOW: one canonical 'now' idiom across the statistics subsystem.

Discovery F-B: a canonical naive-UTC factory ``utc_now()`` already existed yet had
zero callers, while the subsystem stamped "now" four incompatible ways — a
byte-identical duplicate ``base._utc_now``, ``datetime.utcnow`` (deprecated),
``datetime.now(UTC)`` (aware), and naive-local ``datetime.now()``.

This pins the convergence by inspection of the subsystem source (the static-grep
seam the PRD names for REQ-SH-NOW-2/3) and by the ORM column defaults
(REQ-SH-NOW-1):

* NOW-1 — every current-time value comes from the canonical helper.
* NOW-2 — no direct ``datetime.utcnow`` / ``datetime.now`` / ``func.now`` call site.
* NOW-3 — exactly one now helper definition; no duplicate.

NOW-4 (one serialization convention) is verified at the API-contract seam in
``tests/services/test_statistics_serialization.py``.
"""

import ast
from pathlib import Path

import pytest

from app.core.utils import utc_now

# Repo-root-relative subsystem source files (the statistics-collection subsystem).
_BACKEND = Path(__file__).resolve().parents[1]

# The canonical helper module legitimately wraps ``datetime.now`` — it IS the one
# allowed call. Every OTHER subsystem file must route through ``utc_now`` instead.
_HELPER_MODULE = "app/core/timeutils.py"

_CALL_SITE_FILES = [
    "app/core/utils.py",
    "app/models/base.py",
    "app/models/archive_snapshot.py",
    "app/repositories/snapshot_repository.py",
    "app/services/snapshot_service.py",
    "app/utils/refresh_statistics.py",
    "app/tasks/snapshot_tasks.py",
    "app/core/celery_app.py",
    "app/schemas/statistics.py",
    "app/api/v1/endpoints/snapshots.py",
]


def _naive_now_idioms(path: Path) -> list[str]:
    """Return 'lineno: datetime.<attr>'/'func.now' references in *path*.

    Uses the AST so a prose mention in a docstring (e.g. "replaces the deprecated
    datetime.utcnow()") is never a false positive — only real attribute access on
    the ``datetime`` / ``func`` names counts. Catches both the called form
    ``datetime.utcnow()`` and the bare-callable form ``default=datetime.utcnow``.
    """
    tree = ast.parse(path.read_text())
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Name):
            continue
        base, attr = node.value.id, node.attr
        if (base == "datetime" and attr in {"utcnow", "now"}) or (base == "func" and attr == "now"):
            hits.append(f"{node.lineno}: {base}.{attr}")
    return hits


@pytest.mark.parametrize("rel", _CALL_SITE_FILES)
def test_no_naive_now_call_site_in_subsystem(rel):
    """REQ-SH-NOW-2: no statistics call site uses datetime.utcnow / datetime.now /
    func.now directly — they route through the canonical utc_now helper."""
    hits = _naive_now_idioms(_BACKEND / rel)
    assert not hits, f"{rel} still uses a non-canonical now idiom: {hits}"


def test_exactly_one_now_helper_definition():
    """REQ-SH-NOW-3: the canonical now helper is defined exactly once across the
    subsystem, and no byte-identical duplicate (the retired base._utc_now) remains."""
    all_files = [*_CALL_SITE_FILES, _HELPER_MODULE]
    utc_now_defs, underscore_defs = [], []
    for rel in all_files:
        path = _BACKEND / rel
        if not path.exists():
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.FunctionDef):
                if node.name == "utc_now":
                    utc_now_defs.append(rel)
                if node.name == "_utc_now":
                    underscore_defs.append(rel)
    assert utc_now_defs == [_HELPER_MODULE], f"utc_now defined at {utc_now_defs}, expected one leaf"
    assert underscore_defs == [], (
        f"duplicate now helper _utc_now still defined at {underscore_defs}"
    )


def test_canonical_helper_returns_naive_utc():
    """REQ-SH-NOW-1/4 basis: the canonical helper returns a timezone-naive datetime
    (naive-UTC is the serialization convention, Q2)."""
    now = utc_now()
    assert now.tzinfo is None


def _is_canonical_now(callable_) -> bool:
    """The column-default callable is THE canonical helper: same source definition
    (module + name) and same naive-UTC behaviour.

    SQLAlchemy wraps a zero-arg default in a context-accepting shim (functools.wraps
    copies the name/module and exposes the original via ``__wrapped__``), so unwrap
    first. Object identity (``is utc_now``) is deliberately not used — a column
    default is captured at class-definition time and the app's import graph can
    leave it bound to a different live object of the *same*
    ``app.core.timeutils.utc_now`` definition; that churn is irrelevant to the
    obligation, which is that the default comes from the one canonical helper.
    """
    fn = getattr(callable_, "__wrapped__", callable_)
    return (
        fn.__module__ == "app.core.timeutils" and fn.__name__ == "utc_now" and fn().tzinfo is None
    )


def test_archive_snapshot_recorded_at_defaults_to_canonical_now():
    """REQ-SH-NOW-1: the append-only snapshot's recorded_at default is the canonical
    utc_now (not the deprecated datetime.utcnow callable)."""
    from app.models.archive_snapshot import ArchiveSnapshotModel

    default = ArchiveSnapshotModel.__table__.c.recorded_at.default
    assert default is not None and _is_canonical_now(default.arg)


def test_timestamp_mixin_defaults_to_canonical_now():
    """REQ-SH-NOW-1/3: TimestampMixin (created_at drives the registration timeline)
    seeds created_at/updated_at from the canonical utc_now, not a local duplicate."""
    from app.models.base import TimestampMixin

    assert _is_canonical_now(TimestampMixin.created_at.default.arg)
    assert _is_canonical_now(TimestampMixin.updated_at.default.arg)
    assert _is_canonical_now(TimestampMixin.updated_at.onupdate.arg)
