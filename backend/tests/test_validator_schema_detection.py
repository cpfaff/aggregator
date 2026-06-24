"""Regression tests for ABCD schema auto-detection (B33).

_detect_schema_version only matched namespaces containing 'tdwg.org/schemas/abcd'
(the www form). The valid 'http://rs.tdwg.org/abcd/<ver>' forms — explicitly
listed in SCHEMA_MAPPING — were never detected, so schema_path stayed None and
XSD validation was silently skipped (file wrongly reported schema_valid=True).
"""

import abcd_validator.core as core
from lxml import etree


def _detect(namespace: str):
    validator = core.ABCDValidator.__new__(core.ABCDValidator)
    tree = etree.ElementTree(etree.fromstring(f'<DataSets xmlns="{namespace}"/>'.encode()))
    return validator._detect_schema_version(tree)


def test_detects_www_schemas_namespace():
    assert _detect("http://www.tdwg.org/schemas/abcd/2.06") == "abcd2.06.xsd"


def test_detects_rs_tdwg_namespace():
    assert _detect("http://rs.tdwg.org/abcd/2.06") == "abcd2.06.xsd"


def test_detects_rs_tdwg_xsd_namespace():
    assert _detect("http://rs.tdwg.org/abcd/2.06/ABCD_2.06.xsd") == "abcd2.06.xsd"


def test_unknown_namespace_returns_none():
    assert _detect("http://example.com/not-abcd") is None
