"""Regression tests for compute_data_quality weighting (B30).

The 70/30 mandatory/recommended weighting must be renormalized when one category
has no rules, otherwise the absent category's weight is treated as a 0% score:
a perfectly-passing only-mandatory ruleset wrongly caps at 70, only-recommended
at 30.
"""

from abcd_validator.reporting import compute_data_quality


def test_only_mandatory_all_valid_scores_100():
    q = compute_data_quality(
        {"mandatory": [{"valid": True}, {"valid": True}], "recommended": [], "optional": []}
    )
    assert q["total_weighted_quality"] == 100.0


def test_only_recommended_all_valid_scores_100():
    q = compute_data_quality(
        {"mandatory": [], "recommended": [{"valid": True}], "optional": []}
    )
    assert q["total_weighted_quality"] == 100.0


def test_both_categories_present_preserves_70_30_weighting():
    q = compute_data_quality(
        {"mandatory": [{"valid": True}], "recommended": [{"valid": False}]}
    )
    assert q["total_weighted_quality"] == 70.0


def test_no_rules_at_all_scores_zero():
    q = compute_data_quality({"mandatory": [], "recommended": [], "optional": []})
    assert q["total_weighted_quality"] == 0.0
