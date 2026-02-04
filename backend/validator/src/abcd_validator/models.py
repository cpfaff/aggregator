#!/usr/bin/env python3
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ValidationError:
    """
    Represents a single validation error found during XML validation.
    """

    message: str
    error_type: str
    severity: str
    line: int | None = None
    column: int | None = None
    path: str | None = None
    domain_name: str | None = None
    type_name: str | None = None
    level: int | None = None


@dataclass
class ValidationResult:
    """
    Contains the results of validating a single XML file.
    """

    file_name: str
    file_size: int
    schema_valid: bool
    validation_time: float
    errors: list[ValidationError]
    custom_rule_results: list[dict[str, Any]]
    schema_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Returns a dictionary representation of the validation result.
        """
        return {
            "file_name": self.file_name,
            "file_size": self.file_size,
            "schema_valid": self.schema_valid,
            "validation_time": round(self.validation_time, 3),
            "errors": [asdict(error) for error in self.errors],
            "custom_rule_results": self.custom_rule_results,
            "schema_version": self.schema_version,
        }
