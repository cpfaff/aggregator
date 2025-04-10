#!/usr/bin/env python3

import re
import yaml
import logging
import datetime
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable, Tuple
from enum import Enum
from lxml import etree
from urllib.parse import urlparse, quote

#############################
# ENUMS AND DATA CLASSES
#############################

class Importance(Enum):
    MANDATORY = "mandatory"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"

@dataclass
class CustomRule:
    id: str
    name: str
    description: str
    type: str
    severity: str
    message: str
    paths: Optional[List[str]] = None
    pattern: Optional[str] = None
    function: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    importance: Importance = Importance.OPTIONAL
    field: Optional[Dict[str, Any]] = None
    fields: Optional[List[Dict[str, Any]]] = None

    def __post_init__(self):
        # Normalize the importance value.
        if isinstance(self.importance, str):
            self.importance = Importance(self.importance)
        # Normalize to always use 'fields'
        if self.field is not None:
            if self.fields is None:
                self.fields = [self.field]
            else:
                self.fields.insert(0, self.field)
        if self.fields is None:
            self.fields = []
        if self.paths is None:
            self.paths = []

@dataclass
class ValidationCount:
    total: int = 0
    missing: int = 0
    empty: int = 0
    invalid: int = 0
    valid: int = 0
    example_values: Dict[str, List[str]] = None

    def __post_init__(self):
        if self.example_values is None:
            self.example_values = {"valid": [], "invalid": []}

    def add_result(self, category: str, value: str = None):
        self.total += 1
        setattr(self, category, getattr(self, category) + 1)
        if value and category in ["valid", "invalid"]:
            examples = self.example_values[category]
            if len(examples) < 5 and value not in examples:
                examples.append(value)

    def get_summary(self) -> Dict[str, Any]:
        summary = {
            "total": self.total,
            "categories": {
                "missing": {"count": self.missing, "percentage": round((self.missing / self.total * 100), 1) if self.total > 0 else 0},
                "empty": {"count": self.empty, "percentage": round((self.empty / self.total * 100), 1) if self.total > 0 else 0},
                "invalid": {"count": self.invalid, "percentage": round((self.invalid / self.total * 100), 1) if self.total > 0 else 0},
                "valid": {"count": self.valid, "percentage": round((self.valid / self.total * 100), 1) if self.total > 0 else 0}
            },
            "example_values": self.example_values
        }
        return summary

#####################################
# CUSTOM RULE VALIDATOR
#####################################

class CustomRuleValidator:
    _DEFAULT_VERSION = "2.1"

    def __init__(self, rules_file: str, schema_version: str = None):
        self.rules_file = rules_file
        self._schema_version = schema_version or self._DEFAULT_VERSION
        self.rules = self._load_rules(rules_file)
        self._register_python_functions()

    @property
    def ABCD_URI(self) -> str:
        """Return the ABCD URI for the current schema version."""
        return f"http://www.tdwg.org/schemas/abcd/{self._schema_version}"

    def _load_rules(self, rules_file: str) -> List[CustomRule]:
        """Load rules from a YAML file and return a list of CustomRule objects."""
        with open(rules_file, 'r') as f:
            data = yaml.safe_load(f)
            if 'rules' not in data:
                raise ValueError("Rules file must contain a 'rules' key.")
            rules = [CustomRule(**rule) for rule in data['rules']]
            # Precompile any regex patterns defined in the rule
            for rule in rules:
                if rule.pattern:
                    try:
                        rule.pattern_compiled = re.compile(rule.pattern)
                    except re.error as e:
                        logging.error(f"Error compiling pattern for rule {rule.id}: {e}")
                        rule.pattern_compiled = None
            return rules

    def _register_python_functions(self):
        """Register custom Python validation functions."""
        self._python_validators = {
            'validate_coordinates': self._validate_coordinates,
            'url_format': self._validate_url,
            'text_encoding': self._validate_text_encoding
        }

    def _get_namespaces(self, xml_doc: etree._Element) -> Dict[str, str]:
        """Extract namespaces from the XML document using its root element."""
        root = xml_doc.getroottree().getroot()
        nsmap = dict(root.nsmap) if root.nsmap else {}
        if self.ABCD_URI not in nsmap.values():
            nsmap['abcd'] = self.ABCD_URI
        return nsmap

    def _adapt_xpath(self, path: str, nsmap: Dict[str, str]) -> str:
        """Adapt an XPath expression to handle namespaces correctly."""
        if None in nsmap:
            parts = [p for p in path.split('/') if p]
            adapted_parts = []
            for part in parts:
                if ':' in part or part.startswith('@') or part == '*' or part.startswith('*['):
                    adapted_parts.append(part)
                else:
                    adapted_parts.append(f"*[local-name()='{part}']")
            return ('/' if path.startswith('/') else '') + '/'.join(adapted_parts)
        return path

    def _convert_path_to_xpath(self, path: str) -> str:
        """Convert a simplified path to an XPath expression using local-name()."""
        parts = [p for p in path.split('/') if p]
        xpath_parts = [f"*[local-name()='{part}']" for part in parts]
        return '//' + '/'.join(xpath_parts)

    def _get_relative_xpath(self, full_xpath: str, parent_path: str) -> str:
        """
        Compute a relative XPath from the parent's path.
        If the full_xpath starts with the parent_path, remove that portion.
        """
        if full_xpath.startswith(parent_path):
            relative = full_xpath[len(parent_path):].lstrip('/')
        else:
            relative = full_xpath
        return '/'.join(f"*[local-name()='{part}']" for part in relative.split('/') if part)

    def _validate_with_validations(self, node: etree._Element, value: str, validations: List[Dict[str, Any]], result: dict) -> bool:
        """
        Run through validations defined for a field.
        Returns True if all validations pass.
        """
        for validation in validations:
            if validation['type'] == 'pattern':
                if 'compiled' not in validation:
                    try:
                        validation['compiled'] = re.compile(validation['value'])
                    except re.error as e:
                        logging.error(f"Error compiling regex in validation: {e}")
                        validation['compiled'] = None
                if validation['compiled'] and not validation['compiled'].match(value):
                    return False
            elif validation['type'] == 'url_format':
                if not self._python_validators['url_format'](node):
                    return False
            elif validation['type'] == 'text_encoding':
                errors = self._python_validators['text_encoding'](value, validation)
                if errors:
                    result['message'] = errors[0]['message']
                    return False
        return True

    def _validate_field_count(self, doc: etree._Element, field_def: Dict[str, Any], nsmap: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate a field that requires counting (using a parent_context).
        """
        result = {
            'valid': True,
            'message': None,
            'paths': []
        }
        counts = ValidationCount()
        xpath = field_def.get('xpath', field_def.get('path'))
        if not xpath:
            return result

        parent_path = field_def['parent_context']['parent']
        parent_xpath = '//' + '/'.join(f"*[local-name()='{part}']" for part in parent_path.split('/') if part)
        relative_xpath = self._get_relative_xpath(xpath, parent_path)
        parent_elements = doc.xpath(parent_xpath, namespaces=nsmap)

        for parent in parent_elements:
            children = parent.xpath(relative_xpath, namespaces=nsmap)
            if not children:
                counts.add_result('missing')
                counts_example_path = parent.getroottree().getpath(parent)
                result['paths'].append(counts_example_path)
            else:
                for child in children:
                    value = child.text.strip() if child.text else ''
                    if not value:
                        counts.add_result('empty')
                        result['paths'].append(parent.getroottree().getpath(parent))
                    elif 'validation' in field_def:
                        if self._validate_with_validations(child, value, field_def['validation'], result):
                            counts.add_result('valid', value)
                        else:
                            counts.add_result('invalid', value)
                    else:
                        counts.add_result('valid', value)
        result['counts'] = counts.get_summary()
        result['context_name'] = parent_path.split('/')[-1]
        if counts.total > 0 and (counts.missing > 0 or counts.empty > 0 or counts.invalid > 0):
            result['valid'] = False
        return result

    def _validate_field_presence(self, doc: etree._Element, field_def: Dict[str, Any], nsmap: Dict[str, str]) -> Dict[str, Any]:
        """
        Perform a simple presence validation on a field.
        """
        result = {
            'valid': True,
            'paths': [],
            'example_values': []
        }
        xpath = field_def.get('xpath', field_def.get('path'))
        if not xpath:
            return result

        xpath_parts = [f"*[local-name()='{part}']" for part in xpath.split('/') if part]
        adapted_xpath = '//' + '/'.join(xpath_parts)
        matches = doc.xpath(adapted_xpath, namespaces=nsmap)
        if matches:
            examples = []
            for match in matches[:5]:
                value = match.text.strip() if match.text else ''
                if value:
                    examples.append(('valid', value))
            if examples:
                result['example_values'] = examples
        else:
            result['valid'] = False
            result['paths'].append(xpath)
        return result

    def _validate_field(self, doc: etree._Element, field_def: Dict[str, Any], nsmap: Dict[str, str]) -> Dict[str, Any]:
        """
        Decide which validation branch to use based on the field definition.
        """
        if 'parent_context' in field_def:
            return self._validate_field_count(doc, field_def, nsmap)
        else:
            return self._validate_field_presence(doc, field_def, nsmap)

    def validate_document(self, doc: etree._Element) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Validate an XML document against custom rules.
        Returns a list of rule results and a dictionary of calculated scores.
        """
        results = []
        nsmap = self._get_namespaces(doc)
        # If a default namespace is present with a None key, assign it a prefix.
        if None in nsmap:
            nsmap['default'] = nsmap.pop(None)

        # Dictionary to track rule results for scoring.
        rule_results = {}
        for rule in self.rules:
            try:
                passed = True
                example_values = []
                field_results = []
                if rule.fields:
                    for field in rule.fields:
                        res = self._validate_field(doc, field, nsmap)
                        field_results.append(res)
                        if not res.get('valid', True):
                            passed = False
                        if 'example_values' in res:
                            example_values.extend(res['example_values'])
                rule_id = (rule.id, rule.importance.value)
                if rule_id not in rule_results:
                    rule_results[rule_id] = {'total': 1, 'passed': 0}
                if passed:
                    rule_results[rule_id]['passed'] = 1

                rule_result = {
                    'rule': rule.id,
                    'name': rule.name,
                    'description': rule.description,
                    'importance': rule.importance.value,
                    'severity': rule.severity,
                    'valid': passed,
                    'path': None,
                    'message': rule.message if not passed else None,
                    'example_values': example_values[:5]
                }
                if rule.fields:
                    paths = [field.get('path') for field in rule.fields if field.get('path')]
                    if paths:
                        rule_result['path'] = ', '.join(paths)
                    # Merge counting information if available from any field.
                    for res in field_results:
                        if 'counts' in res:
                            rule_result.update({
                                'counts': res['counts'],
                                'context_name': res.get('context_name')
                            })
                            if res['counts']['total'] > 0:
                                valid_count = res['counts']['categories']['valid']['count']
                                rule_result['valid'] = valid_count == res['counts']['total']
                            break
                results.append(rule_result)
            except Exception as e:
                logging.exception("Error processing rule: %s", rule.id)
                results.append({
                    'rule': rule.id,
                    'name': rule.name,
                    'description': rule.description,
                    'importance': rule.importance.value,
                    'severity': rule.severity,
                    'valid': False,
                    'message': f"Error executing rule: {str(e)}"
                })
                rule_id = (rule.id, rule.importance.value)
                if rule_id not in rule_results:
                    rule_results[rule_id] = {'total': 1, 'passed': 0}
        return results, self._calculate_scores(rule_results)

    def _calculate_scores(self, rule_results: Dict[Any, Dict[str, int]]) -> Dict[str, Any]:
        """Calculate and return scores for mandatory and recommended rules."""
        scores = {
            'mandatory': {'passed': 0, 'total': 0},
            'recommended': {'passed': 0, 'total': 0}
        }
        for (rule_id, importance), result in rule_results.items():
            if importance in ['mandatory', 'recommended']:
                scores[importance]['total'] += 1
                if result['passed'] > 0:
                    scores[importance]['passed'] += 1
        return {
            'mandatory': scores['mandatory'],
            'recommended': scores['recommended']
        }

    def _validate_coordinates(self, node: etree._Element, config: Dict[str, Any]) -> bool:
        """
        Validate geographic coordinates using the ABCD namespace.
        """
        nsmap = self._get_namespaces(node)
        abcd_prefix = next((prefix for prefix, uri in nsmap.items() if uri == self.ABCD_URI), 'abcd')
        lat_path = f'.//{abcd_prefix}:CoordinatesLatitude/text()'
        long_path = f'.//{abcd_prefix}:CoordinatesLongitude/text()'
        lat_nodes = node.xpath(lat_path, namespaces=nsmap)
        long_nodes = node.xpath(long_path, namespaces=nsmap)
        if not lat_nodes or not long_nodes:
            return False
        try:
            lat = float(lat_nodes[0])
            long = float(long_nodes[0])
            if (lat < config['lat_min'] or lat > config['lat_max'] or
                long < config['long_min'] or long > config['long_max']):
                return False
        except (ValueError, IndexError):
            return False
        return True

    def _validate_url(self, node: etree._Element, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate whether the text content of a node is a properly formatted URL.
        """
        if node is None or not node.text:
            return False
        url = node.text.strip()
        try:
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                return False
            if parsed.scheme not in ('http', 'https'):
                return False
            domain_parts = parsed.netloc.split('.')
            if len(domain_parts) < 2:
                return False
            for part in domain_parts:
                if not part or part.startswith('-') or part.endswith('-'):
                    return False
                if not all(c.isalnum() or c == '-' for c in part):
                    return False
            path = parsed.path
            if path:
                try:
                    quote(path, safe='/:@-._~!$&\'()*+,;=')
                except Exception:
                    return False
            return True
        except Exception:
            return False

    def _validate_text_encoding(self, value: str, rule_def: dict) -> List[Dict[str, Any]]:
        """
        Validate that the text content is properly UTF-8 encoded and check for problematic characters.
        """
        errors = []
        if not value or not isinstance(value, str):
            return errors
        try:
            value.encode('utf-8')
            problematic_chars = {
                'windows_quotes': ('"', '"'),
                'windows_apostrophe': ("'", "'"),
                'control_chars': [chr(i) for i in range(32) if i not in (9, 10, 13)],
                'zero_width': '\u200b\u200c\u200d\ufeff',
                'non_breaking_space': '\u00A0',
            }
            for char_type, chars in problematic_chars.items():
                if isinstance(chars, (list, str)):
                    chars = tuple(chars)
                for char in chars:
                    if char in value:
                        pos = value.index(char)
                        context = value[max(0, pos-20):min(len(value), pos+20)]
                        errors.append({
                            'message': f"Found problematic character ({char_type}) at position {pos}. Context: ...{context}...",
                            'line': None,
                            'column': None,
                            'path': None,
                            'error_type': "text_encoding",
                            'severity': "warning"
                        })
        except UnicodeEncodeError as e:
            pos = e.start
            context = value[max(0, pos-20):min(len(value), pos+20)]
            errors.append({
                'message': f"Invalid UTF-8 character at position {pos}. Context: ...{context}...",
                'line': None,
                'column': None,
                'path': None,
                'error_type': "text_encoding",
                'severity': "error"
            })
        return errors

    def merge_rules(self, default_rules, custom_rules):
        """Merge custom rules into default rules by updating child categories automatically."""
        merged = default_rules.copy()
        for key, value in custom_rules.items():
            if isinstance(value, dict):
                if key in merged and isinstance(merged[key], dict):
                    merged[key].update(value)
                else:
                    merged[key] = value
            else:
                merged[key] = value
        return merged

    def load_custom_rules(self, custom_file_path, default_rules):
        """Load custom rules from a file and merge them with default rules."""
        try:
            with open(custom_file_path, 'r') as f:
                custom_rules = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file {custom_file_path}: {e}")
            raise
        if custom_rules:
            merged_rules = self.merge_rules(default_rules, custom_rules)
        else:
            merged_rules = default_rules
        return merged_rules
