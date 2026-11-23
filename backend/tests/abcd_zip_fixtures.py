"""Helpers for building small ABCD archives in tests."""

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ABCD_206 = "http://www.tdwg.org/schemas/abcd/2.06"


def _abcd_document(unit_ids: list[str | None], namespace: str) -> str:
    units = []
    for unit_id in unit_ids:
        if unit_id is None:
            units.append("<Unit><SourceID>X</SourceID></Unit>")
        else:
            units.append(f"<Unit><UnitID>{escape(unit_id)}</UnitID></Unit>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<DataSets xmlns="{namespace}"><DataSet><Units>'
        + "".join(units)
        + "</Units></DataSet></DataSets>"
    )


def build_abcd_zip(
    path: Path,
    files: dict[str, list[str | None]],
    namespace: str = ABCD_206,
) -> Path:
    """Write a ZIP at ``path``; ``.xml`` members become ABCD documents."""
    with zipfile.ZipFile(path, "w") as archive:
        for name, unit_ids in files.items():
            if name.lower().endswith(".xml"):
                archive.writestr(name, _abcd_document(unit_ids, namespace))
            else:
                archive.writestr(name, "placeholder\n")
    return path
