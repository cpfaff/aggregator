"""Tests for app.utils.query_utils (filter/sort application to SQL queries)."""

from sqlalchemy import select

from app.models.dataset import DatasetModel
from app.utils.filtering import FilterOperator, FilterParam
from app.utils.query_utils import apply_filters


def _compiled(query) -> str:
    return str(query.compile(compile_kwargs={"literal_binds": True}))


class TestLikeFilterEscaping:
    """LIKE values must not let user-supplied % and _ act as wildcards (B17)."""

    def test_like_escapes_percent_and_underscore(self):
        query = select(DatasetModel)
        filters = [FilterParam(field="title", operator=FilterOperator.LIKE, value="100%_x")]
        out = _compiled(apply_filters(query, filters, {"title": DatasetModel.title}))

        # The user's % and _ are escaped, and an ESCAPE clause is emitted so they
        # are treated as literals, not wildcards.
        assert "ESCAPE" in out.upper()
        assert r"100\%\_x" in out

    def test_like_escapes_backslash(self):
        query = select(DatasetModel)
        filters = [FilterParam(field="title", operator=FilterOperator.LIKE, value="a\\b")]
        out = _compiled(apply_filters(query, filters, {"title": DatasetModel.title}))

        # A literal backslash in the value must itself be escaped first.
        assert r"a\\b" in out
