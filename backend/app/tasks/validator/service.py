"""
Service layer for XML validation operations.
Provides an interface to the ABCD Validator library.
"""

import logging
import os
import shutil
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

from abcd_validator import ABCDValidator, JSONReportStrategy, ValidationResult, download_archive

logger = logging.getLogger(__name__)


class ValidatorService:
    """
    Service for handling XML validation operations.
    Provides a clean interface to the ABCD Validator library.
    """

    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize the validator service.

        Args:
            temp_dir: Directory to store temporary files (e.g., downloaded archives)
                      If None, a system temporary directory will be used
        """
        if temp_dir:
            self.temp_dir = temp_dir
            os.makedirs(temp_dir, exist_ok=True)
        else:
            # Use a system temp directory
            self.temp_dir = tempfile.gettempdir()

        logger.info(f"ValidatorService initialized with temp_dir: {self.temp_dir}")

    def download_archive(self, url: str) -> str:
        """
        Download an archive from a URL.

        Args:
            url: URL of the archive to download

        Returns:
            Path to the downloaded archive
        """
        logger.info(f"Downloading archive from {url}")
        try:
            # First download to default location
            archive_path = download_archive(url)

            # If temp_dir is specified, move the file there
            if self.temp_dir:
                filename = os.path.basename(archive_path)
                new_path = os.path.join(self.temp_dir, filename)
                shutil.move(archive_path, new_path)
                archive_path = new_path

            logger.info(f"Archive downloaded successfully to {archive_path}")
            return archive_path
        except Exception as e:
            logger.error(f"Failed to download archive from {url}: {e}")
            raise

    def validate_archive(
        self, archive_url: str, archive_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate an XML archive either from a URL or local path.

        Args:
            archive_url: URL of the archive (used if archive_path is not provided)
            archive_path: Optional path to a local archive file

        Returns:
            Complete validation report with summary and detailed results
        """
        logger.info(f"Starting validation for archive: {archive_url}")
        validator = ABCDValidator()

        # Download archive if needed (or use local path)
        local_path = archive_path
        if not local_path or not os.path.exists(local_path):
            logger.info(f"No valid local path provided, downloading from {archive_url}")
            local_path = self.download_archive(archive_url)

        # Process the archive
        start_time = datetime.now()
        logger.info(f"Validating archive at {local_path}")

        try:
            # Process the archive and collect results
            results = list(validator.process_archive(local_path))

            # Generate the aggregated report
            report_strategy = JSONReportStrategy()
            final_report = report_strategy.generate_report(results)

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Validation completed in {duration:.2f} seconds")

            return final_report
        except Exception as e:
            logger.error(f"Error during validation: {e}")
            raise
