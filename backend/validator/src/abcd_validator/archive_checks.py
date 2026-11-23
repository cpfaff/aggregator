"""Archive-wide checks that need to see every file of an ABCD archive."""

import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lxml import etree

_WHITESPACE = re.compile(r"\s+")


@dataclass
class DuplicateUnitIdReport:
    """Result of the archive-wide UnitID duplicate count."""

    total_units: int = 0
    units_without_unit_id: int = 0
    distinct_unit_ids: int = 0
    duplicated_unit_ids: int = 0
    units_not_indexable: int = 0
    examples: list[dict[str, Any]] = field(default_factory=list)


def find_duplicate_unit_ids(
    archive_path: str | Path, max_examples: int = 20
) -> DuplicateUnitIdReport:
    """Count units sharing a UnitID across all XML members of a ZIP archive.

    Members are parsed as a stream and every processed ``Unit`` is cleared, so
    memory is bounded by the number of distinct UnitIDs. The key is the UnitID
    text with whitespace runs collapsed to one space (not stripped).
    """
    counts: Counter[str] = Counter()
    total_units = 0
    without_unit_id = 0

    with zipfile.ZipFile(archive_path) as archive:
        names = sorted(n for n in archive.namelist() if n.lower().endswith(".xml"))
        for name in names:
            with archive.open(name) as member:
                for _, unit in etree.iterparse(member, events=("end",), tag="{*}Unit"):
                    total_units += 1
                    unit_id = unit.find("{*}UnitID")
                    text = unit_id.text if unit_id is not None else None
                    if text and text.strip():
                        counts[_WHITESPACE.sub(" ", text)] += 1
                    else:
                        without_unit_id += 1
                    unit.clear()
                    while unit.getprevious() is not None:
                        del unit.getparent()[0]

    duplicates = [(uid, n) for uid, n in counts.items() if n > 1]
    duplicates.sort(key=lambda item: (-item[1], item[0]))
    with_unit_id = total_units - without_unit_id
    return DuplicateUnitIdReport(
        total_units=total_units,
        units_without_unit_id=without_unit_id,
        distinct_unit_ids=len(counts),
        duplicated_unit_ids=len(duplicates),
        units_not_indexable=with_unit_id - len(counts),
        examples=[{"unit_id": uid, "units": n} for uid, n in duplicates[:max_examples]],
    )
