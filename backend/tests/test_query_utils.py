"""Tests for app.utils.query_utils (filter/sort application to SQL queries)."""

import pytest
from sqlalchemy import select

from app.models.dataset import DatasetModel
from app.models.user import UserModel
from app.utils.filtering import FilterError, FilterOperator, FilterParam
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


class TestFilterValueCoercion:
    """Filter values are coerced to the column type; uncastable -> FilterError (B18)."""

    def test_non_numeric_value_on_int_column_raises(self):
        query = select(DatasetModel)
        filters = [FilterParam(field="provider_id", operator=FilterOperator.EQ, value="abc")]
        with pytest.raises(FilterError):
            apply_filters(query, filters, {"provider_id": DatasetModel.provider_id})

    def test_numeric_string_on_int_column_is_coerced(self):
        query = select(DatasetModel)
        filters = [FilterParam(field="provider_id", operator=FilterOperator.EQ, value="5")]
        out = _compiled(apply_filters(query, filters, {"provider_id": DatasetModel.provider_id}))
        # Coerced to an int literal, not the string '5'.
        assert "= 5" in out
        assert "= '5'" not in out

    def test_non_boolean_value_on_bool_column_raises(self):
        query = select(UserModel)
        filters = [FilterParam(field="is_global_admin", operator=FilterOperator.EQ, value="maybe")]
        with pytest.raises(FilterError):
            apply_filters(query, filters, {"is_global_admin": UserModel.is_global_admin})

    def test_boolean_string_on_bool_column_is_accepted(self):
        query = select(UserModel)
        for raw in ("true", "false"):
            filters = [
                FilterParam(field="is_global_admin", operator=FilterOperator.EQ, value=raw)
            ]
            # Must not raise; coercion succeeds.
            apply_filters(query, filters, {"is_global_admin": UserModel.is_global_admin})

    def test_string_column_value_passes_through(self):
        query = select(DatasetModel)
        filters = [FilterParam(field="title", operator=FilterOperator.EQ, value="anything")]
        out = _compiled(apply_filters(query, filters, {"title": DatasetModel.title}))
        assert "'anything'" in out

    def test_in_operator_coerces_each_element(self):
        query = select(DatasetModel)
        filters = [
            FilterParam(field="provider_id", operator=FilterOperator.IN, value=["1", "2"])
        ]
        out = _compiled(apply_filters(query, filters, {"provider_id": DatasetModel.provider_id}))
        assert "'1'" not in out  # ints, not strings

    def test_in_operator_uncastable_element_raises(self):
        query = select(DatasetModel)
        filters = [
            FilterParam(field="provider_id", operator=FilterOperator.IN, value=["1", "x"])
        ]
        with pytest.raises(FilterError):
            apply_filters(query, filters, {"provider_id": DatasetModel.provider_id})
