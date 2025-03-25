#!/usr/bin/env python3
import argparse
import atexit
import json
import logging
import multiprocessing as mp
import os
import re
import sys
import time
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union, Tuple

import psutil
import requests
from lxml import etree
from collections import defaultdict
import glob
from concurrent.futures import ProcessPoolExecutor, as_completed
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from itertools import islice

from .custom_rules import CustomRuleValidator
from .models import ValidationError, ValidationResult
from .reporting import (
    get_report_strategy, format_file_size,
    aggregate_summary_batch, merge_summary,
    aggregate_schema_errors_batch, merge_schema_errors, finalize_schema_errors,
    aggregate_syntax_errors_batch, merge_syntax_errors, finalize_syntax_errors,
    aggregate_encoding_errors_batch, merge_encoding_errors, finalize_encoding_errors,
    aggregate_processing_errors_batch, merge_processing_errors, finalize_processing_errors,
    aggregate_unknown_errors_batch, merge_unknown_errors, finalize_unknown_errors,
    aggregate_custom_rules_batch, merge_custom_rules, finalize_custom_rules,
)

# Precompile regex for encoding detection
ENCODING_REGEX = re.compile(r'encoding=["\']([^"\']+)["\']', re.IGNORECASE)

# Default batch size
DEFAULT_BATCH_SIZE = 100

# Global variables for worker processes
WORKER_SCHEMA = None
WORKER_SCHEMA_PATH = None
WORKER_RULES_FILE = None
WORKER_CUSTOM_VALIDATOR = None
WORKER_SCHEMA_VERSION = None

# Temporary file tracking
_TEMP_FILE_PATH = None
_DOWNLOADED_TEMP_FILE = False

def _cleanup_temp_file():
    global _TEMP_FILE_PATH, _DOWNLOADED_TEMP_FILE
    if _DOWNLOADED_TEMP_FILE and _TEMP_FILE_PATH and os.path.exists(_TEMP_FILE_PATH):
        try:
            os.remove(_TEMP_FILE_PATH)
            logging.info(f"Temporary file {_TEMP_FILE_PATH} removed successfully.")
        except Exception as e:
            logging.error(f"Failed to remove temporary file {_TEMP_FILE_PATH}: {e}")

atexit.register(_cleanup_temp_file)

def worker_init(schema_path: str, rules_file: str):
    global WORKER_SCHEMA, WORKER_SCHEMA_PATH, WORKER_RULES_FILE, WORKER_CUSTOM_VALIDATOR, WORKER_SCHEMA_VERSION
    WORKER_SCHEMA_PATH = schema_path
    WORKER_RULES_FILE = rules_file
    if schema_path:
        try:
            xmlschema_doc = etree.parse(schema_path)
            WORKER_SCHEMA = etree.XMLSchema(xmlschema_doc)
            logging.info(f"Worker {os.getpid()}: Loaded schema from {schema_path}")
            m = re.search(r'abcd([\d\.]+)\.xsd$', os.path.basename(schema_path))
            WORKER_SCHEMA_VERSION = m.group(1) if m else "Unknown"
            logging.info(f"Worker {os.getpid()}: Schema version set to {WORKER_SCHEMA_VERSION}")
        except Exception as e:
            logging.error(f"Worker {os.getpid()}: Failed to load schema {schema_path}: {e}")
            WORKER_SCHEMA = None
            WORKER_SCHEMA_VERSION = None
    else:
        logging.warning(f"Worker {os.getpid()}: No schema path provided")
        WORKER_SCHEMA = None
        WORKER_SCHEMA_VERSION = None
    try:
        WORKER_CUSTOM_VALIDATOR = CustomRuleValidator(rules_file)
        logging.info(f"Worker {os.getpid()}: Loaded custom rules from {rules_file}")
    except Exception as e:
        logging.error(f"Worker {os.getpid()}: Failed to load custom rules {rules_file}: {e}")
        WORKER_CUSTOM_VALIDATOR = None

def worker_validate(task: Union[str, Tuple[str, str]]) -> ValidationResult:
    if isinstance(task, str):
        filename = os.path.basename(task)
        try:
            with open(task, 'rb') as f:
                content = f.read()
        except Exception as e:
            return ValidationResult(
                file_name=filename, file_size=0, schema_valid=False, validation_time=0,
                errors=[ValidationError(message=f"Failed to read file: {e}", error_type="processing", severity="error")],
                custom_rule_results=[]
            )
    elif isinstance(task, tuple):
        zip_path, internal_file = task
        filename = internal_file
        try:
            with zipfile.ZipFile(zip_path) as zf:
                with zf.open(internal_file) as f:
                    content = f.read()
        except Exception as e:
            return ValidationResult(
                file_name=filename, file_size=0, schema_valid=False, validation_time=0,
                errors=[ValidationError(message=f"Failed to read from ZIP: {e}", error_type="processing", severity="error")],
                custom_rule_results=[]
            )
    else:
        raise ValueError("Invalid task type")
    return ABCDValidator._validate_single_file_static(content, filename, WORKER_SCHEMA_PATH, WORKER_RULES_FILE)

class ProgressDisplay:
    def __init__(self, show_progress: bool = False):
        self.show_progress = show_progress
        self.start_time = time.time()
        self.download_start_time = None
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.processed_files = 0
        self.total_files = 0

    def update_download(self, downloaded: int, total: int):
        if not self.show_progress:
            return
        if self.download_start_time is None:
            self.download_start_time = time.time()
        self.downloaded_bytes = downloaded
        self.total_bytes = total
        elapsed = time.time() - self.download_start_time
        speed = downloaded / elapsed if elapsed > 0 else 0
        eta = (total - downloaded) / speed if speed > 0 else 0
        percent = (downloaded / total) * 100 if total > 0 else 0
        print(f"\rDownloading: {percent:.1f}% ({downloaded}/{total} bytes) - ETA: {eta:.1f}s", end='', flush=True)

    def update_processing(self, processed: int, total: int):
        if not self.show_progress:
            return
        self.processed_files = processed
        self.total_files = total
        elapsed = time.time() - self.start_time
        speed = processed / elapsed if elapsed > 0 else 0
        eta = (total - processed) / speed if speed > 0 else 0
        percent = (processed / total) * 100 if total > 0 else 0
        print(f"\rProcessing: {percent:.1f}% ({processed}/{total} files) - ETA: {eta:.1f}s", end='', flush=True)

    def finish_download(self):
        if self.show_progress:
            print(f"\nDownload complete: {self.total_bytes} bytes", flush=True)

    def finish_processing(self):
        if self.show_progress:
            print(f"\nProcessing complete: {self.total_files} files", flush=True)

class ABCDValidator:
    SCHEMA_MAPPING = {
        "http://www.tdwg.org/schemas/abcd/2.06": "abcd2.06.xsd",
        "http://rs.tdwg.org/abcd/2.06": "abcd2.06.xsd",
        "http://rs.tdwg.org/abcd/2.06/ABCD_2.06.xsd": "abcd2.06.xsd",
        "http://www.tdwg.org/schemas/abcd/2.06b": "abcd2.06b.xsd",
        "http://rs.tdwg.org/abcd/2.06b": "abcd2.06b.xsd",
        "http://rs.tdwg.org/abcd/2.06b/ABCD_2.06b.xsd": "abcd2.06b.xsd",
        "http://www.tdwg.org/schemas/abcd/2.06d": "abcd2.06d.xsd",
        "http://rs.tdwg.org/abcd/2.06d": "abcd2.06d.xsd",
        "http://rs.tdwg.org/abcd/2.06d/ABCD_2.06d.xsd": "abcd2.06d.xsd",
        "http://www.tdwg.org/schemas/abcd/2.06e": "abcd2.06e.xsd",
        "http://rs.tdwg.org/abcd/2.06e": "abcd2.06e.xsd",
        "http://rs.tdwg.org/abcd/2.06e/ABCD_2.06e.xsd": "abcd2.06e.xsd",
        "http://www.tdwg.org/schemas/abcd/2.06f": "abcd2.06f.xsd",
        "http://rs.tdwg.org/abcd/2.06f": "abcd2.06f.xsd",
        "http://rs.tdwg.org/abcd/2.06f/ABCD_2.06f.xsd": "abcd2.06f.xsd",
        "http://www.tdwg.org/schemas/abcd/2.1": "abcd2.1.xsd",
        "http://rs.tdwg.org/abcd/2.1": "abcd2.1.xsd",
        "http://rs.tdwg.org/abcd/2.1/ABCD_2.1.xsd": "abcd2.1.xsd",
        "http://www.tdwg.org/schemas/abcd/3.0": "abcd3.0.xsd",
        "http://rs.tdwg.org/abcd/3.0": "abcd3.0.xsd",
        "http://rs.tdwg.org/abcd/3.0/ABCD_3.0.xsd": "abcd3.0.xsd"
    }
    DEFAULT_RULES_FILE = os.path.join(os.path.dirname(__file__), "rules", "default_rules.yaml")

    def __init__(self, schema_path: str = None, rules_file: Optional[str] = None):
        self.schema_path = schema_path
        self.schema = None
        self._detected_version = None
        self.rules_file = rules_file or self.DEFAULT_RULES_FILE
        try:
            self.custom_validator = CustomRuleValidator(self.rules_file)
        except Exception as e:
            logging.error(f"Failed to initialize custom validator with {self.rules_file}: {e}")
            self.custom_validator = None

    def prepare_schema(self, xml_content: bytes) -> None:
        if self.schema_path is None:
            try:
                tree = etree.fromstring(xml_content)
                schema_file = self._detect_schema_version(etree.ElementTree(tree))
                if schema_file:
                    self.schema_path = os.path.join(os.path.dirname(__file__), "schemas", schema_file)
                    logging.info(f"Detected and set schema path to {self.schema_path}")
            except Exception as e:
                logging.warning(f"Schema detection failed: {e}")

    def _detect_schema_version(self, tree: etree.ElementTree) -> Optional[str]:
        try:
            root = tree.getroot()
            nsmap = root.nsmap
            for uri in nsmap.values():
                if 'tdwg.org/schemas/abcd' in uri:
                    version = uri.split('/')[-1]
                    schema_file = f"abcd{version}.xsd"
                    logging.info(f"Detected schema version: {version} -> {schema_file}")
                    self._detected_version = version
                    return schema_file
            logging.warning("No ABCD schema version found in XML")
            return None
        except Exception as e:
            logging.warning(f"Could not detect schema version: {e}")
            return None

    def _load_schema(self):
        if not self.schema_path or not os.path.exists(self.schema_path):
            raise Exception(f"Schema file not found: {self.schema_path}")
        try:
            xmlschema_doc = etree.parse(self.schema_path)
            self.schema = etree.XMLSchema(xmlschema_doc)
            logging.info(f"Loaded schema from {self.schema_path}")
        except Exception as e:
            raise Exception(f"Failed to load schema: {e}")

    @staticmethod
    def _validate_encoding(xml_content: bytes) -> Tuple[bool, Optional[str]]:
        try:
            decoded = xml_content.decode('utf-8')
            if '<?xml' in decoded[:100]:
                encoding_match = ENCODING_REGEX.search(decoded[:100])
                if encoding_match and encoding_match.group(1).lower() != 'utf-8':
                    return False, f"XML declares encoding as {encoding_match.group(1)} but should be UTF-8"
            return True, None
        except UnicodeDecodeError as e:
            pos = e.start
            context = xml_content[max(0, pos-20):min(len(xml_content), pos+20)].decode('utf-8', errors='replace')
            return False, f"Invalid UTF-8 encoding at position {pos}. Context: ...{context}..."

    @staticmethod
    def _validate_single_file_static(xml_content: bytes, filename: str, schema_path: str = None, rules_file: Optional[str] = None) -> ValidationResult:
        validator = ABCDValidator.__new__(ABCDValidator)
        validator.schema = WORKER_SCHEMA
        validator.schema_path = schema_path or WORKER_SCHEMA_PATH
        validator.custom_validator = WORKER_CUSTOM_VALIDATOR
        start_time = time.time()
        errors = []
        custom_results = []
        file_size = len(xml_content)

        # Encoding validation
        is_valid_utf8, encoding_error = ABCDValidator._validate_encoding(xml_content)
        if not is_valid_utf8:
            return ValidationResult(
                file_name=filename, file_size=file_size, schema_valid=False, validation_time=time.time() - start_time,
                errors=[ValidationError(message=f"Encoding error: {encoding_error}", error_type="encoding", severity="error")],
                custom_rule_results=[]
            )

        # Parse XML and validate
        try:
            doc = etree.fromstring(xml_content)
        except etree.XMLSyntaxError as e:
            return ValidationResult(
                file_name=filename, file_size=file_size, schema_valid=False, validation_time=time.time() - start_time,
                errors=[ValidationError(message=str(e), line=e.lineno, column=e.offset, error_type="syntax", severity="error")],
                custom_rule_results=[]
            )
        except Exception as e:
            return ValidationResult(
                file_name=filename, file_size=file_size, schema_valid=False, validation_time=time.time() - start_time,
                errors=[ValidationError(message=f"Unexpected error during parsing: {e}", error_type="unknown", severity="error")],
                custom_rule_results=[]
            )

        # Schema validation
        schema_valid = True
        if validator.schema is None and validator.schema_path:
            try:
                validator._load_schema()
            except Exception as e:
                errors.append(ValidationError(message=f"Schema loading failed: {e}", error_type="processing", severity="error"))
                schema_valid = False
        if validator.schema:
            try:
                schema_valid = validator.schema.validate(doc)
                if not schema_valid:
                    for error in validator.schema.error_log:
                        path = error.path or (etree.ElementTree(doc).getpath(error.node) if hasattr(error, 'node') and error.node is not None else None)
                        errors.append(ValidationError(
                            message=error.message, line=error.line, column=error.column, path=path,
                            error_type="schema", severity="error",
                            domain_name=getattr(error, 'domain_name', None),
                            type_name=getattr(error, 'type_name', None),
                            level=getattr(error, 'level', None)
                        ))
            except Exception as e:
                errors.append(ValidationError(message=f"Schema validation error: {e}", error_type="unknown", severity="error"))
                schema_valid = False

        # Custom rules validation
        if validator.custom_validator:
            try:
                custom_results, _ = validator.custom_validator.validate_document(doc)
            except Exception as e:
                errors.append(ValidationError(message=f"Custom rules validation failed: {e}", error_type="unknown", severity="error"))

        return ValidationResult(
            file_name=filename, file_size=file_size, schema_valid=schema_valid,
            validation_time=time.time() - start_time, errors=errors, custom_rule_results=custom_results,
            schema_version=WORKER_SCHEMA_VERSION or validator._detected_version
        )

    def process_archive(self, archive_path: Union[str, Path], progress: ProgressDisplay = None, batch_size: int = DEFAULT_BATCH_SIZE, workers: int = mp.cpu_count()) -> Iterator[ValidationResult]:
        global_validated = 0
        with zipfile.ZipFile(archive_path) as zf:
            xml_files = sorted(f for f in zf.namelist() if f.lower().endswith('.xml'))
            total_files = len(xml_files)
            logging.info(f"Found {total_files} XML files in archive {archive_path}")
            if progress:
                progress.total_files = total_files

            if self.schema_path is None and xml_files:
                try:
                    with zf.open(xml_files[0]) as f:
                        self.prepare_schema(f.read())
                except Exception as e:
                    logging.warning(f"Schema pre-detection failed for {archive_path}: {e}")

            with ProcessPoolExecutor(max_workers=workers, initializer=worker_init, initargs=(self.schema_path, self.rules_file)) as executor:
                for batch in batch_iterator(xml_files, batch_size):
                    tasks = [(archive_path, xml_file) for xml_file in batch]
                    futures = {executor.submit(worker_validate, task): task for task in tasks}
                    for future in as_completed(futures):
                        try:
                            result = future.result()
                            global_validated += 1
                            if progress:
                                progress.update_processing(global_validated, total_files)
                            yield result
                        except Exception as e:
                            task = futures[future]
                            logging.error(f"Error validating {task[1]} in {archive_path}: {e}")
                            yield ValidationResult(
                                file_name=task[1], file_size=0, schema_valid=False, validation_time=0,
                                errors=[ValidationError(message=f"Processing error: {e}", error_type="processing", severity="error")],
                                custom_rule_results=[]
                            )
                if progress:
                    progress.finish_processing()

    def process_files(self, file_paths: List[str], progress: ProgressDisplay = None, batch_size: int = DEFAULT_BATCH_SIZE, workers: int = mp.cpu_count()) -> Iterator[ValidationResult]:
        total_files = len(file_paths)
        logging.info(f"Processing {total_files} XML files")
        if progress:
            progress.total_files = total_files

        if self.schema_path is None and file_paths:
            try:
                with open(file_paths[0], 'rb') as f:
                    self.prepare_schema(f.read())
            except Exception as e:
                logging.warning(f"Schema pre-detection failed for {file_paths[0]}: {e}")

        with ProcessPoolExecutor(max_workers=workers, initializer=worker_init, initargs=(self.schema_path, self.rules_file)) as executor:
            for batch in batch_iterator(file_paths, batch_size):
                futures = {executor.submit(worker_validate, task): task for task in batch}
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if progress:
                            progress.update_processing(progress.processed_files + 1, total_files)
                        yield result
                    except Exception as e:
                        file_path = futures[future]
                        logging.error(f"Error validating {file_path}: {e}")
                        yield ValidationResult(
                            file_name=file_path, file_size=0, schema_valid=False, validation_time=0,
                            errors=[ValidationError(message=f"Processing error: {e}", error_type="processing", severity="error")],
                            custom_rule_results=[]
                        )
            if progress:
                progress.finish_processing()

def batch_iterator(iterable, batch_size: int):
    iterator = iter(iterable)
    while True:
        batch = list(islice(iterator, batch_size))
        if not batch:
            break
        yield batch

def validate_archive(archive_path: str, schema_path: Optional[str] = None, rules_file: Optional[str] = None, progress: ProgressDisplay = None, file_batch_size: int = DEFAULT_BATCH_SIZE, workers: int = mp.cpu_count()) -> Iterator[ValidationResult]:
    validator = ABCDValidator(schema_path=schema_path, rules_file=rules_file)
    if os.path.isdir(archive_path):
        xml_files = [os.path.join(root, f) for root, _, files in os.walk(archive_path) for f in files if f.lower().endswith('.xml')]
        return validator.process_files(xml_files, progress=progress, batch_size=file_batch_size, workers=workers)
    elif archive_path.lower().endswith('.zip'):
        return validator.process_archive(archive_path, progress=progress, batch_size=file_batch_size, workers=workers)
    elif archive_path.lower().endswith('.xml'):
        xml_files = glob.glob(archive_path) if ('*' in archive_path or '?' in archive_path) else [archive_path]
        return validator.process_files(xml_files, progress=progress, batch_size=file_batch_size, workers=workers)
    else:
        raise ValueError("Input must be a ZIP archive, XML file(s), or directory")

def download_archive(url: str, progress: ProgressDisplay = None, timeout: float = 30.0, retries: int = 5, backoff: float = 0.5) -> str:
    session = requests.Session()
    retry_strategy = Retry(total=retries, backoff_factor=backoff, status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retry_strategy))
    session.mount('https://', HTTPAdapter(max_retries=retry_strategy))
    filename = os.path.basename(urlparse(url).path) or "downloaded_archive.zip"
    temp_path = os.path.join(tempfile.gettempdir(), filename)

    try:
        response = session.get(url, stream=True, timeout=timeout)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        if progress:
            progress.total_bytes = total_size
        downloaded = 0
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress:
                        progress.update_download(downloaded, total_size)
        if progress:
            progress.finish_download()
        logging.info(f"Downloaded {url} to {temp_path}")
        return temp_path
    except requests.RequestException as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise Exception(f"Failed to download {url}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Validate ABCD XML files')
    parser.add_argument('input', help='Path to ABCD archive or URL')
    parser.add_argument('--schema', help='Path to custom schema file')
    parser.add_argument('--rules', help='Path to custom rules file')
    parser.add_argument('--format', choices=['text', 'json'], default='json', help='Output format')
    parser.add_argument('--progress', action='store_true', help='Show progress display')
    parser.add_argument('--batch-files', type=int, default=100, help='Batch size for file processing tasks')
    parser.add_argument('--batch-aggregate', type=int, default=50, help='Batch size for aggregator updates')
    parser.add_argument('--batch-report', type=int, default=100, help='Batch size for report generation')
    # New parameters
    parser.add_argument('--download-timeout', type=float, default=30.0, help='Timeout for URL downloads in seconds')
    parser.add_argument('--download-retries', type=int, default=5, help='Number of download retries')
    parser.add_argument('--download-backoff', type=float, default=0.5, help='Backoff factor for download retries')
    parser.add_argument('--workers', type=int, default=mp.cpu_count(), help='Number of worker processes')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help='Logging level')
    parser.add_argument('--memory-limit', type=int, help='Memory limit in MB to auto-tune batch sizes')
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=getattr(logging, args.log_level), format='%(asctime)s - %(levelname)s - %(message)s')

    # Adjust batch sizes based on memory limit
    batch_files = args.batch_files
    batch_report = args.batch_report
    if args.memory_limit:
        available_mb = psutil.virtual_memory().available / (1024 * 1024)
        batch_factor = min(1.0, args.memory_limit / available_mb) if available_mb > 0 else 1.0
        batch_files = max(1, int(args.batch_files * batch_factor))
        batch_report = max(1, int(args.batch_report * batch_factor))
        logging.info(f"Adjusted batch-files to {batch_files}, batch-report to {batch_report} based on memory limit {args.memory_limit}MB")

    progress = ProgressDisplay(args.progress and sys.stdout.isatty())
    if args.progress and not progress.show_progress:
        logging.warning("Progress display disabled when output is not a terminal")

    archive_path = None
    downloaded_temp_file = False
    try:
        if args.input.startswith(('http://', 'https://')):
            archive_path = download_archive(
                args.input, progress, args.download_timeout, args.download_retries, args.download_backoff
            )
            downloaded_temp_file = True
            global _TEMP_FILE_PATH, _DOWNLOADED_TEMP_FILE
            _TEMP_FILE_PATH = archive_path
            _DOWNLOADED_TEMP_FILE = True
        else:
            archive_path = args.input

        results_generator = validate_archive(
            archive_path, schema_path=args.schema, rules_file=args.rules, progress=progress,
            file_batch_size=batch_files, workers=args.workers
        )
        report_strategy = get_report_strategy(args.format)
        report_strategy.batch_size = batch_report
        logging.info("Generating report...")
        report = report_strategy.generate_report(results_generator)
        if progress:
            progress.finish_processing()

        print(json.dumps(report, indent=4) if args.format == 'json' else report)

    except KeyboardInterrupt:
        print("\nValidation interrupted by user", file=sys.stderr)
        sys.exit(1)
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if downloaded_temp_file and archive_path and os.path.exists(archive_path):
            try:
                os.remove(archive_path)
                logging.info(f"Temporary file {archive_path} removed.")
            except Exception as e:
                logging.error(f"Failed to remove temporary file {archive_path}: {e}")

if __name__ == '__main__':
    main()
