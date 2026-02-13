"""
Unit tests for Prometheus metrics.
Tests metric definitions, labels, and types.
"""
import pytest
from consumer.metrics import (
    analytics_events_consumed_total,
    analytics_events_published_total,
    analytics_event_processing_latency_ms,
    analytics_influx_writes_total,
    analytics_processing_errors_total,
    analytics_event_validation_failures_total,
    analytics_events_in_flight
)


@pytest.mark.unit
class TestMetricsDefinitions:
    """Test that all metrics are defined correctly."""
    
    def test_events_consumed_counter_exists(self):
        """Test that events consumed counter is defined."""
        assert analytics_events_consumed_total is not None
        assert analytics_events_consumed_total._type == 'counter'
    
    def test_events_published_counter_exists(self):
        """Test that events published counter is defined."""
        assert analytics_events_published_total is not None
        assert analytics_events_published_total._type == 'counter'
    
    def test_processing_latency_histogram_exists(self):
        """Test that processing latency histogram is defined."""
        assert analytics_event_processing_latency_ms is not None
        assert analytics_event_processing_latency_ms._type == 'histogram'
    
    def test_influx_writes_counter_exists(self):
        """Test that InfluxDB writes counter is defined."""
        assert analytics_influx_writes_total is not None
        assert analytics_influx_writes_total._type == 'counter'
    
    def test_processing_errors_counter_exists(self):
        """Test that processing errors counter is defined."""
        assert analytics_processing_errors_total is not None
        assert analytics_processing_errors_total._type == 'counter'
    
    def test_validation_failures_counter_exists(self):
        """Test that validation failures counter is defined."""
        assert analytics_event_validation_failures_total is not None
        assert analytics_event_validation_failures_total._type == 'counter'
    
    def test_events_in_flight_gauge_exists(self):
        """Test that in-flight events gauge is defined."""
        assert analytics_events_in_flight is not None
        assert analytics_events_in_flight._type == 'gauge'


@pytest.mark.unit
class TestMetricsLabels:
    """Test metric labels."""
    
    def test_events_consumed_has_topic_label(self):
        """Test that consumed events counter has topic label."""
        # Try to increment with label
        try:
            analytics_events_consumed_total.labels(topic='test-topic').inc(0)
            success = True
        except Exception:
            success = False
        assert success
    
    def test_processing_latency_has_topic_label(self):
        """Test that processing latency has topic label."""
        try:
            analytics_event_processing_latency_ms.labels(topic='test-topic').observe(100)
            success = True
        except Exception:
            success = False
        assert success
    
    def test_influx_writes_has_status_label(self):
        """Test that InfluxDB writes counter has status label."""
        try:
            analytics_influx_writes_total.labels(status='success').inc(0)
            analytics_influx_writes_total.labels(status='failure').inc(0)
            success = True
        except Exception:
            success = False
        assert success


@pytest.mark.unit
class TestHistogramBuckets:
    """Test histogram bucket configuration."""
    
    def test_latency_histogram_has_buckets(self):
        """Test that latency histogram has defined buckets."""
        metric = analytics_event_processing_latency_ms
        # Check that buckets are defined
        assert hasattr(metric, '_buckets') or hasattr(metric, '_upper_bounds')

