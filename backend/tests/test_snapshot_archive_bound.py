"""The streamed archive download must be bounded by a byte budget (RH-04).

``parse_archive_xml`` streams a provider archive into a
``SpooledTemporaryFile(max_size=10 MiB)`` and then parses the whole buffer.
``max_size`` is a *memory→disk rollover* threshold, **not** a cap: a huge or
hostile archive is streamed in full, exhausting the stats worker's disk/memory
(REQ-OUT-1 / F-SNAP-01).

The fix introduces ``settings.MAX_ARCHIVE_BYTES`` and, in the ``iter_content``
loop, a running ``written`` counter that raises ``XMLParsingError`` once the
budget is exceeded — authoritative, because ``Content-Length`` may be absent or
lie. These tests pin that bound behaviourally:

* ``test_oversized_archive_stream_aborts`` — a streamed response with **no**
  ``Content-Length`` yielding well-formed single-root XML chunks totalling more
  than the (test-lowered) budget must abort: total bytes written stays at/under
  the cap **and** ``XMLParsingError`` is raised. Single-root well-formed XML is
  used deliberately so the *only* abort cause is the byte cap — a multi-root
  padding would raise ``ParseError`` for the wrong reason (tautological).
* ``test_normal_archive_parses`` — a small, well-formed archive under the budget
  still parses to the correct unit count (the guard is not over-eager).

House idiom: monkeypatch ``snapshot_tasks.requests.get`` with a fake streaming
response and lower ``snapshot_tasks.settings.MAX_ARCHIVE_BYTES`` so the test is
fast and free of per-byte tuning against the 200 MiB production default.
"""

import tempfile

import pytest

from app.tasks import snapshot_tasks
from app.tasks.snapshot_tasks import XMLParsingError, parse_archive_xml


class _FakeStreamingResponse:
    """A minimal stand-in for a streamed ``requests`` response.

    Yields the given byte chunks from ``iter_content`` and exposes an empty
    headers mapping by default (no ``Content-Length``) so the byte counter — not
    the header early-out — is what enforces the cap.
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


def test_oversized_archive_stream_aborts(monkeypatch):
    """An oversized streamed body (no Content-Length) aborts at the byte cap.

    The chunks form one well-formed ``<root>…</root>`` document whose total size
    exceeds the lowered budget, so the abort can only come from the byte counter,
    never from an XML parse error. We spy on every byte handed to the spooled
    temp file and assert the total never exceeds the cap, and that
    ``XMLParsingError`` is raised.
    """
    cap = 64 * 1024
    monkeypatch.setattr(snapshot_tasks.settings, "MAX_ARCHIVE_BYTES", cap, raising=False)

    # One well-formed single-root XML document, padded with a comment far beyond
    # the cap. Split into chunks so the running counter trips mid-stream.
    padding = b"<!--" + b"x" * (cap * 4) + b"-->"
    payload = b"<root>" + padding + b"<Unit/></root>"
    chunks = [payload[i : i + 8192] for i in range(0, len(payload), 8192)]
    assert len(payload) > cap  # the body genuinely exceeds the budget

    monkeypatch.setattr(
        snapshot_tasks.requests,
        "get",
        lambda *a, **k: _FakeStreamingResponse(chunks),
    )

    written_total = 0
    real_write = tempfile.SpooledTemporaryFile.write

    def _spy_write(self, b):
        nonlocal written_total
        written_total += len(b)
        return real_write(self, b)

    monkeypatch.setattr(tempfile.SpooledTemporaryFile, "write", _spy_write)

    with pytest.raises(XMLParsingError):
        parse_archive_xml("http://provider.example/huge.xml")

    assert written_total <= cap, (
        f"streamed {written_total} bytes past the {cap}-byte cap — the download is unbounded"
    )


def test_normal_archive_parses(monkeypatch):
    """A small, well-formed archive under the budget still parses correctly.

    Proves the cap is not over-eager: a tiny single-root XML with two units
    flows through and returns unit_count == 2.
    """
    cap = 64 * 1024
    monkeypatch.setattr(snapshot_tasks.settings, "MAX_ARCHIVE_BYTES", cap, raising=False)

    payload = (
        b'<?xml version="1.0"?>'
        b'<DataSets xmlns="http://www.tdwg.org/schemas/abcd/2.06">'
        b"<DataSet><Units><Unit/><Unit/></Units></DataSet>"
        b"</DataSets>"
    )
    assert len(payload) < cap

    monkeypatch.setattr(
        snapshot_tasks.requests,
        "get",
        lambda *a, **k: _FakeStreamingResponse([payload]),
    )

    result = parse_archive_xml("http://provider.example/small.xml")
    assert result.unit_count == 2
