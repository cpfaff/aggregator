"""Tests for RFC 7807 error response handling."""

import pytest

from app.core.exceptions import (
    APIError,
    BadRequestError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from app.schemas.errors import ProblemDetail, ValidationProblemDetail


class TestProblemDetailSchema:
    def test_problem_detail_required_fields(self):
        """ProblemDetail requires title and status."""
        problem = ProblemDetail(title="Not Found", status=404)
        assert problem.title == "Not Found"
        assert problem.status == 404
        assert problem.type == "about:blank"

    def test_problem_detail_with_all_fields(self):
        """ProblemDetail accepts all RFC 7807 fields."""
        problem = ProblemDetail(
            type="https://api.gfbio.org/errors/not-found",
            title="Resource Not Found",
            status=404,
            detail="Provider with ID 999 does not exist.",
            instance="/api/v1/data-providers/999",
        )
        assert problem.type == "https://api.gfbio.org/errors/not-found"
        assert problem.detail == "Provider with ID 999 does not exist."
        assert problem.instance == "/api/v1/data-providers/999"

    def test_problem_detail_has_timestamp(self):
        """ProblemDetail includes timestamp extension field."""
        problem = ProblemDetail(title="Error", status=500)
        assert problem.timestamp is not None

    def test_validation_problem_detail_has_errors(self):
        """ValidationProblemDetail includes errors list."""
        problem = ValidationProblemDetail(
            title="Validation Error",
            status=422,
            errors=[{"field": "name", "message": "Field required"}],
        )
        assert len(problem.errors) == 1
        assert problem.errors[0]["field"] == "name"


class TestAPIExceptions:
    def test_not_found_error(self):
        """NotFoundError has correct attributes."""
        error = NotFoundError("Provider", 999)
        assert error.status_code == 404
        assert error.error_type == "not-found"
        assert error.title == "Resource Not Found"
        assert "999" in error.detail

    def test_bad_request_error(self):
        """BadRequestError has correct attributes."""
        error = BadRequestError("Invalid parameter")
        assert error.status_code == 400
        assert error.error_type == "bad-request"

    def test_unauthorized_error(self):
        """UnauthorizedError has correct attributes."""
        error = UnauthorizedError()
        assert error.status_code == 401
        assert error.error_type == "unauthorized"

    def test_forbidden_error(self):
        """ForbiddenError has correct attributes."""
        error = ForbiddenError("Admin required")
        assert error.status_code == 403
        assert "Admin required" in error.detail

    def test_api_error_is_exception(self):
        """APIError can be raised and caught."""
        with pytest.raises(APIError) as exc_info:
            raise NotFoundError("User", 1)
        assert exc_info.value.status_code == 404
