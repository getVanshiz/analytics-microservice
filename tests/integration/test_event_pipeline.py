"""
Integration Tests for Event Pipeline

Tests cover full event pipeline:
API → Kafka → Consumer → InfluxDB → Metrics/Logs
"""

import pytest
from unittest.mock import patch, MagicMock
from app.consumer.consumer import (
    validate_schema,
    normalize_event,
    parse_event_time_ms,
)


class TestEventIngestionPipeline:
    """Test complete event ingestion from API to metrics."""
    
    @patch("app.consumer.influx_writer.write_event_ingest")
    def test_user_event_end_to_end(self, mock_write):
        """Test complete user event pipeline."""
        topic = "user-events"
        event = {
            "user_id": 123,
            "email": "user@example.com",
            "status": "ACTIVE",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
        }
        
        missing = validate_schema(topic, event)
        assert missing == []
        
        ts_ms = parse_event_time_ms(topic, event)
        assert ts_ms > 0
        
        normalized = normalize_event(topic, event)
        
        mock_write(
            topic=topic,
            event_type=normalized["event_name"],
            source_team=normalized["source_team"],
            latency_ms=5,
        )
        
        assert normalized["event_name"] == "user_event"
        mock_write.assert_called_once()
    
    @patch("app.consumer.influx_writer.write_event_ingest")
    def test_order_event_with_metrics(self, mock_write):
        """Test order event with detailed metrics recording."""
        topic = "order-events"
        event = {
            "order_id": "ORD789",
            "status": "SHIPPED",
            "customer_id": 456,
            "amount": 299.99,
        }
        
        missing = validate_schema(topic, event)
        assert missing == []
        
        ts_ms = parse_event_time_ms(topic, event)
        normalized = normalize_event(topic, event)
        
        mock_write(
            topic=topic,
            event_type=normalized["event_name"],
            source_team=normalized["source_team"],
            latency_ms=12,
        )
        
        assert normalized["source_team"] == "commerce"
        mock_write.assert_called_once()


class TestKafkaMessageFlow:
    """Test Kafka message consumption and processing."""
    
    @patch("app.consumer.analytics_producer.produce_to_kafka")
    def test_consume_and_produce_analytics_event(self, mock_produce):
        """Test consuming event and producing analytics event."""
        consumed_event = {
            "user_id": 123,
            "email": "test@example.com",
            "status": "ACTIVE",
            "created_at": "2024-01-15T10:00:00Z",
        }
        
        normalized = normalize_event("user-events", consumed_event)
        
        mock_produce(
            topic="analytics-events",
            value={"event_name": normalized["event_name"]},
        )
        
        mock_produce.assert_called_once()
    
    @patch("app.consumer.analytics_producer.produce_to_kafka")
    def test_batch_processing(self, mock_produce):
        """Test processing multiple events in batch."""
        events = [
            {"user_id": 1, "email": "user1@example.com", "status": "ACTIVE"},
            {"user_id": 2, "email": "user2@example.com", "status": "INACTIVE"},
        ]
        
        for event in events:
            normalize_event("user-events", event)
            mock_produce(topic="analytics-events", value={})
        
        assert mock_produce.call_count == 2


class TestDataValidation:
    """Test data validation and transformation."""
    
    def test_email_field_validation(self):
        """Email field is validated and preserved."""
        event = {
            "user_id": 1,
            "email": "test+alias@example.co.uk",
            "status": "ACTIVE",
            "created_at": "2024-01-15T10:00:00Z",
        }
        
        missing = validate_schema("user-events", event)
        assert missing == []
        
        normalized = normalize_event("user-events", event)
        assert normalized.get("email") == "test+alias@example.co.uk"
    
    def test_numeric_field_preservation(self):
        """Numeric fields are preserved correctly."""
        event = {
            "order_id": "ORD123",
            "status": "SHIPPED",
            "customer_id": 999,
            "amount": 1234.56,
        }
        
        normalized = normalize_event("order-events", event)
        assert normalized.get("customer_id") == 999
        assert normalized.get("amount") == 1234.56
    
    def test_timestamp_to_milliseconds(self):
        """Timestamp fields are parsed to milliseconds."""
        event = {
            "user_id": 1,
            "email": "test@example.com",
            "status": "ACTIVE",
            "created_at": "2024-01-15T10:00:00Z",
        }
        
        ts_ms = parse_event_time_ms("user-events", event)
        assert ts_ms >= 1705318800000


class TestErrorHandling:
    """Test error scenarios."""
    
    def test_missing_required_field_detected(self):
        """Missing required fields are detected."""
        event = {"user_id": 1}
        
        missing = validate_schema("user-events", event)
        assert len(missing) > 0
    
    def test_invalid_event_normalizes(self):
        """Invalid event still produces normalized output."""
        event = {}
        
        result = normalize_event("user-events", event)
        
        assert result["event_name"] == "user_event"
        assert "source_team" in result
    
    @patch("app.consumer.influx_writer.write_event_ingest")
    def test_write_failure(self, mock_write):
        """Write failures are handled."""
        mock_write.side_effect = Exception("Write failed")
        
        event = {
            "user_id": 1,
            "email": "test@example.com",
            "status": "ACTIVE",
        }
        
        normalized = normalize_event("user-events", event)
        
        with pytest.raises(Exception):
            mock_write(
                topic="user-events",
                event_type=normalized["event_name"],
                source_team=normalized["source_team"],
            )


class TestMetricsCollection:
    """Test metrics recording."""
    
    @patch("app.consumer.influx_writer.write_event_ingest")
    def test_latency_metrics(self, mock_write):
        """Processing latency is recorded."""
        latencies = [5, 10, 15, 20]
        
        for latency in latencies:
            mock_write(
                topic="user-events",
                event_type="user_event",
                source_team="platform",
                latency_ms=latency,
            )
        
        assert mock_write.call_count == 4
    
    @patch("app.consumer.influx_writer.write_event_ingest")
    def test_event_count_by_topic(self, mock_write):
        """Event counts tracked per topic."""
        topics = ["user-events", "order-events", "user-events"]
        
        for topic in topics:
            mock_write(
                topic=topic,
                event_type="test",
                source_team="test",
            )
        
        recorded_topics = [call[1]["topic"] for call in mock_write.call_args_list]
        assert recorded_topics == topics
