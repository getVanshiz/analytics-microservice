"""
Test configuration and fixtures.
This file provides common fixtures for all tests.
"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

# Add app directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer for testing without real Kafka."""
    with patch('kafka.KafkaProducer') as mock:
        producer_instance = MagicMock()
        mock.return_value = producer_instance
        # Mock the send().get() pattern
        future = MagicMock()
        future.get.return_value = MagicMock()
        producer_instance.send.return_value = future
        yield producer_instance


@pytest.fixture
def mock_influx_client():
    """Mock InfluxDB client for testing without real InfluxDB."""
    with patch('influxdb_client.InfluxDBClient') as mock:
        client_instance = MagicMock()
        write_api = MagicMock()
        client_instance.write_api.return_value = write_api
        mock.return_value = client_instance
        yield write_api


@pytest.fixture
def mock_otel_tracer():
    """Mock OpenTelemetry tracer."""
    with patch('opentelemetry.trace.get_tracer') as mock:
        tracer = MagicMock()
        span = MagicMock()
        span.__enter__ = Mock(return_value=span)
        span.__exit__ = Mock(return_value=False)
        tracer.start_as_current_span.return_value = span
        mock.return_value = tracer
        yield tracer


@pytest.fixture
def sample_user_event():
    """Sample valid user event for testing."""
    return {
        "user_id": 123,
        "email": "test@example.com",
        "status": "ACTIVE",
        "created_at": "2024-01-01T10:00:00+05:30Z",
        "updated_at": "2024-01-01T10:00:00+05:30Z",
    }


@pytest.fixture
def sample_order_event():
    """Sample valid order event for testing."""
    return {
        "id": "order-123",
        "order_id": 456,
        "user_id": 123,
        "item": "Product XYZ",
        "quantity": 2,
        "status": "SHIPPED",
        "total": 99.99,
        "created_at": "2024-01-01T10:00:00Z",
        "updated_at": "2024-01-01T10:00:00Z"
    }


@pytest.fixture
def sample_notification_event():
    """Sample valid notification event for testing."""
    return {
        "event_id": "notif-789",
        "event_version": "1.0",
        "event_name": "notification_sent",
        "producer": "notification-service",
        "user_id": 123,
        "type": "EMAIL",
        "data": {"message": "Test notification"},
        "occurred_at": "2024-01-01 10:00:00 IST"
    }


@pytest.fixture
def flask_app():
    """Create Flask app for testing."""
    # Import here to avoid import issues
    from main import app
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(flask_app):
    """Flask test client."""
    return flask_app.test_client()


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up test environment variables."""
    test_env = {
        'APP_VERSION': '0.1.0-test',
        'PORT': '8080',
        'KAFKA_BOOTSTRAP': 'localhost:9092',
        'INFLUX_URL': 'http://localhost:8086',
        'INFLUX_TOKEN': 'test-token',
        'INFLUX_ORG': 'test-org',
        'INFLUX_BUCKET': 'test-bucket',
        'OTEL_SERVICE_NAME': 'analytics-service-test',
        'OTEL_EXPORTER_OTLP_ENDPOINT': 'localhost:4317',
        'OTEL_EXPORTER_OTLP_INSECURE': 'true',
    }
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    return test_env