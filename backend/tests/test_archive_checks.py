import time

from abcd_validator.archive_checks import find_duplicate_unit_ids

from tests.abcd_zip_fixtures import build_abcd_zip


def test_no_duplicates(tmp_path):
    zip_path = build_abcd_zip(tmp_path / "a.zip", {"r1.xml": ["A", "B", "C"]})
    report = find_duplicate_unit_ids(zip_path)
    assert report.total_units == 3
    assert report.units_not_indexable == 0
    assert report.examples == []


def test_counts_duplicates_across_files(tmp_path):
    zip_path = build_abcd_zip(
        tmp_path / "a.zip",
        {
            "response.00001.xml": ["ZFMK-Ac-00987", "ZFMK-Ac-00712", "ZFMK-Ac-00712"],
            "response.00002.xml": ["ZFMK-Ac-00987", "ZFMK-Ac-00001"],
        },
    )
    report = find_duplicate_unit_ids(zip_path)
    assert report.total_units == 5
    assert report.distinct_unit_ids == 3
    assert report.duplicated_unit_ids == 2
    assert report.units_not_indexable == 2
    assert report.examples == [
        {"unit_id": "ZFMK-Ac-00712", "units": 2},
        {"unit_id": "ZFMK-Ac-00987", "units": 2},
    ]


def test_whitespace_variants_collapse(tmp_path):
    zip_path = build_abcd_zip(tmp_path / "a.zip", {"r1.xml": ["A  1", "A 1", " A1", "A1"]})
    report = find_duplicate_unit_ids(zip_path)
    assert report.distinct_unit_ids == 3
    assert report.duplicated_unit_ids == 1
    assert report.units_not_indexable == 1


def test_missing_unit_id(tmp_path):
    zip_path = build_abcd_zip(tmp_path / "a.zip", {"r1.xml": [None, "", "A"]})
    report = find_duplicate_unit_ids(zip_path)
    assert report.total_units == 3
    assert report.units_without_unit_id == 2
    assert report.distinct_unit_ids == 1
    assert report.units_not_indexable == 0


def test_namespaces_and_non_xml_members(tmp_path):
    first = build_abcd_zip(tmp_path / "one.zip", {"r1.xml": ["A", "B"]})
    second = build_abcd_zip(
        tmp_path / "two.zip",
        {"r2.xml": ["B", "C"], "occurrence.csv": []},
        namespace="http://www.tdwg.org/schemas/abcd/2.1",
    )
    # Merge both into one archive with two namespaces.
    import zipfile

    merged = tmp_path / "merged.zip"
    with zipfile.ZipFile(merged, "w") as out:
        for src in (first, second):
            with zipfile.ZipFile(src) as zin:
                for name in zin.namelist():
                    out.writestr(name, zin.read(name))
    report = find_duplicate_unit_ids(merged)
    assert report.total_units == 4
    assert report.distinct_unit_ids == 3
    assert report.units_not_indexable == 1


def test_max_examples(tmp_path):
    ids = [f"ID-{i:02d}" for i in range(30)]
    zip_path = build_abcd_zip(tmp_path / "a.zip", {"r1.xml": ids + ids})
    report = find_duplicate_unit_ids(zip_path, max_examples=20)
    assert report.duplicated_unit_ids == 30
    assert len(report.examples) == 20


def test_clears_parsed_units(tmp_path):
    ids = [f"U-{i}" for i in range(5000)]
    zip_path = build_abcd_zip(tmp_path / "a.zip", {"r1.xml": ids})
    start = time.monotonic()
    report = find_duplicate_unit_ids(zip_path)
    assert time.monotonic() - start < 10
    assert report.total_units == 5000


def test_whitespace_only_unit_id_is_keyed(tmp_path):
    zip_path = build_abcd_zip(tmp_path / "a.zip", {"r1.xml": ["  ", "\t", "A1"]})
    report = find_duplicate_unit_ids(zip_path)
    assert report.units_without_unit_id == 0
    assert report.distinct_unit_ids == 2
    assert report.units_not_indexable == 1
    assert report.examples == [{"unit_id": " ", "units": 2}]


def test_iterparse_called_with_tag_filter(tmp_path, monkeypatch):
    from abcd_validator import archive_checks

    calls = []
    real = archive_checks.etree.iterparse

    def spy(*args, **kwargs):
        calls.append(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(archive_checks.etree, "iterparse", spy)
    zip_path = build_abcd_zip(tmp_path / "a.zip", {"r1.xml": ["A"]})
    find_duplicate_unit_ids(zip_path)
    assert calls and calls[0]["tag"] == "{*}Unit"
