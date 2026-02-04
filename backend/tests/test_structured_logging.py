"""Tests for structured logging configuration and request ID propagation."""

import json
import logging
import uuid

from app.core.logging_config import RequestIdFilter, configure_logging, request_id_var


class TestConfigureLogging:
    """Tests for the configure_logging function."""

    def test_log_output_is_json(self, capfd):
        """Test that log output is valid JSON format."""
        configure_logging(level="INFO")
        test_logger = logging.getLogger("test.json_format")
        test_logger.info("test message")

        captured = capfd.readouterr()
        # At least one line should be parseable JSON
        for line in captured.err.strip().split("\n"):
            if line.strip():
                data = json.loads(line)
                assert "message" in data

    def test_log_includes_level(self, capfd):
        """Test that log output includes the log level."""
        configure_logging(level="INFO")
        test_logger = logging.getLogger("test.level")
        test_logger.warning("level test")

        captured = capfd.readouterr()
        for line in captured.err.strip().split("\n"):
            if line.strip():
                data = json.loads(line)
                if data.get("message") == "level test":
                    assert data.get("level") == "WARNING"

    def test_log_includes_timestamp(self, capfd):
        """Test that log output includes a timestamp."""
        configure_logging(level="INFO")
        test_logger = logging.getLogger("test.timestamp")
        test_logger.info("timestamp test")

        captured = capfd.readouterr()
        for line in captured.err.strip().split("\n"):
            if line.strip():
                data = json.loads(line)
                if data.get("message") == "timestamp test":
                    assert "timestamp" in data

    def test_log_includes_logger_name(self, capfd):
        """Test that log output includes the logger name."""
        configure_logging(level="INFO")
        test_logger = logging.getLogger("test.logger_name")
        test_logger.info("name test")

        captured = capfd.readouterr()
        for line in captured.err.strip().split("\n"):
            if line.strip():
                data = json.loads(line)
                if data.get("message") == "name test":
                    assert data.get("name") == "test.logger_name"


class TestRequestIdFilter:
    """Tests for request ID injection into log records."""

    def test_request_id_included_when_set(self, capfd):
        """Test that request_id appears in logs when set in contextvars."""
        configure_logging(level="INFO")
        test_id = str(uuid.uuid4())
        token = request_id_var.set(test_id)
        try:
            test_logger = logging.getLogger("test.request_id")
            test_logger.info("request id test")

            captured = capfd.readouterr()
            for line in captured.err.strip().split("\n"):
                if line.strip():
                    data = json.loads(line)
                    if data.get("message") == "request id test":
                        assert data.get("request_id") == test_id
        finally:
            request_id_var.reset(token)

    def test_request_id_empty_when_not_set(self, capfd):
        """Test that request_id is empty/missing when not set in contextvars."""
        configure_logging(level="INFO")
        # Ensure no request_id is set
        token = request_id_var.set("")
        try:
            test_logger = logging.getLogger("test.no_request_id")
            test_logger.info("no request id test")

            captured = capfd.readouterr()
            for line in captured.err.strip().split("\n"):
                if line.strip():
                    data = json.loads(line)
                    if data.get("message") == "no request id test":
                        # request_id should be empty string or not present
                        assert data.get("request_id", "") == ""
        finally:
            request_id_var.reset(token)

    def test_request_id_propagates_to_different_loggers(self, capfd):
        """Test that request_id propagates to loggers with different names."""
        configure_logging(level="INFO")
        test_id = str(uuid.uuid4())
        token = request_id_var.set(test_id)
        try:
            logger_a = logging.getLogger("test.service_a")
            logger_b = logging.getLogger("test.service_b")
            logger_a.info("from service a")
            logger_b.info("from service b")

            captured = capfd.readouterr()
            found_a = False
            found_b = False
            for line in captured.err.strip().split("\n"):
                if line.strip():
                    data = json.loads(line)
                    if data.get("message") == "from service a":
                        assert data.get("request_id") == test_id
                        found_a = True
                    if data.get("message") == "from service b":
                        assert data.get("request_id") == test_id
                        found_b = True
            assert found_a and found_b
        finally:
            request_id_var.reset(token)


class TestRequestIdFilterUnit:
    """Unit tests for the RequestIdFilter class."""

    def test_filter_adds_request_id_to_record(self):
        """Test that the filter injects request_id into log records."""
        filt = RequestIdFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="test", args=(), exc_info=None
        )
        test_id = str(uuid.uuid4())
        token = request_id_var.set(test_id)
        try:
            filt.filter(record)
            assert record.request_id == test_id
        finally:
            request_id_var.reset(token)

    def test_filter_returns_true(self):
        """Test that filter always returns True (doesn't suppress records)."""
        filt = RequestIdFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="test", args=(), exc_info=None
        )
        assert filt.filter(record) is True
