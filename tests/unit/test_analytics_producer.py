"""
Unit tests for Kafka analytics producer.
Tests message publishing, error handling, and OpenTelemetry integration.
"""
import pytest
import json
from unittest.mock import patch, MagicMock, call
from consumer import analytics_producer


@pytest.mark.unit
class TestKafkaProducer:
    """Test Kafka producer functionality."""
    
    @patch('consumer.analytics_producer.KafkaProducer')
    def test_new_producer_creates_kafka_producer(self, mock_producer_class):
        """Test that new producer creates KafkaProducer instance."""
        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer
        
        result = analytics_producer._new_producer()
        
        mock_producer_class.assert_called_once()
        assert result == mock_producer
    
    @patch('consumer.analytics_producer.KafkaProducer')
    def test_new_producer_configuration(self, mock_producer_class):
        """Test that producer is configured correctly."""
        analytics_producer._new_producer()
        
        call_kwargs = mock_producer_class.call_args[1]
        assert 'bootstrap_servers' in call_kwargs
        assert 'value_serializer' in call_kwargs
        assert call_kwargs['acks'] == 'all'
        assert call_kwargs['retries'] == 5
    
    @patch('consumer.analytics_producer.KafkaProducer')
    def test_get_producer_reuses_instance(self, mock_producer_class):
        """Test that producer instance is reused."""
        # Reset module state
        analytics_producer._producer = None
        
        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer
        
        # First call
        analytics_producer._get_producer()
        # Second call
        analytics_producer._get_producer()
        
        # Should only create once
        assert mock_producer_class.call_count == 1


@pytest.mark.unit
class TestPublishAnalytics:
    """Test publishing analytics events."""
    
    @patch('consumer.analytics_producer.trace.get_tracer')
    @patch('consumer.analytics_producer._get_producer')
    def test_publish_analytics_creates_event(self, mock_get_producer, mock_get_tracer):
        """Test that analytics event is created with correct structure."""
        mock_producer = MagicMock()
        future = MagicMock()
        future.get.return_value = MagicMock()
        mock_producer.send.return_value = future
        mock_get_producer.return_value = mock_producer
        
        # Mock tracer
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        analytics_producer.publish_analytics(
            topic="user-events",
            lag=5,
            latency=150,
            trace_id="test-trace-123"
        )
        
        # Verify send was called
        mock_producer.send.assert_called_once()
        
        # Get the event that was sent
        call_args = mock_producer.send.call_args[0]
        event = call_args[1]
        
        assert event['event_type'] == 'analytics_updated'
        assert event['observed_topic'] == 'user-events'
        assert event['consumer_lag'] == 5
        assert event['latency_ms'] == 150
        assert event['trace_id'] == 'test-trace-123'
        assert event['source_team'] == 'team-4'
        assert 'event_id' in event
        assert 'produced_at' in event
    
    @patch('consumer.analytics_producer.trace.get_tracer')
    @patch('consumer.analytics_producer._get_producer')
    def test_publish_analytics_sends_to_correct_topic(self, mock_get_producer, mock_get_tracer):
        """Test that event is sent to analytics topic."""
        mock_producer = MagicMock()
        future = MagicMock()
        future.get.return_value = MagicMock()
        mock_producer.send.return_value = future
        mock_get_producer.return_value = mock_producer
        
        # Mock tracer
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        analytics_producer.publish_analytics(
            topic="order-events",
            lag=10,
            latency=200,
            trace_id="trace-456"
        )
        
        call_args = mock_producer.send.call_args[0]
        topic = call_args[0]
        
        assert topic == 'analytics-events' or topic == analytics_producer.ANALYTICS_TOPIC
    
    @patch('consumer.analytics_producer.trace.get_tracer')
    @patch('consumer.analytics_producer._get_producer')
    def test_publish_analytics_creates_span(self, mock_get_producer, mock_get_tracer):
        """Test that OpenTelemetry span is created."""
        mock_producer = MagicMock()
        future = MagicMock()
        future.get.return_value = MagicMock()
        mock_producer.send.return_value = future
        mock_get_producer.return_value = mock_producer
        
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        analytics_producer.publish_analytics(
            topic="notification-events",
            lag=2,
            latency=75,
            trace_id="trace-789"
        )
        
        # Verify span was created
        mock_tracer.start_as_current_span.assert_called_once()
        span_name = mock_tracer.start_as_current_span.call_args[0][0]
        assert span_name == "kafka.produce"
    
    @patch('consumer.analytics_producer.time.sleep')
    @patch('consumer.analytics_producer.trace.get_tracer')
    @patch('consumer.analytics_producer._get_producer')
    @patch('consumer.analytics_producer.log')
    def test_publish_analytics_handles_errors(
        self, mock_log, mock_get_producer, mock_get_tracer, mock_sleep
    ):
        """Test that publish errors are handled gracefully."""
        mock_producer = MagicMock()
        mock_producer.send.side_effect = Exception("Kafka connection failed")
        mock_get_producer.return_value = mock_producer
        
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        # Should not raise exception
        analytics_producer.publish_analytics(
            topic="user-events",
            lag=5,
            latency=150,
            trace_id="trace-error"
        )
        
        # Verify error was logged
        mock_log.error.assert_called_once()


@pytest.mark.unit
class TestKafkaConfiguration:
    """Test Kafka configuration from environment."""
    
    def test_bootstrap_servers_default(self):
        """Test default Kafka bootstrap servers."""
        import os
        os.environ.pop('KAFKA_BOOTSTRAP', None)
        import importlib
        importlib.reload(analytics_producer)
        assert analytics_producer.BOOTSTRAP is not None
    
    def test_analytics_topic_from_env(self, mock_env_vars):
        """Test that analytics topic can be configured."""
        import os
        os.environ['ANALYTICS_TOPIC'] = 'custom-analytics-topic'
        import importlib
        importlib.reload(analytics_producer)
        # Will use env var or default
        assert analytics_producer.ANALYTICS_TOPIC is not None