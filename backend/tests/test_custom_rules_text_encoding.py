"""Regression tests for CustomRuleValidator._validate_text_encoding (B29).

The 'windows_quotes' / 'windows_apostrophe' entries were meant to detect
Windows smart quotes but held plain ASCII " and ', so ordinary text like
O'Brien or 5'10" was flagged 'problematic' (and escalated to a hard failure),
while real smart quotes were never detected.
"""

from abcd_validator.custom_rules import CustomRuleValidator


def _validator() -> CustomRuleValidator:
    # __init__ requires a rules file; _validate_text_encoding uses no instance
    # state, so bypass __init__.
    return CustomRuleValidator.__new__(CustomRuleValidator)


def test_ascii_apostrophe_is_not_flagged():
    assert _validator()._validate_text_encoding("O'Brien", {}) == []


def test_ascii_double_quote_is_not_flagged():
    assert _validator()._validate_text_encoding('say "hi"', {}) == []


def test_real_smart_double_quotes_are_flagged():
    errors = _validator()._validate_text_encoding("curly “quote”", {})
    assert any("windows_quotes" in e["message"] for e in errors)


def test_real_smart_apostrophe_is_flagged():
    errors = _validator()._validate_text_encoding("O’Brien", {})
    assert any("windows_apostrophe" in e["message"] for e in errors)
