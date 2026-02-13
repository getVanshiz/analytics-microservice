"""
Unit tests for logging configuration.
Tests JSON formatting, trace ID injection, and log structure.
"""
import pytest
import json
import logging
from unittest.mock import MagicMock, patch
from logging_config import JsonFormatter, setup_logging


@pytest.mark.unit
class TestJsonFormatter:
    """Test JSON log formatter."""
    
    def test_formatter_creates_valid_json(self):
        """Test that formatter produces valid JSON."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)  # Should not raise
        assert isinstance(data, dict)
    
    def test_formatter_includes_required_fields(self):
        """Test that all required fields are present."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert 'timestamp' in data
        assert 'level' in data
        assert 'service' in data
        assert 'message' in data
        assert 'logger' in data
    
    def test_formatter_service_name(self):
        """Test that service name is correct."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        assert data['service'] == 'analytics-service'
    
    def test_formatter_log_level(self):
        """Test that log level is captured."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.ERROR,
            pathname='test.py',
            lineno=1,
            msg='Error message',
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        assert data['level'] == 'ERROR'
    
    def test_formatter_message_content(self):
        """Test that message content is preserved."""
        formatter = JsonFormatter()
        test_msg = 'This is a test message'
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg=test_msg,
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        assert data['message'] == test_msg
    
    def test_formatter_extra_fields(self):
        """Test that extra fields are included."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test',
            args=(),
            exc_info=None
        )
        record.extra = {'component': 'kafka-consumer'}
        
        output = formatter.format(record)
        data = json.loads(output)
        assert 'component' in data
        assert data['component'] == 'kafka-consumer'
    
    @patch('opentelemetry.trace.get_current_span')
    def test_formatter_includes_otel_trace_id(self, mock_get_span):
        """Test that OpenTelemetry trace IDs are included when available."""
        formatter = JsonFormatter()
        
        # Mock span context
        mock_span = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.is_valid = True
        mock_ctx.trace_id = 123456789
        mock_ctx.span_id = 987654321
        mock_span.get_span_context.return_value = mock_ctx
        mock_get_span.return_value = mock_span
        
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test',
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        assert 'otel_trace_id' in data
        assert 'otel_span_id' in data


@pytest.mark.unit
class TestLoggingSetup:
    """Test logging setup function."""
    
    def test_setup_logging_configures_root_logger(self):
        """Test that setup_logging configures the root logger."""
        setup_logging()
        root = logging.getLogger()
        assert root.level == logging.INFO
        assert len(root.handlers) > 0
    
    def test_setup_logging_uses_json_formatter(self):
        """Test that JSON formatter is used."""
        setup_logging()
        root = logging.getLogger()
        handler = root.handlers[0]
        assert isinstance(handler.formatter, JsonFormatter)

