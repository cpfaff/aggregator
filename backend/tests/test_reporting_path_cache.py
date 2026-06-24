"""Regression tests for extract_error_components path caching (B31).

extract_error_components cached results keyed solely on error.message but the
cached dict included normalized_path (derived from the per-instance error.path).
Two schema errors with identical message text at different document paths were
therefore reported under the first error's path, corrupting error grouping and
sample_paths.
"""

import abcd_validator.reporting as reporting
from abcd_validator.models import ValidationError, ValidationResult

_MSG = (
    "Element 'code': [facet 'pattern'] The value 'aa' is not accepted by the "
    "pattern '[A-Z]{3}'."
)


def _err(path: str) -> ValidationError:
    return ValidationError(
        message=_MSG,
        error_type="schema",
        severity="error",
        type_name="SCHEMAV_CVC_PATTERN_VALID",
        path=path,
    )


def _result(errors):
    return ValidationResult(
        file_name="f.xml",
        file_size=1,
        schema_valid=False,
        validation_time=0.0,
        errors=errors,
        custom_rule_results=[],
    )


def _clear_caches():
    reporting._error_component_cache.clear()
    reporting._normalized_path_cache.clear()


def test_normalized_path_is_per_instance_not_cached_by_message():
    _clear_caches()
    reporting.extract_error_components(_err("/root/item/code"))
    comps2 = reporting.extract_error_components(_err("/root/box/code"))
    assert comps2["normalized_path"] == "/root/box/code"


def test_distinct_paths_with_same_message_group_separately():
    _clear_caches()
    groups = reporting.aggregate_schema_errors_batch(
        [_result([_err("/root/item/code"), _err("/root/box/code")])]
    )
    assert len(groups) == 2
    all_paths = set()
    for group in groups.values():
        all_paths |= group["paths"]
    assert all_paths == {"/root/item/code", "/root/box/code"}


def test_indexed_paths_still_collapse_to_one_group():
    _clear_caches()
    groups = reporting.aggregate_schema_errors_batch(
        [_result([_err("/root/item[1]/code"), _err("/root/item[2]/code")])]
    )
    assert len(groups) == 1
    paths = next(iter(groups.values()))["paths"]
    assert paths == {"/root/item[*]/code"}
