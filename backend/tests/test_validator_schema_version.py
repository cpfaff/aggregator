"""Regression tests for the static validation worker path (B28).

``_validate_single_file_static`` builds its validator with
``ABCDValidator.__new__`` (bypassing ``__init__``), so the instance never
gets ``_detected_version``. When the worker has no known schema version
(``WORKER_SCHEMA_VERSION is None`` — the normal state when no schema is
provided/detected), the ``WORKER_SCHEMA_VERSION or validator._detected_version``
fallback used to raise ``AttributeError``, which upstream code masks as a bogus
per-file 'Processing error'. These tests pin the no-crash contract.

Note: ``make test`` imports this ``abcd_validator`` copy via
``PYTHONPATH=validator/src``; the equivalent fix is mirrored into the
deployed ``backend/validator`` copy, which is not covered here.
"""

import abcd_validator.core as core

PLAIN_XML = b'<?xml version="1.0" encoding="UTF-8"?><root><a>1</a></root>'


def test_static_validate_without_schema_version_does_not_crash(monkeypatch):
    """No known schema version must yield schema_version=None, not AttributeError."""
    monkeypatch.setattr(core, "WORKER_SCHEMA", None)
    monkeypatch.setattr(core, "WORKER_SCHEMA_PATH", None)
    monkeypatch.setattr(core, "WORKER_CUSTOM_VALIDATOR", None)
    monkeypatch.setattr(core, "WORKER_SCHEMA_VERSION", None)

    result = core.ABCDValidator._validate_single_file_static(PLAIN_XML, "test.xml", None, None)

    assert result.schema_version is None
    # The crash would have surfaced as a masked 'processing' error.
    assert not any(
        getattr(e, "error_type", None) == "processing"
        and "_detected_version" in getattr(e, "message", "")
        for e in result.errors
    )


def test_static_validate_uses_worker_schema_version_when_known(monkeypatch):
    """When the worker knows the schema version, it is reported through."""
    monkeypatch.setattr(core, "WORKER_SCHEMA", None)
    monkeypatch.setattr(core, "WORKER_SCHEMA_PATH", None)
    monkeypatch.setattr(core, "WORKER_CUSTOM_VALIDATOR", None)
    monkeypatch.setattr(core, "WORKER_SCHEMA_VERSION", "2.06")

    result = core.ABCDValidator._validate_single_file_static(PLAIN_XML, "test.xml", None, None)

    assert result.schema_version == "2.06"
