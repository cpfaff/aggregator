#!/usr/bin/env python3
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

@dataclass
class ValidationError:
    """
    Represents a single validation error found during XML validation.
    """
    message: str
    error_type: str
    severity: str
    line: Optional[int] = None
    column: Optional[int] = None
    path: Optional[str] = None
    domain_name: Optional[str] = None
    type_name: Optional[str] = None
    level: Optional[int] = None

@dataclass
class ValidationResult:
    """
    Contains the results of validating a single XML file.
    """
    file_name: str
    file_size: int
    schema_valid: bool
    validation_time: float
    errors: List[ValidationError]
    custom_rule_results: List[Dict[str, Any]]
    schema_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Returns a dictionary representation of the validation result.
        """
        return {
            'file_name': self.file_name,
            'file_size': self.file_size,
            'schema_valid': self.schema_valid,
            'validation_time': round(self.validation_time, 3),
            'errors': [asdict(error) for error in self.errors],
            'custom_rule_results': self.custom_rule_results,
            'schema_version': self.schema_version
        }
