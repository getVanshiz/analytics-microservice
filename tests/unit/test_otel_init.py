"""
Unit tests for OpenTelemetry tracing setup.
Tests tracer initialization, configuration, and environment variable handling.
"""
import pytest
from unittest.mock import patch, MagicMock
from otel_init import setup_tracing, _parse_resource_attrs


@pytest.mark.unit
class TestParseResourceAttrs:
    """Test resource attribute parsing."""
    
    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result = _parse_resource_attrs("")
        assert result == {}
    
    def test_parse_none(self):
        """Test parsing None."""
        result = _parse_resource_attrs(None)
        assert result == {}
    
    def test_parse_single_attribute(self):
        """Test parsing single key=value pair."""
        result = _parse_resource_attrs("key1=value1")
        assert result == {"key1": "value1"}
    
    def test_parse_multiple_attributes(self):
        """Test parsing multiple attributes."""
        result = _parse_resource_attrs("key1=value1,key2=value2,key3=value3")
        assert result == {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }
    
    def test_parse_with_spaces(self):
        """Test parsing with extra spaces."""
        result = _parse_resource_attrs("key1=value1 , key2=value2")
        assert result == {"key1": "value1", "key2": "value2"}
    
    def test_parse_ignores_invalid_pairs(self):
        """Test that invalid pairs are ignored."""
        result = _parse_resource_attrs("key1=value1,invalid,key2=value2")
        assert result == {"key1": "value1", "key2": "value2"}
    
    def test_parse_values_with_equals(self):
        """Test parsing values containing equals signs."""
        result = _parse_resource_attrs("key1=value=with=equals")
        assert result == {"key1": "value=with=equals"}


@pytest.mark.unit
class TestSetupTracing:
    """Test OpenTelemetry setup."""
    
    @patch('otel_init.OTLPSpanExporter')
    @patch('otel_init.BatchSpanProcessor')
    @patch('otel_init.TracerProvider')
    @patch('otel_init.trace.set_tracer_provider')
    @patch('otel_init.trace.get_tracer')
    def test_setup_tracing_creates_tracer(
        self, mock_get_tracer, mock_set_provider, 
        mock_provider_class, mock_processor_class, mock_exporter_class
    ):
        """Test that setup_tracing creates and returns a tracer."""
        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider
        
        mock_tracer = MagicMock()
        mock_get_tracer.return_value = mock_tracer
        
        result = setup_tracing("test-service")
        
        assert result is not None
        mock_get_tracer.assert_called_once_with("test-service")
    
    @patch('otel_init.OTLPSpanExporter')
    @patch('otel_init.BatchSpanProcessor')
    @patch('otel_init.TracerProvider')
    @patch('otel_init.trace.set_tracer_provider')
    def test_setup_tracing_uses_default_service_name(
        self, mock_set_provider, mock_provider_class, 
        mock_processor_class, mock_exporter_class, mock_env_vars
    ):
        """Test that default service name is used when env var not set."""
        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider
        
        # Remove OTEL_SERVICE_NAME if it exists
        import os
        os.environ.pop('OTEL_SERVICE_NAME', None)
        
        setup_tracing("my-default-service")
        
        # Check that Resource was created with correct service name
        call_args = mock_provider_class.call_args
        resource = call_args[1]['resource']
        assert resource.attributes['service.name'] == 'my-default-service'
    
    @patch('otel_init.OTLPSpanExporter')
    @patch('otel_init.BatchSpanProcessor')
    @patch('otel_init.TracerProvider')
    @patch('otel_init.trace.set_tracer_provider')
    def test_setup_tracing_uses_env_service_name(
        self, mock_set_provider, mock_provider_class,
        mock_processor_class, mock_exporter_class, mock_env_vars
    ):
        """Test that environment variable overrides default service name."""
        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider
        
        setup_tracing("default-service")
        
        call_args = mock_provider_class.call_args
        resource = call_args[1]['resource']
        # Should use env var from mock_env_vars fixture
        assert resource.attributes['service.name'] == 'analytics-service-test'
    
    @patch('otel_init.OTLPSpanExporter')
    @patch('otel_init.BatchSpanProcessor')
    @patch('otel_init.TracerProvider')
    @patch('otel_init.trace.set_tracer_provider')
    def test_setup_tracing_configures_exporter(
        self, mock_set_provider, mock_provider_class,
        mock_processor_class, mock_exporter_class, mock_env_vars
    ):
        """Test that OTLP exporter is configured correctly."""
        setup_tracing("test-service")
        
        mock_exporter_class.assert_called_once()
        call_kwargs = mock_exporter_class.call_args[1]
        assert 'endpoint' in call_kwargs
        assert 'insecure' in call_kwargs
        assert call_kwargs['insecure'] is True
    
    @patch('otel_init.OTLPSpanExporter')
    @patch('otel_init.BatchSpanProcessor')
    @patch('otel_init.TracerProvider')
    @patch('otel_init.trace.set_tracer_provider')
    def test_setup_tracing_adds_span_processor(
        self, mock_set_provider, mock_provider_class,
        mock_processor_class, mock_exporter_class
    ):
        """Test that span processor is added to provider."""
        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider
        
        setup_tracing("test-service")
        
        mock_provider.add_span_processor.assert_called_once()