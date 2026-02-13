"""
Unit tests for main Flask application.
Tests health endpoint, metrics, and basic app functionality.
"""
import pytest
import json
from unittest.mock import patch, MagicMock


@pytest.mark.unit
class TestHealthEndpoint:
    """Test the /health endpoint."""
    
    def test_health_endpoint_returns_200(self, client):
        """Test that health endpoint returns 200 status."""
        response = client.get('/health')
        assert response.status_code == 200
    
    def test_health_endpoint_json_format(self, client):
        """Test that health endpoint returns valid JSON."""
        response = client.get('/health')
        data = json.loads(response.data)
        assert isinstance(data, dict)
    
    def test_health_endpoint_required_fields(self, client):
        """Test that health endpoint contains all required fields."""
        response = client.get('/health')
        data = json.loads(response.data)
        
        assert 'status' in data
        assert 'service' in data
        assert 'uptime_seconds' in data
        assert 'version' in data
        
    def test_health_endpoint_status_ok(self, client):
        """Test that health endpoint reports status as ok."""
        response = client.get('/health')
        data = json.loads(response.data)
        assert data['status'] == 'ok'
    
    def test_health_endpoint_service_name(self, client):
        """Test that service name is correct."""
        response = client.get('/health')
        data = json.loads(response.data)
        assert data['service'] == 'analytics-service'
    
    def test_health_endpoint_uptime_positive(self, client):
        """Test that uptime is a positive number."""
        response = client.get('/health')
        data = json.loads(response.data)
        assert data['uptime_seconds'] >= 0
        assert isinstance(data['uptime_seconds'], (int, float))
    
    def test_health_endpoint_version_format(self, client):
        """Test that version is returned."""
        response = client.get('/health')
        data = json.loads(response.data)
        assert 'version' in data
        assert isinstance(data['version'], str)


@pytest.mark.unit
class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint."""
    
    def test_metrics_endpoint_exists(self, client):
        """Test that /metrics endpoint exists."""
        response = client.get('/metrics')
        assert response.status_code == 200
    
    def test_metrics_endpoint_content_type(self, client):
        """Test that metrics endpoint returns text/plain."""
        response = client.get('/metrics')
        assert 'text/plain' in response.content_type or 'text' in response.content_type
    
    def test_metrics_contains_app_info(self, client):
        """Test that metrics include app_info."""
        response = client.get('/metrics')
        data = response.data.decode('utf-8')
        assert 'app_info' in data


@pytest.mark.unit
class TestFlaskApp:
    """Test Flask app configuration."""
    
    def test_app_exists(self, flask_app):
        """Test that Flask app is created."""
        assert flask_app is not None
    
    def test_app_is_flask_instance(self, flask_app):
        """Test that app is a Flask instance."""
        from flask import Flask
        assert isinstance(flask_app, Flask)
    
    def test_app_testing_mode(self, flask_app):
        """Test that app is in testing mode."""
        assert flask_app.config['TESTING'] is True
