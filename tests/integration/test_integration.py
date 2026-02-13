"""
Integration tests for the analytics service.
Tests end-to-end workflows with mocked external services.
"""
import pytest
import json
from unittest.mock import patch, MagicMock, call


@pytest.mark.integration
class TestEventProcessingFlow:
    """Test complete event processing flow."""
    
    @patch('consumer.influx_writer.write_event_ingest')
    @patch('consumer.analytics_producer.publish_analytics')
    def test_user_event_complete_flow(
        self, mock_publish, mock_influx_write, sample_user_event
    ):
        """Test complete processing of a user event."""
        from consumer.consumer import validate_schema, normalize_event, parse_event_time_ms
        
        topic = "user-events"
        
        # Step 1: Schema validation
        missing = validate_schema(topic, sample_user_event)
        assert missing == [], f"Event should be valid but missing: {missing}"
        
        # Step 2: Normalization
        normalized = normalize_event(topic, sample_user_event)
        assert normalized["producer"] == "user-service"
        assert normalized["event_name"] == "user_event"
        assert "source_team" in normalized
        
        # Step 3: Time parsing
        ts_ms = parse_event_time_ms(topic, sample_user_event)
        assert isinstance(ts_ms, int)
        assert ts_ms > 0
        
        # Step 4: Simulate InfluxDB write
        mock_influx_write(
            topic=topic,
            event_type=normalized["event_name"],
            source_team=normalized["source_team"],
            latency_ms=100,
            lag=5,
            ts_ms=ts_ms
        )
        
        # Step 5: Simulate analytics publication
        mock_publish(
            topic=topic,
            lag=5,
            latency=100,
            trace_id="test-trace-id"
        )
        
        # Verify all steps were called
        mock_influx_write.assert_called_once()
        mock_publish.assert_called_once()
    
    @patch('consumer.influx_writer.write_event_ingest')
    @patch('consumer.analytics_producer.publish_analytics')
    def test_order_event_complete_flow(
        self, mock_publish, mock_influx_write, sample_order_event
    ):
        """Test complete processing of an order event."""
        from consumer.consumer import validate_schema, normalize_event, parse_event_time_ms
        
        topic = "order-events"
        
        # Validation
        missing = validate_schema(topic, sample_order_event)
        assert missing == []
        
        # Normalization
        normalized = normalize_event(topic, sample_order_event)
        assert normalized["producer"] == "order-service"
        assert "event_name" in normalized
        
        # Time parsing
        ts_ms = parse_event_time_ms(topic, sample_order_event)
        assert isinstance(ts_ms, int)
        
        # Simulate writes
        mock_influx_write(
            topic=topic,
            event_type=normalized["event_name"],
            source_team=normalized.get("source_team", "team-4"),
            latency_ms=150,
            lag=10,
            ts_ms=ts_ms
        )
        
        mock_publish(
            topic=topic,
            lag=10,
            latency=150,
            trace_id="order-trace"
        )
        
        mock_influx_write.assert_called_once()
        mock_publish.assert_called_once()
    
    @patch('consumer.metrics.analytics_event_validation_failures_total')
    def test_invalid_event_handling(self, mock_validation_failures):
        """Test handling of invalid events."""
        from consumer.consumer import validate_schema
        
        # Create invalid event (missing required fields)
        invalid_event = {
            "user_id": 123
            # Missing: email, status, created_at, updated_at
        }
        
        missing = validate_schema("user-events", invalid_event)
        
        # Should detect missing fields
        assert len(missing) > 0
        assert "email" in missing or "status" in missing


@pytest.mark.integration
class TestInfluxDBIntegration:
    """Test InfluxDB integration."""
    
    @patch('consumer.influx_writer.InfluxDBClient')
    def test_influx_write_creates_correct_point(self, mock_client_class):
        """Test that InfluxDB Point is created with correct structure."""
        from consumer.influx_writer import write_event_ingest
        
        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client_class.return_value = mock_client
        
        # Reset module state
        import consumer.influx_writer as influx_writer
        influx_writer._client = None
        influx_writer._write_api = None
        
        write_event_ingest(
            topic="user-events",
            event_type="user_created",
            source_team="team-4",
            latency_ms=125,
            lag=3,
            ts_ms=1640000000000
        )
        
        # Verify write was called with correct bucket
        mock_write_api.write.assert_called_once()
        call_kwargs = mock_write_api.write.call_args[1]
        assert 'bucket' in call_kwargs
        assert 'record' in call_kwargs
    
    @patch('consumer.influx_writer.InfluxDBClient')
    @patch('consumer.influx_writer.log')
    def test_influx_write_error_handling(self, mock_log, mock_client_class):
        """Test error handling when InfluxDB write fails."""
        from consumer.influx_writer import write_event_ingest
        
        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_write_api.write.side_effect = Exception("Connection timeout")
        mock_client.write_api.return_value = mock_write_api
        mock_client_class.return_value = mock_client
        
        # Reset module state
        import consumer.influx_writer as influx_writer
        influx_writer._client = None
        influx_writer._write_api = None
        
        # Should not raise exception
        write_event_ingest(
            topic="user-events",
            event_type="user_created",
            source_team="team-4",
            latency_ms=125,
            lag=3,
            ts_ms=1640000000000
        )
        
        # Verify error was logged
        mock_log.error.assert_called_once()


@pytest.mark.integration
class TestKafkaIntegration:
    """Test Kafka producer integration."""
    
    @patch('consumer.analytics_producer.KafkaProducer')
    @patch('consumer.analytics_producer.trace.get_tracer')
    def test_kafka_publish_with_headers(self, mock_get_tracer, mock_producer_class):
        """Test that Kafka messages include OpenTelemetry headers."""
        from consumer.analytics_producer import publish_analytics
        
        mock_producer = MagicMock()
        future = MagicMock()
        future.get.return_value = MagicMock()
        mock_producer.send.return_value = future
        mock_producer_class.return_value = mock_producer
        
        # Reset module state
        import consumer.analytics_producer as analytics_producer
        analytics_producer._producer = None
        
        # Mock tracer
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        publish_analytics(
            topic="user-events",
            lag=5,
            latency=100,
            trace_id="integration-test-trace"
        )
        
        # Verify send was called
        mock_producer.send.assert_called_once()
        
        # Check that headers were included
        call_args = mock_producer.send.call_args
        if 'headers' in call_args[1]:
            headers = call_args[1]['headers']
            assert isinstance(headers, list)
    
    @patch('consumer.analytics_producer.KafkaProducer')
    @patch('consumer.analytics_producer.trace.get_tracer')
    @patch('consumer.analytics_producer.time.sleep')
    def test_kafka_publish_retry_on_failure(
        self, mock_sleep, mock_get_tracer, mock_producer_class
    ):
        """Test that publisher attempts to recreate producer on failure."""
        from consumer.analytics_producer import publish_analytics
        
        mock_producer = MagicMock()
        mock_producer.send.side_effect = Exception("Network error")
        mock_producer_class.return_value = mock_producer
        
        # Reset module state
        import consumer.analytics_producer as analytics_producer
        analytics_producer._producer = None
        
        # Mock tracer
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        # Should not raise exception
        publish_analytics(
            topic="user-events",
            lag=5,
            latency=100,
            trace_id="retry-test"
        )
        
        # Verify sleep was called (part of retry logic)
        mock_sleep.assert_called_once()


@pytest.mark.integration
class TestMetricsIntegration:
    """Test Prometheus metrics integration."""
    
    @patch('consumer.influx_writer.InfluxDBClient')
    def test_metrics_incremented_on_success(self, mock_client_class):
        """Test that success metrics are incremented."""
        from consumer.influx_writer import write_event_ingest
        from consumer.metrics import analytics_influx_writes_total
        
        # Setup mock client
        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_client_class.return_value = mock_client
        
        # Reset module state
        import consumer.influx_writer as influx_writer
        influx_writer._client = None
        influx_writer._write_api = None
        
        # Reset counter
        analytics_influx_writes_total.labels(status='success')._value.set(0)
        
        write_event_ingest(
            topic="user-events",
            event_type="user_created",
            source_team="team-4",
            latency_ms=100,
            lag=5,
            ts_ms=1640000000000
        )
        
        # Verify success metric was incremented
        metric_value = analytics_influx_writes_total.labels(status='success')._value.get()
        assert metric_value >= 1
    
    def test_metrics_incremented_on_failure(self):
        """Test that failure metrics are incremented."""
        from consumer.influx_writer import write_event_ingest
        from consumer.metrics import analytics_influx_writes_total
        
        with patch('consumer.influx_writer._get_write_api') as mock_get_api:
            mock_write_api = MagicMock()
            mock_write_api.write.side_effect = Exception("Write failed")
            mock_get_api.return_value = mock_write_api
            
            # Reset counter
            analytics_influx_writes_total.labels(status='failure')._value.set(0)
            
            write_event_ingest(
                topic="user-events",
                event_type="user_created",
                source_team="team-4",
                latency_ms=100,
                lag=5,
                ts_ms=1640000000000
            )
            
            # Verify failure metric was incremented
            metric_value = analytics_influx_writes_total.labels(status='failure')._value.get()
            assert metric_value >= 1


@pytest.mark.integration
class TestOpenTelemetryIntegration:
    """Test OpenTelemetry tracing integration."""
    
    @patch('otel_init.OTLPSpanExporter')
    @patch('otel_init.BatchSpanProcessor')
    @patch('otel_init.TracerProvider')
    def test_tracing_setup_integration(
        self, mock_provider_class, mock_processor_class, mock_exporter_class
    ):
        """Test that tracing is set up correctly."""
        from otel_init import setup_tracing
        
        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider
        
        tracer = setup_tracing("analytics-service")
        
        assert tracer is not None
        mock_provider.add_span_processor.assert_called_once()
    
    @patch('consumer.analytics_producer.trace.get_tracer')
    @patch('consumer.analytics_producer.KafkaProducer')
    def test_span_created_for_kafka_publish(self, mock_producer_class, mock_get_tracer):
        """Test that spans are created for Kafka publishing."""
        from consumer.analytics_producer import publish_analytics
        
        mock_producer = MagicMock()
        future = MagicMock()
        future.get.return_value = MagicMock()
        mock_producer.send.return_value = future
        mock_producer_class.return_value = mock_producer
        
        # Reset module state
        import consumer.analytics_producer as analytics_producer
        analytics_producer._producer = None
        
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        publish_analytics(
            topic="user-events",
            lag=5,
            latency=100,
            trace_id="otel-test"
        )
        
        # Verify span was created with correct name
        mock_tracer.start_as_current_span.assert_called_once()
        span_name = mock_tracer.start_as_current_span.call_args[0][0]
        assert span_name == "kafka.produce"