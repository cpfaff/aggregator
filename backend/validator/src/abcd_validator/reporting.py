#!/usr/bin/env python3
import re
from collections import defaultdict
from collections.abc import Iterator
from itertools import islice
from typing import Any

from .models import ValidationError, ValidationResult

# Define the default batch size for reporting
DEFAULT_BATCH_SIZE = 100

# --- Mapping dictionary for lxml schema error types ---
ERROR_TYPE_MAPPING = {
    "SCHEMAV_CVC_PATTERN_VALID": "Invalid format for {element}. Please check the expected pattern in the schema documentation.",
    "SCHEMAV_CVC_DATATYPE_VALID_1_2_1": "Invalid datatype for {element}. Please ensure the value conforms to the expected data type.",
    "SCHEMAV_CVC_ATTRIBUTE_1": "Invalid attribute value for {element}. Verify that the attribute value meets the schema requirements.",
    "SCHEMAV_CVC_ATTRIBUTE_2": "Invalid attribute value for {element}. Verify that the attribute value meets the schema requirements.",
    "SCHEMAV_CVC_ATTRIBUTE_3": "Invalid attribute value for {element}. Verify that the attribute value meets the schema requirements.",
    "SCHEMAV_CVC_ATTRIBUTE_4": "Invalid attribute value for {element}. Verify that the attribute value meets the schema requirements.",
    "SCHEMAV_CVC_ELT_1": "Invalid element value for {element}. Please check the schema documentation for valid values.",
    "SCHEMAV_CVC_ELT_2": "Invalid element value for {element}. Please check the schema documentation for valid values.",
    "SCHEMAV_CVC_ELT_3_1": "Invalid element structure for {element}. Ensure the element structure conforms to the schema.",
    "SCHEMAV_CVC_ELT_3_2_1": "Invalid element structure for {element}. Ensure the element structure conforms to the schema.",
    "SCHEMAV_CVC_ELT_3_2_2": "Invalid element structure for {element}. Ensure the element structure conforms to the schema.",
    "SCHEMAV_CVC_ELT_4_1": "Invalid element content for {element}. Check that the content matches schema expectations.",
    "SCHEMAV_CVC_ELT_4_2": "Invalid element content for {element}. Check that the content matches schema expectations.",
    "SCHEMAV_CVC_ELT_4_3": "Invalid element content for {element}. Check that the content matches schema expectations.",
    "SCHEMAV_CVC_ENUMERATION_VALID": "Invalid enumeration value for {element}. Please check the schema documentation for the list of allowed values.",
    "SCHEMAV_CVC_FACET_VALID": "Invalid facet constraint for {element}. Check the schema requirements for this element.",
    "SCHEMAV_CVC_LENGTH_VALID": "Invalid length for {element}. Ensure the length conforms to schema specifications.",
    "SCHEMAV_CVC_MAXEXCLUSIVE_VALID": "Value exceeds the maximum exclusive limit for {element}. Please use a smaller value that meets the schema constraints.",
    "SCHEMAV_CVC_MAXINCLUSIVE_VALID": "Value exceeds the maximum inclusive limit for {element}. Please use a smaller value that meets the schema constraints.",
    "SCHEMAV_CVC_MAXLENGTH_VALID": "Value exceeds the maximum length for {element}. Consider splitting the content into multiple fields or abbreviating it.",
    "SCHEMAV_CVC_MINEXCLUSIVE_VALID": "Value is below the minimum exclusive limit for {element}. Please use a larger value that meets the schema constraints.",
    "SCHEMAV_CVC_MININCLUSIVE_VALID": "Value is below the minimum inclusive limit for {element}. Please use a larger value that meets the schema constraints.",
    "SCHEMAV_CVC_MINLENGTH_VALID": "Value is shorter than the minimum length for {element}. Please provide proper content for this element or consider removing it if not applicable.",
    "SCHEMAV_CVC_TOTALDIGITS_VALID": "Total digits exceed allowed count for {element}. Ensure the number conforms to the digit limit in the schema.",
    "SCHEMAV_DOCUMENT_ELEMENT_MISSING": "Document element is missing. Please check the XML document structure.",
    "SCHEMAV_INVALIDATTR": "Invalid attribute on {element}. Check schema for permitted attributes.",
    "SCHEMAV_INVALIDELEM": "Invalid element encountered. Verify against the schema documentation.",
    "SCHEMAV_NOTEMPTY": "{element} must not be empty. Please provide valid content for this element.",
    "SCHEMAV_NOTYPE": "Type mismatch in {element}. Ensure the element content matches the expected type.",
}

# Precompiled regex patterns for performance improvements
ELEMENT_REGEX = re.compile(r"Element '(.+?)': ")
VALUE_PATTERNS = [
    re.compile(r"Element '[^']+': '([^']+)' is not a valid value"),
    re.compile(r"'([^']+)' is not a valid value"),
    re.compile(r"The value '(.+?)' is not accepted"),
    re.compile(r"The value '(.+?)' is not an element"),
    # Captures length from facet constraint errors
    re.compile(r"The value has a length of '(\d+)'"),
]
NORMALIZE_PATH_REGEX = re.compile(r"\[\d+\]")

# Caches to avoid redundant computations
_normalized_path_cache: dict[str, str] = {}
_error_component_cache: dict[str, dict[str, Any]] = {}


def format_file_size(size_bytes: int) -> str:
    """Convert a file size in bytes into a human‐readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_time(seconds: float) -> str:
    """Convert seconds into a human‐readable string."""
    if seconds < 60:
        return f"{seconds:.1f} sec"
    else:
        minutes, sec = divmod(seconds, 60)
        if minutes < 60:
            return f"{int(minutes)} min {sec:.1f} sec"
        else:
            hours, minutes = divmod(minutes, 60)
            return f"{int(hours)} hr {int(minutes)} min {sec:.1f} sec"


def normalize_path(path: str) -> str:
    """
    Normalize an XML path by replacing numeric indices with a wildcard.
    For example, "/a[1]/b[3]" becomes "/a[*]/b[*]".
    """
    if not path:
        return path
    if path not in _normalized_path_cache:
        _normalized_path_cache[path] = NORMALIZE_PATH_REGEX.sub("[*]", path)
    return _normalized_path_cache[path]


def get_local_name(qname: str) -> str:
    """
    Extract the local name from a qualified XML name.
    E.g. '{http://www.example.com}TagName' becomes 'TagName'.
    """
    if qname and qname.startswith("{"):
        return qname.split("}", 1)[1]
    return qname


def extract_error_components(error: ValidationError) -> dict[str, Any]:
    """
    Extract key components (such as element and value) from a ValidationError message.
    Uses caching to avoid reprocessing the same error message.
    For non-schema errors, falls back to line information if an element isn’t detected.
    """
    key = error.message
    if key in _error_component_cache:
        return _error_component_cache[key]
    element = None
    value = None
    m = ELEMENT_REGEX.search(error.message)
    if m:
        element = m.group(1)
    if not element and error.error_type in ("syntax", "encoding", "processing", "unknown"):
        element = f"Line {error.line}" if error.line else "Unknown"
    for pattern in VALUE_PATTERNS:
        m = pattern.search(error.message)
        if m:
            value = m.group(1)
            break
    comps = {
        "element": element,
        "value": value,
        "normalized_path": normalize_path(error.path) if error.path else None,
    }
    _error_component_cache[key] = comps
    return comps


# --- Aggregators for batched processing ---


def aggregate_schema_errors_batch(results: list[ValidationResult]) -> dict[tuple, dict[str, Any]]:
    error_groups = defaultdict(
        lambda: {
            "message": None,
            "validation_type": None,
            "element": None,
            "total_errors": 0,
            "values": set(),
            "files": set(),
            "paths": set(),
            "details": None,
            "context_details": set(),
        }
    )
    for result in results:
        for error in result.errors:
            if error.error_type != "schema":
                continue
            comps = extract_error_components(error)
            key = (error.type_name, comps.get("normalized_path"), comps.get("element"))
            group = error_groups[key]
            if group["message"] is None:
                template = ERROR_TYPE_MAPPING.get(error.type_name)
                if template:
                    base_msg = template.format(element=comps.get("element") or "Unknown element")
                else:
                    base_msg = error.message.split("\n")[0]
                group["message"] = base_msg
                group["validation_type"] = error.type_name
                group["element"] = comps.get("element")
                group["details"] = {
                    "domain": getattr(error, "domain_name", None),
                    "level": getattr(error, "level", None),
                }
                parts = error.message.split("\n")
                if len(parts) > 1:
                    detail = " ".join(parts[1:]).strip()
                    if detail:
                        group["context_details"].add(detail)
                elif ":" in error.message:
                    detail = error.message.split(":", 1)[1].strip()
                    if detail:
                        group["context_details"].add(detail)
            group["total_errors"] += 1
            if comps.get("value"):
                group["values"].add(comps.get("value"))
            group["files"].add(result.file_name)
            if error.path:
                group["paths"].add(comps.get("normalized_path"))
    return error_groups


def merge_schema_errors(
    dict1: dict[tuple, dict[str, Any]], dict2: dict[tuple, dict[str, Any]]
) -> dict[tuple, dict[str, Any]]:
    for key, group in dict2.items():
        if key in dict1:
            existing = dict1[key]
            existing["total_errors"] += group["total_errors"]
            existing["values"].update(group["values"])
            existing["files"].update(group["files"])
            existing["paths"].update(group["paths"])
            existing["context_details"].update(group["context_details"])
        else:
            dict1[key] = group
    return dict1


def finalize_schema_errors(error_groups: dict[tuple, dict[str, Any]]) -> list[dict[str, Any]]:
    aggregated = []
    for group in error_groups.values():
        message = group["message"]
        element_name = get_local_name(group["element"]) if group["element"] else "Unknown"
        validation_type = group["validation_type"]

        # Extract constraint values from context details when available
        constraint_value = None
        if group["context_details"]:
            context = next(iter(group["context_details"]))

            # Extract min/max length constraints
            if validation_type == "SCHEMAV_CVC_MINLENGTH_VALID":
                min_match = re.search(r"allowed minimum length of '(\d+)'", context)
                if min_match:
                    constraint_value = min_match.group(1)
                    # Add XML example for minLength violation - using local element name only
                    # Use proper XML format with abcd21 namespace as commonly used in the files
                    xml_example = f'&lt;abcd21:{element_name} language="de" /&gt;'
                    message += f" Required length: at least {constraint_value} characters. Example of problematic format: {xml_example}"

            elif validation_type == "SCHEMAV_CVC_MAXLENGTH_VALID":
                max_match = re.search(r"allowed maximum length of '(\d+)'", context)
                if max_match:
                    constraint_value = max_match.group(1)
                    # Add max length information to message
                    message += f" Maximum allowed length: {constraint_value} characters."

                    # If we have a value example that's too long, provide a truncated example
                    if group["values"]:
                        actual_length = next(iter(group["values"]), "unknown")
                        message += f" Your content length: {actual_length} characters."

            # Extract enumeration constraints
            elif validation_type == "SCHEMAV_CVC_ENUMERATION_VALID":
                # Add XML example for enumeration
                message += f" Example usage: &lt;abcd21:{element_name}&gt;allowed_value&lt;/abcd21:{element_name}&gt;"

            # Extract pattern constraints
            elif validation_type == "SCHEMAV_CVC_PATTERN_VALID":
                pattern_match = re.search(
                    r"The value '.*?' is not a valid value of the atomic type '.*?' - pattern constraint failed: '(.*?)'",
                    context,
                )
                if pattern_match:
                    pattern = pattern_match.group(1)
                    message += f" Pattern constraint: '{pattern}'"

        # Optionally add count information but NO examples to message
        if group["values"]:
            distinct_count = len(group["values"])
            message = f"{message} ({distinct_count} distinct values found)"

        aggregated.append(
            {
                "heading": f"Schema error for {element_name}",
                "context": "; ".join(sorted(list(group["context_details"]))),
                "message": message,
                "total_errors": group["total_errors"],
                "affected_files": {
                    "total": len(group["files"]),
                    "examples": sorted(list(group["files"]))[:5],
                    "has_more": len(group["files"]) > 5,
                },
                "details": {
                    "validation_type": validation_type,
                    "domain": group["details"]["domain"] if group["details"] else None,
                    "level": group["details"]["level"] if group["details"] else None,
                    "sample_paths": sorted(list(group["paths"]))[:3],
                    "distinct_values": sorted(list(group["values"]))[:5]
                    if group["values"]
                    else None,
                    "distinct_count": len(group["values"]) if group["values"] else 0,
                },
            }
        )
    aggregated.sort(key=lambda x: x["total_errors"], reverse=True)
    return aggregated


def aggregate_syntax_errors_batch(results: list[ValidationResult]) -> dict[tuple, dict[str, Any]]:
    groups = defaultdict(
        lambda: {
            "message": None,
            "error_type": None,
            "element": None,
            "total_errors": 0,
            "files": set(),
            "lines": set(),
        }
    )
    for result in results:
        for error in result.errors:
            if error.error_type != "syntax":
                continue
            comps = extract_error_components(error)
            key = (error.error_type, error.message.split("\n")[0], comps.get("element"))
            group = groups[key]
            if group["message"] is None:
                group["message"] = error.message.split("\n")[0]
                group["error_type"] = error.error_type
                group["element"] = comps.get("element")
            group["total_errors"] += 1
            group["files"].add(result.file_name)
            if error.line:
                group["lines"].add(error.line)
    return groups


def merge_syntax_errors(
    dict1: dict[tuple, dict[str, Any]], dict2: dict[tuple, dict[str, Any]]
) -> dict[tuple, dict[str, Any]]:
    for key, group in dict2.items():
        if key in dict1:
            existing = dict1[key]
            existing["total_errors"] += group["total_errors"]
            existing["files"].update(group["files"])
            existing["lines"].update(group["lines"])
        else:
            dict1[key] = group
    return dict1


def finalize_syntax_errors(groups: dict[tuple, dict[str, Any]]) -> list[dict[str, Any]]:
    aggregated = []
    for group in groups.values():
        aggregated.append(
            {
                "heading": f"Syntax error at {group['element']}",
                "message": group["message"],
                "total_errors": group["total_errors"],
                "affected_files": {
                    "total": len(group["files"]),
                    "examples": sorted(list(group["files"]))[:5],
                    "has_more": len(group["files"]) > 5,
                },
                "details": {"lines": sorted(list(group["lines"]))},
            }
        )
    aggregated.sort(key=lambda x: x["total_errors"], reverse=True)
    return aggregated


def aggregate_encoding_errors_batch(results: list[ValidationResult]) -> dict[tuple, dict[str, Any]]:
    groups = defaultdict(
        lambda: {
            "message": None,
            "error_type": None,
            "element": None,
            "total_errors": 0,
            "files": set(),
        }
    )
    for result in results:
        for error in result.errors:
            if error.error_type != "encoding":
                continue
            comps = extract_error_components(error)
            key = (error.error_type, error.message.split("\n")[0])
            group = groups[key]
            if group["message"] is None:
                group["message"] = error.message.split("\n")[0]
                group["error_type"] = error.error_type
                group["element"] = comps.get("element")
            group["total_errors"] += 1
            group["files"].add(result.file_name)
    return groups


def merge_encoding_errors(
    dict1: dict[tuple, dict[str, Any]], dict2: dict[tuple, dict[str, Any]]
) -> dict[tuple, dict[str, Any]]:
    for key, group in dict2.items():
        if key in dict1:
            existing = dict1[key]
            existing["total_errors"] += group["total_errors"]
            existing["files"].update(group["files"])
        else:
            dict1[key] = group
    return dict1


def finalize_encoding_errors(groups: dict[tuple, dict[str, Any]]) -> list[dict[str, Any]]:
    aggregated = []
    for group in groups.values():
        aggregated.append(
            {
                "heading": "Encoding error",
                "message": group["message"],
                "total_errors": group["total_errors"],
                "affected_files": {
                    "total": len(group["files"]),
                    "examples": sorted(list(group["files"]))[:5],
                    "has_more": len(group["files"]) > 5,
                },
                "details": {},
            }
        )
    aggregated.sort(key=lambda x: x["total_errors"], reverse=True)
    return aggregated


def aggregate_processing_errors_batch(
    results: list[ValidationResult],
) -> dict[tuple, dict[str, Any]]:
    groups = defaultdict(
        lambda: {
            "message": None,
            "error_type": None,
            "element": None,
            "total_errors": 0,
            "files": set(),
        }
    )
    for result in results:
        for error in result.errors:
            if error.error_type != "processing":
                continue
            comps = extract_error_components(error)
            key = (error.error_type, error.message.split("\n")[0])
            group = groups[key]
            if group["message"] is None:
                group["message"] = error.message.split("\n")[0]
                group["error_type"] = error.error_type
                group["element"] = comps.get("element")
            group["total_errors"] += 1
            group["files"].add(result.file_name)
    return groups


def merge_processing_errors(
    dict1: dict[tuple, dict[str, Any]], dict2: dict[tuple, dict[str, Any]]
) -> dict[tuple, dict[str, Any]]:
    for key, group in dict2.items():
        if key in dict1:
            existing = dict1[key]
            existing["total_errors"] += group["total_errors"]
            existing["files"].update(group["files"])
        else:
            dict1[key] = group
    return dict1


def finalize_processing_errors(groups: dict[tuple, dict[str, Any]]) -> list[dict[str, Any]]:
    aggregated = []
    for group in groups.values():
        aggregated.append(
            {
                "heading": "Processing error",
                "message": group["message"],
                "total_errors": group["total_errors"],
                "affected_files": {
                    "total": len(group["files"]),
                    "examples": sorted(list(group["files"]))[:5],
                    "has_more": len(group["files"]) > 5,
                },
                "details": {},
            }
        )
    aggregated.sort(key=lambda x: x["total_errors"], reverse=True)
    return aggregated


def aggregate_unknown_errors_batch(results: list[ValidationResult]) -> dict[tuple, dict[str, Any]]:
    groups = defaultdict(
        lambda: {
            "message": None,
            "error_type": None,
            "element": None,
            "total_errors": 0,
            "files": set(),
        }
    )
    for result in results:
        for error in result.errors:
            if error.error_type != "unknown":
                continue
            comps = extract_error_components(error)
            key = (error.error_type, error.message.split("\n")[0])
            group = groups[key]
            if group["message"] is None:
                group["message"] = error.message.split("\n")[0]
                group["error_type"] = error.error_type
                group["element"] = comps.get("element")
            group["total_errors"] += 1
            group["files"].add(result.file_name)
    return groups


def merge_unknown_errors(
    dict1: dict[tuple, dict[str, Any]], dict2: dict[tuple, dict[str, Any]]
) -> dict[tuple, dict[str, Any]]:
    for key, group in dict2.items():
        if key in dict1:
            existing = dict1[key]
            existing["total_errors"] += group["total_errors"]
            existing["files"].update(group["files"])
        else:
            dict1[key] = group
    return dict1


def finalize_unknown_errors(groups: dict[tuple, dict[str, Any]]) -> list[dict[str, Any]]:
    aggregated = []
    for group in groups.values():
        aggregated.append(
            {
                "heading": "Unknown error",
                "message": group["message"],
                "total_errors": group["total_errors"],
                "affected_files": {
                    "total": len(group["files"]),
                    "examples": sorted(list(group["files"]))[:5],
                    "has_more": len(group["files"]) > 5,
                },
                "details": {},
            }
        )
    aggregated.sort(key=lambda x: x["total_errors"], reverse=True)
    return aggregated


def aggregate_custom_rules_batch(
    results: list[ValidationResult],
) -> dict[str, dict[str, list[tuple[dict[str, Any], str]]]]:
    rule_aggregates = defaultdict(lambda: defaultdict(list))
    for result in results:
        for rule in result.custom_rule_results:
            if isinstance(rule, dict):
                importance = rule.get("importance", "optional")
                rule_name = rule.get("name")
                if rule_name:
                    rule_aggregates[importance][rule_name].append((rule, result.file_name))
    return rule_aggregates


def merge_custom_rules(
    dict1: dict[str, dict[str, list[tuple[dict[str, Any], str]]]],
    dict2: dict[str, dict[str, list[tuple[dict[str, Any], str]]]],
) -> dict[str, dict[str, list[tuple[dict[str, Any], str]]]]:
    for importance, rules in dict2.items():
        if importance not in dict1:
            dict1[importance] = rules
        else:
            for rule_name, rule_instances in rules.items():
                dict1[importance][rule_name].extend(rule_instances)
    return dict1


def finalize_custom_rules(
    rule_aggregates: dict[str, dict[str, list[tuple[dict[str, Any], str]]]],
) -> dict[str, list[dict[str, Any]]]:
    aggregated = {"mandatory": [], "recommended": [], "optional": []}
    for importance, rules in rule_aggregates.items():
        for rule_name, rule_instances in rules.items():
            base_rule = rule_instances[0][0]
            total_counts = {
                "total": 0,
                "categories": {
                    cat: {"count": 0, "percentage": 0}
                    for cat in ["missing", "empty", "invalid", "valid"]
                },
                "example_values": {"valid": set(), "invalid": set()},
            }
            affected_files = set()
            for rule_instance, file_name in rule_instances:
                if not rule_instance.get("valid", True):
                    affected_files.add(file_name)
                if "counts" in rule_instance and rule_instance["counts"]:
                    counts = rule_instance["counts"]
                    total_counts["total"] += counts.get("total", 0)
                    for cat in ["missing", "empty", "invalid", "valid"]:
                        total_counts["categories"][cat]["count"] += (
                            counts.get("categories", {}).get(cat, {}).get("count", 0)
                        )
                    for status in ["valid", "invalid"]:
                        examples = counts.get("example_values", {}).get(status, [])
                        for ex in examples:
                            total_counts["example_values"][status].add(ex)
            for cat in total_counts["categories"]:
                if total_counts["total"] > 0:
                    percentage = (
                        total_counts["categories"][cat]["count"] / total_counts["total"]
                    ) * 100
                    total_counts["categories"][cat]["percentage"] = round(percentage, 1)
            aggregated.setdefault(importance, []).append(
                {
                    "name": rule_name,
                    "importance": importance,
                    "valid": all(r[0].get("valid", True) for r in rule_instances),
                    "message": base_rule.get("message"),
                    "context_name": base_rule.get("context_name"),
                    "path": base_rule.get("path"),
                    "counts": {
                        "total": total_counts["total"],
                        "categories": {
                            cat: {
                                "count": total_counts["categories"][cat]["count"],
                                "percentage": total_counts["categories"][cat]["percentage"],
                            }
                            for cat in total_counts["categories"]
                        },
                        "example_values": {
                            status: sorted(list(vals))[:5]
                            for status, vals in total_counts["example_values"].items()
                        },
                    },
                    "affected_files": {
                        "total": len(affected_files),
                        "examples": sorted(list(affected_files))[:5],
                        "has_more": len(affected_files) > 5,
                    }
                    if affected_files
                    else None,
                }
            )
    for imp in ["mandatory", "recommended", "optional"]:
        aggregated.setdefault(imp, [])
    return aggregated


def aggregate_summary_batch(results: list[ValidationResult]) -> dict[str, Any]:
    summary = {
        "total_files": 0,
        "valid_files": 0,
        "total_size": 0,
        "total_time": 0.0,
        "schema_version": None,
    }
    for result in results:
        summary["total_files"] += 1
        if result.schema_valid:
            summary["valid_files"] += 1
        summary["total_size"] += result.file_size
        summary["total_time"] += result.validation_time
        if summary["schema_version"] is None and result.schema_version is not None:
            summary["schema_version"] = result.schema_version
    return summary


def merge_summary(sum1: dict[str, Any], sum2: dict[str, Any]) -> dict[str, Any]:
    merged = {
        "total_files": sum1.get("total_files", 0) + sum2.get("total_files", 0),
        "valid_files": sum1.get("valid_files", 0) + sum2.get("valid_files", 0),
        "total_size": sum1.get("total_size", 0) + sum2.get("total_size", 0),
        "total_time": sum1.get("total_time", 0) + sum2.get("total_time", 0),
        "schema_version": sum1.get("schema_version") or sum2.get("schema_version"),
    }
    return merged


def batch_iterator(iterable: Iterator[Any], batch_size: int) -> Iterator[list[Any]]:
    """Yield successive batches from an iterator using islice."""
    iterator = iter(iterable)
    while True:
        batch = list(islice(iterator, batch_size))
        if not batch:
            break
        yield batch


def compute_data_quality(custom_rules: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """
    Compute quality metrics based on distinct custom rule definitions.
    For each of the 'mandatory' and 'recommended' categories, count the number
    of rules flagged as valid. The overall weighted quality is calculated using
    a 70/30 weighting.
    """
    quality = {
        "mandatory": {
            "total_rules": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "valid_percentage": 0.0,
        },
        "recommended": {
            "total_rules": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "valid_percentage": 0.0,
        },
    }
    for importance in ["mandatory", "recommended"]:
        rules = custom_rules.get(importance, [])
        quality[importance]["total_rules"] = len(rules)
        for rule in rules:
            if rule.get("valid", True):
                quality[importance]["valid_count"] += 1
            else:
                quality[importance]["invalid_count"] += 1
        total = quality[importance]["total_rules"]
        if total > 0:
            quality[importance]["valid_percentage"] = round(
                (quality[importance]["valid_count"] / total) * 100, 1
            )
    weighted = 0.0
    if quality["mandatory"]["total_rules"] or quality["recommended"]["total_rules"]:
        weighted = (
            0.7 * quality["mandatory"]["valid_percentage"]
            + 0.3 * quality["recommended"]["valid_percentage"]
        )
    return {
        "mandatory": quality["mandatory"],
        "recommended": quality["recommended"],
        "total_weighted_quality": round(weighted, 1),
    }


# --- JSONReportStrategy with batched processing ---
class JSONReportStrategy:
    def __init__(self, batch_size: int = DEFAULT_BATCH_SIZE):
        self.batch_size = batch_size

    def generate_report(self, results_iterator: Iterator[ValidationResult]) -> dict[str, Any]:
        # Initialize accumulators
        summary_acc = {
            "total_files": 0,
            "valid_files": 0,
            "total_size": 0,
            "total_time": 0.0,
            "schema_version": None,
        }
        schema_acc = {}
        syntax_acc = {}
        encoding_acc = {}
        processing_acc = {}
        unknown_acc = {}
        custom_rules_acc = {}

        # Process results in batches from the iterator
        for batch in batch_iterator(results_iterator, self.batch_size):
            batch_summary = aggregate_summary_batch(batch)
            batch_schema = aggregate_schema_errors_batch(batch)
            batch_syntax = aggregate_syntax_errors_batch(batch)
            batch_encoding = aggregate_encoding_errors_batch(batch)
            batch_processing = aggregate_processing_errors_batch(batch)
            batch_unknown = aggregate_unknown_errors_batch(batch)
            batch_custom = aggregate_custom_rules_batch(batch)

            summary_acc = merge_summary(summary_acc, batch_summary)
            schema_acc = merge_schema_errors(schema_acc, batch_schema)
            syntax_acc = merge_syntax_errors(syntax_acc, batch_syntax)
            encoding_acc = merge_encoding_errors(encoding_acc, batch_encoding)
            processing_acc = merge_processing_errors(processing_acc, batch_processing)
            unknown_acc = merge_unknown_errors(unknown_acc, batch_unknown)
            custom_rules_acc = merge_custom_rules(custom_rules_acc, batch_custom)

        # Finalize custom rules only once and reuse the result.
        final_custom_rules = finalize_custom_rules(custom_rules_acc)

        summary = {
            "total_files": summary_acc["total_files"],
            "valid_files": summary_acc["valid_files"],
            "total_size": summary_acc["total_size"],
            "total_size_human": format_file_size(summary_acc["total_size"]),
            "total_time": summary_acc["total_time"],
            "total_time_human": format_time(summary_acc["total_time"]),
            "schema_version": summary_acc["schema_version"] or "Unknown",
            "data_quality": compute_data_quality(final_custom_rules),
        }

        schema_errors = finalize_schema_errors(schema_acc)
        syntax_errors = finalize_syntax_errors(syntax_acc)
        encoding_errors = finalize_encoding_errors(encoding_acc)
        processing_errors = finalize_processing_errors(processing_acc)
        unknown_errors = finalize_unknown_errors(unknown_acc)

        report = {
            "summary": summary,
            "validation_results": {
                "schema_validation": schema_errors,
                "syntax_errors": syntax_errors,
                "encoding_errors": encoding_errors,
                "processing_errors": processing_errors,
                "unknown_errors": unknown_errors,
                "custom_rules": final_custom_rules,
            },
        }
        return report


def get_report_strategy(format: str) -> JSONReportStrategy:
    if format != "json":
        raise ValueError("Only 'json' format is supported in the current implementation.")
    return JSONReportStrategy()


if __name__ == "__main__":
    # For testing purposes
    pass
