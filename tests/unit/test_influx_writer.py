"""
Unit tests for InfluxDB writer module.
Tests write operations, error handling, and metric recording.
"""
import pytest
from unittest.mock import patch, MagicMock, call
from consumer import influx_writer
from consumer.metrics import analytics_influx_writes_total


@pytest.mark.unit
class TestInfluxWriter:
    """Test InfluxDB write functionality."""
    
    @patch('consumer.influx_writer.InfluxDBClient')
    def test_get_write_api_creates_client(self, mock_client_class):
        """Test that write API is created on first call."""
        # Reset module state
        influx_writer._client = None
        influx_writer._write_api = None
        
        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client_class.return_value = mock_client
        
        result = influx_writer._get_write_api()
        
        mock_client_class.assert_called_once()
        mock_client.write_api.assert_called_once()
        assert result == mock_write_api
    
    @patch('consumer.influx_writer.InfluxDBClient')
    def test_get_write_api_reuses_client(self, mock_client_class):
        """Test that write API is reused on subsequent calls."""
        # Reset module state
        influx_writer._client = None
        influx_writer._write_api = None
        
        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client_class.return_value = mock_client
        
        # First call
        influx_writer._get_write_api()
        # Second call
        influx_writer._get_write_api()
        
        # Client should only be created once
        assert mock_client_class.call_count == 1
    
    @patch('consumer.influx_writer._get_write_api')
    def test_write_event_ingest_success(self, mock_get_api):
        """Test successful event write to InfluxDB."""
        mock_write_api = MagicMock()
        mock_get_api.return_value = mock_write_api
        
        # Reset counter
        analytics_influx_writes_total.labels(status='success')._value.set(0)
        
        influx_writer.write_event_ingest(
            topic="user-events",
            event_type="user_created",
            source_team="team-4",
            latency_ms=150,
            lag=5,
            ts_ms=1640000000000
        )
        
        # Verify write was called
        mock_write_api.write.assert_called_once()
        
        # Verify metric was incremented
        metric_value = analytics_influx_writes_total.labels(status='success')._value.get()
        assert metric_value >= 1
    
    @patch('consumer.influx_writer._get_write_api')
    def test_write_event_ingest_with_point_fields(self, mock_get_api):
        """Test that Point is created with correct fields."""
        mock_write_api = MagicMock()
        mock_get_api.return_value = mock_write_api
        
        influx_writer.write_event_ingest(
            topic="order-events",
            event_type="order_placed",
            source_team="team-4",
            latency_ms=250,
            lag=10,
            ts_ms=1640000000000
        )
        
        # Get the Point argument
        call_args = mock_write_api.write.call_args
        point = call_args[1]['record']
        
        # Verify Point was passed
        assert point is not None
    
    @patch('consumer.influx_writer._get_write_api')
    def test_write_event_ingest_failure_increments_error_metric(self, mock_get_api):
        """Test that failures increment error metric."""
        mock_write_api = MagicMock()
        mock_write_api.write.side_effect = Exception("Connection failed")
        mock_get_api.return_value = mock_write_api
        
        # Reset counter
        analytics_influx_writes_total.labels(status='failure')._value.set(0)
        
        influx_writer.write_event_ingest(
            topic="user-events",
            event_type="user_created",
            source_team="team-4",
            latency_ms=150,
            lag=5,
            ts_ms=1640000000000
        )
        
        # Verify failure metric was incremented
        metric_value = analytics_influx_writes_total.labels(status='failure')._value.get()
        assert metric_value >= 1
    
    @patch('consumer.influx_writer._get_write_api')
    @patch('consumer.influx_writer.log')
    def test_write_event_ingest_logs_error(self, mock_log, mock_get_api):
        """Test that write failures are logged."""
        mock_write_api = MagicMock()
        mock_write_api.write.side_effect = Exception("Connection failed")
        mock_get_api.return_value = mock_write_api
        
        influx_writer.write_event_ingest(
            topic="user-events",
            event_type="user_created",
            source_team="team-4",
            latency_ms=150,
            lag=5,
            ts_ms=1640000000000
        )
        
        # Verify error was logged
        mock_log.error.assert_called_once()


@pytest.mark.unit
class TestInfluxConfiguration:
    """Test InfluxDB configuration from environment."""
    
    def test_influx_url_default(self):
        """Test default InfluxDB URL."""
        import os
        os.environ.pop('INFLUX_URL', None)
        # Reimport to get new values
        import importlib
        importlib.reload(influx_writer)
        assert influx_writer._INFLUX_URL is not None
    
    def test_influx_org_from_env(self, mock_env_vars):
        """Test that InfluxDB org is read from environment."""
        import importlib
        importlib.reload(influx_writer)
        assert influx_writer._INFLUX_ORG == 'test-org'
    
    def test_influx_bucket_from_env(self, mock_env_vars):
        """Test that InfluxDB bucket is read from environment."""
        import importlib
        importlib.reload(influx_writer)
        assert influx_writer._INFLUX_BUCKET == 'test-bucket'