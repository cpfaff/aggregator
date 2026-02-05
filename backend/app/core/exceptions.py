"""Custom API exceptions with RFC 7807 support."""


class APIError(Exception):
    """Base API error that supports RFC 7807 Problem Details."""

    def __init__(
        self,
        status_code: int,
        error_type: str,
        title: str,
        detail: str | None = None,
    ):
        self.status_code = status_code
        self.error_type = error_type
        self.title = title
        self.detail = detail
        super().__init__(detail or title)


class NotFoundError(APIError):
    """Resource not found error (404)."""

    def __init__(self, resource: str, identifier: str | int):
        super().__init__(
            status_code=404,
            error_type="not-found",
            title="Resource Not Found",
            detail=f"{resource} with ID {identifier} does not exist.",
        )
        self.resource = resource
        self.identifier = identifier


class BadRequestError(APIError):
    """Bad request error (400)."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=400,
            error_type="bad-request",
            title="Bad Request",
            detail=detail,
        )


class UnauthorizedError(APIError):
    """Authentication required error (401)."""

    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=401,
            error_type="unauthorized",
            title="Unauthorized",
            detail=detail,
        )


class ForbiddenError(APIError):
    """Permission denied error (403)."""

    def __init__(self, detail: str = "Permission denied"):
        super().__init__(
            status_code=403,
            error_type="forbidden",
            title="Forbidden",
            detail=detail,
        )


class ConflictError(APIError):
    """Resource conflict error (409)."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=409,
            error_type="conflict",
            title="Conflict",
            detail=detail,
        )
