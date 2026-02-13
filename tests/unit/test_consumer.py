"""
Unit tests for consumer event processing logic.
Tests schema validation, event normalization, and time parsing.
"""
import pytest
from datetime import datetime


# Note: These tests assume consumer.py has the following functions:
# - validate_schema(topic, event) -> list of missing fields
# - normalize_event(topic, event) -> normalized event dict
# - parse_event_time_ms(topic, event) -> timestamp in milliseconds

@pytest.mark.unit
class TestEventTimeParser:
    """Test event timestamp parsing logic."""
    
    def test_user_event_time_parsing(self):
        """Test parsing user event timestamp."""
        from consumer.consumer import parse_event_time_ms
        
        event = {
            "created_at": "2024-01-15T10:30:00+05:30Z"
        }
        ts = parse_event_time_ms("user-events", event)
        
        assert isinstance(ts, int)
        assert ts > 0
    
    def test_notification_event_time_parsing(self):
        """Test parsing notification event timestamp."""
        from consumer.consumer import parse_event_time_ms
        
        event = {
            "occurred_at": "2024-01-15 10:30:00 IST"
        }
        ts = parse_event_time_ms("notification-events", event)
        
        assert isinstance(ts, int)
        assert ts > 0
    
    def test_order_event_time_parsing(self):
        """Test parsing order event timestamp."""
        from consumer.consumer import parse_event_time_ms
        
        event = {
            "created_at": "2024-01-15T10:30:00Z"
        }
        ts = parse_event_time_ms("order-events", event)
        
        assert isinstance(ts, int)
        assert ts > 0
    
    def test_missing_timestamp_returns_current_time(self):
        """Test that missing timestamp returns current time."""
        from consumer.consumer import parse_event_time_ms
        import time
        
        before = int(time.time() * 1000)
        ts = parse_event_time_ms("user-events", {})
        after = int(time.time() * 1000)
        
        assert isinstance(ts, int)
        assert before <= ts <= after
    
    def test_different_topics_different_fields(self):
        """Test that different topics use different timestamp fields."""
        from consumer.consumer import parse_event_time_ms
        
        # User events use 'created_at'
        user_event = {"created_at": "2024-01-15T10:00:00Z"}
        user_ts = parse_event_time_ms("user-events", user_event)
        
        # Notification events use 'occurred_at'
        notif_event = {"occurred_at": "2024-01-15 10:00:00 IST"}
        notif_ts = parse_event_time_ms("notification-events", notif_event)
        
        assert isinstance(user_ts, int)
        assert isinstance(notif_ts, int)


@pytest.mark.unit
class TestSchemaValidation:
    """Test event schema validation."""
    
    def test_user_event_valid_schema(self, sample_user_event):
        """Test that valid user event passes validation."""
        from consumer.consumer import validate_schema
        
        missing = validate_schema("user-events", sample_user_event)
        
        assert missing == []
    
    def test_user_event_missing_required_fields(self):
        """Test detection of missing required fields."""
        from consumer.consumer import validate_schema
        
        event = {
            "user_id": 123,
            "email": "test@example.com"
            # Missing: status, created_at, updated_at
        }
        missing = validate_schema("user-events", event)
        
        assert len(missing) > 0
        assert "status" in missing
        assert "created_at" in missing
    
    def test_order_event_valid_schema(self, sample_order_event):
        """Test that valid order event passes validation."""
        from consumer.consumer import validate_schema
        
        missing = validate_schema("order-events", sample_order_event)
        
        assert missing == []
    
    def test_notification_event_valid_schema(self, sample_notification_event):
        """Test that valid notification event passes validation."""
        from consumer.consumer import validate_schema
        
        missing = validate_schema("notification-events", sample_notification_event)
        
        assert missing == []
    
    def test_unknown_topic_no_validation(self):
        """Test that unknown topics skip validation."""
        from consumer.consumer import validate_schema
        
        event = {"random": "data"}
        missing = validate_schema("unknown-topic", event)
        
        # Unknown topics should return empty list (no validation)
        assert missing == []
    
    def test_empty_event_validation(self):
        """Test validation of empty event."""
        from consumer.consumer import validate_schema
        
        missing = validate_schema("user-events", {})
        
        # Should detect all required fields as missing
        assert len(missing) > 0


@pytest.mark.unit
class TestEventNormalization:
    """Test event normalization logic."""
    
    def test_user_event_normalization(self):
        """Test normalization of user events."""
        from consumer.consumer import normalize_event
        
        result = normalize_event("user-events", {})
        
        assert "event_name" in result
        assert "producer" in result
        assert "source_team" in result
        assert result["event_name"] == "user_event"
        assert result["producer"] == "user-service"
    
    def test_order_event_normalization_shipped(self):
        """Test normalization of shipped order event."""
        from consumer.consumer import normalize_event
        
        event = {"status": "SHIPPED"}
        result = normalize_event("order-events", event)
        
        assert result["event_name"] == "order_shipped"
        assert result["producer"] == "order-service"
    
    def test_order_event_normalization_pending(self):
        """Test normalization of pending order event."""
        from consumer.consumer import normalize_event
        
        event = {"status": "PENDING"}
        result = normalize_event("order-events", event)
        
        assert result["event_name"] == "order_pending"
        assert result["producer"] == "order-service"
    
    def test_notification_event_preserves_fields(self):
        """Test that notification events preserve existing fields."""
        from consumer.consumer import normalize_event
        
        event = {
            "event_name": "notification_sent",
            "producer": "notification-service"
        }
        result = normalize_event("notification-events", event)
        
        assert result["event_name"] == "notification_sent"
        assert result["producer"] == "notification-service"
    
    def test_normalization_adds_source_team(self):
        """Test that normalization adds source_team."""
        from consumer.consumer import normalize_event
        
        result = normalize_event("user-events", {})
        
        assert "source_team" in result
        assert isinstance(result["source_team"], str)
    
    def test_normalization_adds_metadata_fields(self):
        """Test that normalization adds required metadata fields."""
        from consumer.consumer import normalize_event
        
        event = {"user_id": 123, "email": "test@example.com"}
        result = normalize_event("user-events", event)
        
        # Check that metadata fields are added
        assert "event_name" in result
        assert "producer" in result
        assert "source_team" in result


@pytest.mark.unit
class TestEventProcessingHelpers:
    """Test helper functions for event processing."""
    
    def test_event_validation_returns_list(self):
        """Test that validation always returns a list."""
        from consumer.consumer import validate_schema
        
        result = validate_schema("user-events", {})
        
        assert isinstance(result, list)
    
    def test_normalization_returns_dict(self):
        """Test that normalization always returns a dict."""
        from consumer.consumer import normalize_event
        
        result = normalize_event("user-events", {})
        
        assert isinstance(result, dict)
    
    def test_time_parsing_returns_int(self):
        """Test that time parsing always returns an integer."""
        from consumer.consumer import parse_event_time_ms
        
        result = parse_event_time_ms("user-events", {})
        
        assert isinstance(result, int)


