"""Regression test for the broken CSRF decorator (B11).

`@csrf_protect.validate_csrf` was stacked above `@router.post/put/delete`.
validate_csrf is an async instance method, not a decorator, so applying it
rebound the endpoint's module-level name to a never-awaited coroutine OBJECT
(emitting RuntimeWarnings) while providing zero protection — security theater.
The served route worked only because @router.* had already registered the
original function.

Auth is Bearer-token-in-header (not cookie), so CSRF is not an applicable threat
(forged cross-site requests fail at authentication). The fix removes the dead
no-op decorators; this test asserts the endpoint names are real coroutine
functions again.
"""

import inspect

from app.api.v1.endpoints import datasets, providers


def test_mutating_dataset_endpoints_are_real_coroutine_functions():
    for fn in (datasets.create_dataset, datasets.update_dataset, datasets.delete_dataset):
        assert inspect.iscoroutinefunction(fn), f"{fn!r} is not a coroutine function"


def test_mutating_provider_endpoints_are_real_coroutine_functions():
    for fn in (providers.create_provider, providers.update_provider, providers.delete_provider):
        assert inspect.iscoroutinefunction(fn), f"{fn!r} is not a coroutine function"
