"""REQ-SH-LANG: the statistics subsystem names its two timeline kinds canonically.

Discovery F-A found two semantically distinct "timeline" notions that shared no
vocabulary and were therefore easy to conflate:

* the **collection timeline** — the as-of unit-count series, forward-filled over
  ``ArchiveSnapshot.recorded_at`` (the collected-at instant); and
* the **registration timeline** — the cumulative entity-count series keyed on
  ``created_at`` (entity registration).

This locks the canonical names from the PRD *Ubiquitous Language* into the
subsystem source so the two cannot silently re-merge. The PRD names the lowest
seam for these terminology obligations as ``inspection (glossary grep)``; these
tests are that grep, run over the actual module source / docstrings.

* REQ-SH-LANG-1 — name the as-of unit-count series the "collection timeline".
* REQ-SH-LANG-2 — name the cumulative entity-count series the "registration timeline".
* REQ-SH-LANG-3 (SHOULD) — a symbol that denotes a timeline indicates its kind.
"""

import inspect

from app.repositories import snapshot_repository
from app.services import snapshot_service

_SERVICE_SRC = inspect.getsource(snapshot_service).lower()
_REPO_SRC = inspect.getsource(snapshot_repository).lower()


def test_collection_timeline_term_present():
    """REQ-SH-LANG-1: the canonical term 'collection timeline' is established."""
    assert "collection timeline" in _SERVICE_SRC


def test_registration_timeline_term_present():
    """REQ-SH-LANG-2: the canonical term 'registration timeline' is established."""
    assert "registration timeline" in _SERVICE_SRC


def test_glossary_defines_both_timeline_kinds_together():
    """A single glossary names both kinds so the distinction is discoverable in
    one place (the root cause of F-A was that nothing named the unifying concept)."""
    assert "collection timeline" in _SERVICE_SRC
    assert "registration timeline" in _SERVICE_SRC


def test_as_of_unit_count_method_names_its_kind():
    """REQ-SH-LANG-3: the as-of unit-count series method declares it is the
    *collection* timeline (keyed on recorded_at), not a registration timeline."""
    doc = (snapshot_service.SnapshotService.get_biological_units_timeline.__doc__ or "").lower()
    assert "collection timeline" in doc


def test_cumulative_entity_count_method_names_its_kind():
    """REQ-SH-LANG-3: the cumulative entity-count series method declares it is the
    *registration* timeline (keyed on created_at), not a collection timeline."""
    doc = (snapshot_service.SnapshotService.get_growth_metrics.__doc__ or "").lower()
    assert "registration timeline" in doc


def test_repository_entity_timeline_names_registration_kind():
    """REQ-SH-LANG-3: the repository entity-timeline primitive (created_at-keyed)
    declares it serves the registration timeline."""
    doc = (snapshot_repository.SnapshotRepository.get_entity_timeline.__doc__ or "").lower()
    assert "registration timeline" in doc


def test_glossary_marks_loose_synonyms_as_retired():
    """REQ-SH-LANG-1: the glossary records the loose synonyms it retires (e.g.
    'as-of timeline') so a future reader knows not to reintroduce them as labels.

    The discovery cause of F-A was that the as-of series had several loose names
    and nothing said which was canonical; the glossary fixes that by naming the
    canonical term and explicitly listing the retired ones.
    """
    assert "retired synonyms" in _SERVICE_SRC
    assert "as-of timeline" in _SERVICE_SRC  # listed, as a retired synonym
