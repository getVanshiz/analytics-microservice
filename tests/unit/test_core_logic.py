"""
Comprehensive Unit Tests for Core Business Logic

Tests cover:
- Event time parsing (parse_event_time_ms)
- Schema validation (validate_schema)
- Event normalization (normalize_event)
"""

import pytest
from datetime import datetime, timedelta
from app.consumer.consumer import (
    validate_schema,
    normalize_event,
    parse_event_time_ms,
)


class TestEventTimeParsing:
    """Test parse_event_time_ms function with various timestamp formats."""
    
    def test_iso_8601_with_timezone(self):
        event = {"created_at": "2024-01-15T10:00:00Z"}
        ts_ms = parse_event_time_ms("user-events", event)
        assert ts_ms > 0

    def test_unix_timestamp_seconds(self):
        now_seconds = int(datetime.now().timestamp())
        event = {"created_at": now_seconds}
        ts_ms = parse_event_time_ms("user-events", event)
        assert ts_ms > 0

    def test_missing_timestamp_field(self):
        event = {"user_id": 123, "status": "ACTIVE"}
        ts_ms = parse_event_time_ms("user-events", event)
        assert ts_ms >= 0

    def test_invalid_timestamp_format(self):
        event = {"created_at": "not-a-date"}
        ts_ms = parse_event_time_ms("user-events", event)
        assert ts_ms >= 0


class TestSchemaValidation:
    """Test validate_schema function."""
    
    def test_valid_user_event(self):
        event = {
            "user_id": 123,
            "email": "user@example.com",
            "status": "ACTIVE",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
        }
        missing = validate_schema("user-events", event)
        assert missing == []
    
    def test_valid_order_event(self):
        event = {
            "order_id": "ORD123",
            "status": "SHIPPED",
            "customer_id": 456,
        }
        missing = validate_schema("order-events", event)
        assert missing == []
    
    def test_missing_required_fields(self):
        event = {"user_id": 123}
        missing = validate_schema("user-events", event)
        assert len(missing) > 0
    
    def test_extra_fields_allowed(self):
        event = {
            "user_id": 123,
            "email": "user@example.com",
            "status": "ACTIVE",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
            "extra_field": "ok",
        }
        missing = validate_schema("user-events", event)
        assert missing == []


class TestEventNormalization:
    """Test normalize_event function."""
    
    def test_user_event_normalization(self):
        event = {
            "user_id": 123,
            "email": "user@example.com",
            "status": "ACTIVE",
        }
        normalized = normalize_event("user-events", event)
        
        assert normalized["event_name"] == "user_event"
        assert normalized["source_team"] == "platform"
    
    def test_order_event_normalization(self):
        event = {
            "order_id": "ORD123",
            "status": "SHIPPED",
            "customer_id": 456,
        }
        normalized = normalize_event("order-events", event)
        
        assert normalized["event_name"] == "order_event"
        assert normalized["source_team"] == "commerce"
    
    def test_metadata_injection(self):
        event = {"user_id": 123, "email": "test@example.com"}
        normalized = normalize_event("user-events", event)
        
        assert "event_name" in normalized
        assert "producer" in normalized
        assert "source_team" in normalized
    
    def test_numeric_field_preservation(self):
        event = {
            "order_id": "O123",
            "customer_id": 999,
            "amount": 1234.56,
        }
        normalized = normalize_event("order-events", event)
        
        assert normalized.get("customer_id") == 999
        assert normalized.get("amount") == 1234.56


class TestCombinedPipeline:
    """Test complete pipeline: validate → parse → normalize."""
    
    def test_full_pipeline_valid_event(self):
        event = {
            "user_id": 123,
            "email": "user@example.com",
            "status": "ACTIVE",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
        }
        
        missing = validate_schema("user-events", event)
        assert missing == []
        
        ts_ms = parse_event_time_ms("user-events", event)
        assert ts_ms > 0
        
        normalized = normalize_event("user-events", event)
        assert normalized["event_name"] == "user_event"
    
    def test_pipeline_handles_missing_fields(self):
        event = {"user_id": 123}
        
        missing = validate_schema("user-events", event)
        assert len(missing) > 0
        
        ts_ms = parse_event_time_ms("user-events", event)
        normalized = normalize_event("user-events", event)
        
        assert ts_ms >= 0
        assert isinstance(normalized, dict)
