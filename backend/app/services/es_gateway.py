"""EsGateway — the thin httpx-backed Elasticsearch test seam.

This module is the **single owner** of every Elasticsearch wire-detail for the
harvest-success indicator: the base URL, index/alias, doc type, the term/sort
field names, the URN scheme, optional basic auth, and the bounded timeout. Every
consumer (``HarvestStatusService`` in T-7 and its tests) mocks this one small
interface; ES details never leak past it.

It exposes exactly two read-only operations against the **ES 5.6.16** cluster,
using ES 5.6 **type-in-path** URLs (``/{index}/{type}/_count|_search``):

* :meth:`EsGateway.count_for_urn` — a ``term`` ``_count`` → raw doc count.
* :meth:`EsGateway.latest_datestamp_for_urn` — a size-1 ``_search`` → latest
  ``internal-datestamp`` or ``None``.

**Failure contract.** ES-down — a timeout, a connection/transport error, any
non-2xx response, or an unparseable/garbled 2xx body — collapses to a single
typed, non-throwing :class:`EsUnavailable`. T-7 maps ``EsUnavailable`` →
``harvest_status = unknown``. A *successful* query is never ``EsUnavailable``:
``count == 0`` is a valid "not in index" answer and an empty ``_search`` hit list
is a valid ``None`` ("no datestamp yet"); absence is not ES-down. A raw
``httpx.*`` error must never escape either method, and presence is never guessed
on failure (no degrade/fallback — per-dataset accuracy is non-negotiable).
"""

import logging
from datetime import datetime

import httpx

from app.core.config import Settings
from app.core.config import settings as default_settings

logger = logging.getLogger(__name__)

# ES term field path for the dataset identifier. T-5 spike proved (against the
# real localhost index, count=281) that the PLAIN field name matches; the
# ``.keyword`` sub-field does NOT exist (returns 0).
ES_DATASET_ID_FIELD: str = "abcdDatasetIdentifier"

# ``date`` field mapped in index/setup-elasticsearch.sh; sorted desc for last-seen.
ES_DATESTAMP_FIELD: str = "internal-datestamp"

# URN string shape. T-6 owns the shape; T-7 owns choosing the latest archive_id.
URN_TEMPLATE: str = "urn:gfbio.org:abcd:{provider_id}_{dataset_id}_{archive_id}"

# Constant scheme prefix, derived from the template so the two never drift.
URN_PREFIX: str = URN_TEMPLATE.split("{", 1)[0]  # "urn:gfbio.org:abcd:"


def _parse_best_effort_datestamp(value: object) -> datetime | None:
    """Best-effort parse of a hit's ``internal-datestamp`` value to a ``datetime``.

    The real harvested ``pansimple`` docs frequently carry no datestamp, and ES
    returns multi-valued fields as JSON arrays — so a present hit can yield a
    missing / ``None`` / empty / list / non-string / unparseable value. None of
    those is an ES-down condition: each resolves to ``None`` so the *successful*
    presence check is never masked. A list value is reduced to its first element;
    a trailing ``Z`` is tolerated (``fromisoformat`` rejects it pre-3.11).
    """
    if isinstance(value, list):
        value = value[0] if value else None
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def compose_dataset_urn(provider_id: int, dataset_id: int, archive_id: int) -> str:
    """Compose the GFBio ABCD dataset URN from its integer ids.

    The URN is ASCII by construction (all parts are ints), so there is no
    injection or encoding risk in the term value.
    """
    return URN_TEMPLATE.format(
        provider_id=provider_id,
        dataset_id=dataset_id,
        archive_id=archive_id,
    )


def parse_dataset_urn(identifier: str) -> tuple[int, int, int] | None:
    """Parse a GFBio ABCD identifier back into ``(provider_id, dataset_id, archive_id)``.

    The exact inverse of :func:`compose_dataset_urn`. This is the join from a
    search ES ``abcdDatasetIdentifier`` term value back to the aggregator's
    integer ids, used by the public validation-stats endpoint.

    A ``:unitID`` suffix (unit-level docs carry the dataset URN plus the unit id,
    per the harvester's ``ESConnector`` and panFMP ``config.xml``) is stripped so
    a unit identifier resolves to its parent dataset. Anything that is not a
    well-formed dataset URN — wrong scheme, wrong component count, or a
    non-integer component — returns ``None`` rather than raising, so one bad id
    in a batch never fails the whole lookup.
    """
    if not isinstance(identifier, str) or not identifier.startswith(URN_PREFIX):
        return None
    # Drop the scheme prefix, then any ':unitID' suffix on unit-level identifiers.
    body = identifier[len(URN_PREFIX) :].split(":", 1)[0]
    parts = body.split("_")
    if len(parts) != 3 or not all(part.isascii() and part.isdigit() for part in parts):
        return None
    provider_id, dataset_id, archive_id = (int(part) for part in parts)
    return provider_id, dataset_id, archive_id


class EsUnavailable(Exception):
    """Typed, non-throwing-to-the-caller signal that Elasticsearch is unreachable.

    Raised by :class:`EsGateway` for every ES-down path (timeout, connection /
    transport error, non-2xx, or unparseable/garbled body). T-7's
    ``HarvestStatusService`` catches this and maps it to ``harvest_status =
    unknown`` — never a guessed presence. Always raised with ``from err`` (B904)
    so the originating cause is preserved on ``__cause__``.
    """


class EsGateway:
    """Thin async httpx client over Elasticsearch — pure HTTP, no DB.

    A per-call :class:`httpx.AsyncClient` is opened inside ``async with`` so the
    explicit bounded timeout covers connect+read+write+pool and the socket is
    always released, even when ``.post`` raises.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings if settings is not None else default_settings
        self._base_url = settings.ES_BASE_URL.rstrip("/")
        self._index = settings.ES_INDEX
        self._doc_type = settings.ES_DOC_TYPE
        self._timeout_seconds = settings.ES_TIMEOUT_SECONDS
        self._auth = (
            httpx.BasicAuth(settings.ES_USERNAME, settings.ES_PASSWORD)
            if settings.ES_USERNAME
            else None
        )

    def _endpoint(self, op: str) -> str:
        """Build an ES 5.6 type-in-path endpoint URL (``/{index}/{type}/{op}``)."""
        return f"{self._base_url}/{self._index}/{self._doc_type}/{op}"

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout_seconds),
            auth=self._auth,
        )

    async def count_for_urn(self, urn: str) -> int:
        """Return the raw ES doc count for ``urn`` via a ``term`` ``_count`` query.

        On success returns the integer ``count`` (``0`` is a valid "not in
        index"). Any ES-down path raises :class:`EsUnavailable`. The caller
        derives ``present = count >= 1`` and ``M = max(count - 1, 0)``.
        """
        url = self._endpoint("_count")
        body = {"query": {"term": {ES_DATASET_ID_FIELD: urn}}}
        try:
            async with self._client() as client:
                response = await client.post(url, json=body)
                response.raise_for_status()
                return int(response.json()["count"])
        except (
            httpx.TimeoutException,
            httpx.TransportError,
            httpx.HTTPStatusError,
            KeyError,
            TypeError,
            ValueError,
        ) as err:
            logger.warning("ES _count unavailable for urn=%s: %s", urn, err)
            raise EsUnavailable(f"Elasticsearch _count failed for {urn}") from err

    async def latest_datestamp_for_urn(self, urn: str) -> datetime | None:
        """Return the latest ``internal-datestamp`` for ``urn``, or ``None``.

        Issues a size-1 ``_search`` sorted by ``internal-datestamp`` desc.

        Transport/HTTP failure — a timeout, connection/transport error, a non-2xx
        response, or a structurally malformed body missing the ``hits`` envelope —
        raises :class:`EsUnavailable` (T-7 → ``unknown``). Everything *after* a
        valid envelope is **best-effort**: zero hits, or a present hit whose
        ``internal-datestamp`` is missing / ``None`` / empty / list-valued /
        non-string / unparseable, returns ``None``. A missing datestamp is a
        data-quality fact, **not** ES-down, and never masks the successful
        presence check.
        """
        url = self._endpoint("_search")
        body = {
            "size": 1,
            "_source": [ES_DATESTAMP_FIELD],
            "query": {"term": {ES_DATASET_ID_FIELD: urn}},
            "sort": [{ES_DATESTAMP_FIELD: {"order": "desc"}}],
        }
        try:
            async with self._client() as client:
                response = await client.post(url, json=body)
                response.raise_for_status()
                hits = response.json()["hits"]["hits"]
        except (
            httpx.TimeoutException,
            httpx.TransportError,
            httpx.HTTPStatusError,
            KeyError,
            TypeError,
            ValueError,
        ) as err:
            logger.warning("ES _search unavailable for urn=%s: %s", urn, err)
            raise EsUnavailable(f"Elasticsearch _search failed for {urn}") from err

        if not hits:
            return None
        source = hits[0].get("_source", {}) if isinstance(hits[0], dict) else {}
        return _parse_best_effort_datestamp(source.get(ES_DATESTAMP_FIELD))
