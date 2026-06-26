"""Pure-unit tests for the validation-stats summary projection.

``summarize_validation_results`` is the single place that flattens a stored
``ValidationJob.results`` JSONB blob into the small set of headline numbers the
public validation-stats endpoint exposes to the search UI. It is a pure function
(no DB, no I/O) so every branch — missing blob, missing ``summary``, missing
``data_quality``, partial file counts — is covered here without testcontainers.

The full per-rule defect report is deliberately NOT surfaced (it stays behind the
authenticated DPM endpoints, per the B12 provider-scope decision); only aggregate
quality numbers leak to public search.
"""

from app.services.validation_service import summarize_validation_results

# A representative completed-validation results blob, shaped like
# validator/src/abcd_validator/reporting.py emits (summary + data_quality).
_RESULTS = {
    "summary": {
        "total_files": 12,
        "valid_files": 11,
        "data_quality": {
            "total_weighted_quality": 0.86,
            "mandatory": {"valid_percentage": 95.0},
            "recommended": {"valid_percentage": 70.0},
        },
    }
}

_EMPTY_SUMMARY = {
    "is_valid": None,
    "quality_score": None,
    "mandatory_percentage": None,
    "recommended_percentage": None,
    "total_files": None,
    "valid_files": None,
}


def test_summary_is_none_safe_for_missing_results():
    assert summarize_validation_results(None) == _EMPTY_SUMMARY


def test_summary_is_none_safe_for_empty_dict():
    assert summarize_validation_results({}) == _EMPTY_SUMMARY


def test_summary_extracts_all_headline_numbers():
    out = summarize_validation_results(_RESULTS)
    assert out["total_files"] == 12
    assert out["valid_files"] == 11
    assert out["quality_score"] == 0.86
    assert out["mandatory_percentage"] == 95.0
    assert out["recommended_percentage"] == 70.0


def test_is_valid_true_when_all_files_valid():
    results = {"summary": {"total_files": 5, "valid_files": 5}}
    assert summarize_validation_results(results)["is_valid"] is True


def test_is_valid_false_when_some_files_invalid():
    results = {"summary": {"total_files": 5, "valid_files": 4}}
    assert summarize_validation_results(results)["is_valid"] is False


def test_is_valid_none_when_counts_partial():
    # A present total but a missing valid count is an honest unknown, not False.
    results = {"summary": {"total_files": 5}}
    assert summarize_validation_results(results)["is_valid"] is None


def test_quality_fields_none_when_data_quality_absent():
    # File counts can be present while data_quality is not yet computed.
    results = {"summary": {"total_files": 3, "valid_files": 3}}
    out = summarize_validation_results(results)
    assert out["quality_score"] is None
    assert out["mandatory_percentage"] is None
    assert out["recommended_percentage"] is None
    assert out["total_files"] == 3
