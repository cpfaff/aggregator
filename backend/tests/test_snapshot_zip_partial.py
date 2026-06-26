"""A ZIP whose entries don't all parse must not report a clean snapshot (RH-10).

``parse_archive_xml`` streams a provider archive and, for a ZIP, iterates its
``.xml`` entries counting biological units. The defect (F-SNAP-04 / REQ-OUT-2):
the per-entry loop caught ``ET.ParseError``, logged, and ``continue``d, then
returned the *partial* ``total_unit_count`` as a successful
``ArchiveParseResult`` — so a half-broken archive was silently reported as a
clean, complete snapshot, exactly the failure the whole-file path already guards
against by raising ``XMLParsingError``.

The fix is **fail-fast**, symmetric with the whole-file path: collect the names
of entries that fail to parse and, if any, ``raise XMLParsingError`` listing
them instead of returning a partial count.

These tests pin that behaviour:

* ``test_zip_with_unparseable_entry_not_clean`` — a two-entry ZIP with a
  well-formed ``good.xml`` (two units) and a cleanly-malformed ``bad.xml``
  (mismatched tag) must **not** return a clean partial count: it raises
  ``XMLParsingError`` (or, if the indicator route were taken, returns a result
  whose incompleteness indicator is truthy). ``good.xml`` is well-formed and
  ``bad.xml`` is malformed only by a mismatched end tag, so the *only* failure
  cause is the per-entry parse error — never a ZIP-structure or wrong-reason
  throw.
* ``test_zip_all_entries_parse_ok`` — a two-entry ZIP whose entries all parse
  still returns the correct summed unit count (the guard is not over-eager).

House idiom (shared with ``test_snapshot_archive_bound``): monkeypatch
``snapshot_tasks.requests.get`` with a fake streaming response that yields the
in-memory ZIP bytes (first bytes ``PK``) so the ZIP branch is taken.
"""

import io
import zipfile

from app.tasks import snapshot_tasks
from app.tasks.snapshot_tasks import (
    ArchiveParseResult,
    XMLParsingError,
    parse_archive_xml,
)


class _FakeStreamingResponse:
    """A minimal stand-in for a streamed ``requests`` response.

    Yields the given byte chunks from ``iter_content`` and exposes an empty
    headers mapping (no ``Content-Length``) so the byte-budget early-out never
    interferes with the ZIP-parsing path under test.
    """

    def __init__(self, chunks, headers=None):
        self._chunks = chunks
        self.headers = headers if headers is not None else {}

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size=8192):
        yield from self._chunks

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _build_zip(entries: dict[str, bytes]) -> bytes:
    """Build an in-memory ZIP (first bytes ``PK``) from name -> content."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    data = buffer.getvalue()
    assert data[:2] == b"PK"  # routes through the ZIP branch of parse_archive_xml
    return data


def test_zip_with_unparseable_entry_not_clean(monkeypatch):
    """A ZIP with one unparseable entry is not reported as a clean snapshot.

    ``good.xml`` parses to two units; ``bad.xml`` has a mismatched end tag and
    fails ``ET.fromstring``. The archive is incomplete, so ``parse_archive_xml``
    must either raise ``XMLParsingError`` or return a result whose incompleteness
    indicator is truthy — never a clean partial count.
    """
    zip_bytes = _build_zip(
        {
            "good.xml": b"<root><Unit/><Unit/></root>",
            "bad.xml": b"<root><Unit></root>",
        }
    )

    monkeypatch.setattr(
        snapshot_tasks.requests,
        "get",
        lambda *a, **k: _FakeStreamingResponse([zip_bytes]),
    )

    try:
        result = parse_archive_xml("http://provider.example/partial.zip")
    except XMLParsingError:
        # Fail-fast stance: an unparseable entry aborts the snapshot. Accepted.
        return

    # Indicator stance (alternative): a result is allowed only if it carries a
    # truthy incompleteness signal — never a silently-clean partial count.
    assert isinstance(result, ArchiveParseResult)
    indicator = (
        getattr(result, "incomplete", None)
        or getattr(result, "parse_errors", None)
        or getattr(result, "failed_entries", None)
    )
    assert indicator, (
        "ZIP with an unparseable entry was reported as a clean snapshot "
        f"(unit_count={result.unit_count}, no incompleteness indicator)"
    )


def test_zip_all_entries_parse_ok(monkeypatch):
    """A ZIP whose entries all parse returns the correct summed unit count.

    Proves the guard is not over-eager: two well-formed entries (2 + 1 units)
    flow through and return unit_count == 3.
    """
    zip_bytes = _build_zip(
        {
            "a.xml": b"<root><Unit/><Unit/></root>",
            "b.xml": b"<root><Unit/></root>",
        }
    )

    monkeypatch.setattr(
        snapshot_tasks.requests,
        "get",
        lambda *a, **k: _FakeStreamingResponse([zip_bytes]),
    )

    result = parse_archive_xml("http://provider.example/clean.zip")
    assert result.unit_count == 3
