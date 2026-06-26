"""REQ-SH-TL-1/2: one coherent timeline contract.

Discovery F-L: one statistics surface shipped three timeline payload shapes, two of
them colliding on a ``data_points`` key with *incompatible* element types —
``TimeSeriesResponse.data_points`` is ``list[TimeSeriesPoint]``, but the
multi-provider endpoint's ``data_points`` are provider-keyed wide-row dicts, served
as ``dict[str, Any]`` (untyped in OpenAPI).

Per Q5 the multi-provider endpoint gains a real typed response model and its
wide-row key is renamed off ``data_points``, so ``data_points`` denotes one element
type (TimeSeriesPoint) everywhere.

* TL-1 — every timeline endpoint declares a typed response model (not dict[str, Any]).
* TL-2 — the ``data_points`` key carries one declared element type across endpoints.
"""

_MULTI_PROVIDER_PATH = "/api/v1/statistics/multi-provider-biological-units"


def _spec() -> dict:
    from main import app

    return app.openapi()


def test_multi_provider_endpoint_has_typed_response_model():
    """REQ-SH-TL-1: the multi-provider timeline endpoint is typed (a named model,
    not the opaque dict[str, Any] that documents nothing in OpenAPI)."""
    spec = _spec()
    schema = spec["paths"][_MULTI_PROVIDER_PATH]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert "$ref" in schema, f"multi-provider response is still untyped: {schema}"
    assert schema["$ref"].endswith("MultiProviderTimelineResponse")


def test_data_points_key_denotes_one_element_type():
    """REQ-SH-TL-2: across statistics schemas, a 'data_points' key carries elements
    of one declared type (TimeSeriesPoint); the wide-row payload uses a different key."""
    schemas = _spec()["components"]["schemas"]

    ts_items = schemas["TimeSeriesResponse"]["properties"]["data_points"]["items"]
    assert ts_items["$ref"].endswith("TimeSeriesPoint")

    mp_props = schemas["MultiProviderTimelineResponse"]["properties"]
    assert "data_points" not in mp_props, "wide-row payload must not reuse the data_points key"
    assert "series" in mp_props, "wide-row payload should expose its points under 'series'"
