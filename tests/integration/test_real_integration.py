"""
Real integration tests for analytics service.
These tests run against actual services (not mocked) in the test namespace.
Tests: API connectivity and basic service health (READ-ONLY)

Test Environment: Reuses existing Kafka and InfluxDB (read-only mode)
"""
import pytest
import requests
import os


# Test Configuration - reads from environment (set by run-integration-tests.sh)
ANALYTICS_URL = os.getenv("ANALYTICS_URL", "http://analytics-service-test.analytics-test.svc.cluster.local:8080")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "team4-kafka-kafka-bootstrap.team4.svc.cluster.local:9092")
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb2.team4.svc.cluster.local")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "team4-dev-admin-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "team4")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "analytics")


class TestAPIHealthCheck:
    """Test API endpoints are accessible."""
    
    def test_health_endpoint(self):
        """Test that health endpoint is accessible and returns 200."""
        response = requests.get(f"{ANALYTICS_URL}/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "ok"]
    
    def test_metrics_endpoint(self):
        """Test that metrics endpoint is accessible."""
        response = requests.get(f"{ANALYTICS_URL}/metrics", timeout=5)
        assert response.status_code == 200
        # Prometheus metrics should contain some data
        assert len(response.text) > 0


class TestKafkaConnectivity:
    """Test Kafka connectivity from test environment."""
    
    def test_kafka_connection(self):
        """Test that the analytics service can connect to Kafka."""
        from kafka import KafkaAdminClient
        from kafka.errors import KafkaError
        
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                request_timeout_ms=5000
            )
            topics = admin_client.list_topics()
            admin_client.close()
            
            # Verify we can list topics
            assert len(topics) > 0
            print(f"✅ Connected to Kafka, found {len(topics)} topics")
        except KafkaError as e:
            pytest.fail(f"Failed to connect to Kafka: {e}")


class TestInfluxDBConnectivity:
    """Test InfluxDB connectivity from test environment."""
    
    def test_influxdb_connection(self):
        """Test that we can connect to InfluxDB and query data."""
        from influxdb_client import InfluxDBClient
        
        client = InfluxDBClient(
            url=INFLUX_URL,
            token=INFLUX_TOKEN,
            org=INFLUX_ORG,
            timeout=5000
        )
        
        try:
            # Simple health check
            health = client.health()
            assert health.status == "pass"
            print(f"✅ Connected to InfluxDB, status: {health.status}")
            
            # Try to query recent data (read-only)
            query_api = client.query_api()
            query = f'''
            from(bucket: "{INFLUX_BUCKET}")
              |> range(start: -1h)
              |> limit(n: 1)
            '''
            
            tables = query_api.query(query, org=INFLUX_ORG)
            
            # We don't assert data exists (might be empty), just that query works
            record_count = sum(len(table.records) for table in tables)
            print(f"✅ Successfully queried InfluxDB, found {record_count} recent records")
            
        finally:
            client.close()


class TestServiceConfiguration:
    """Test that the analytics service is properly configured."""
    
    def test_environment_variables(self):
        """Verify test configuration is correct."""
        # Verify all required env vars are set
        assert ANALYTICS_URL is not None
        assert KAFKA_BOOTSTRAP is not None
        assert INFLUX_URL is not None
        assert INFLUX_TOKEN is not None
        assert INFLUX_ORG is not None
        assert INFLUX_BUCKET is not None
        
        # Verify URLs are properly formatted
        assert ANALYTICS_URL.startswith("http://")
        assert KAFKA_BOOTSTRAP.endswith(":9092")
        assert INFLUX_URL.startswith("http://")
        
        print("✅ All environment variables configured correctly")


class TestEndToEndConnectivity:
    """Test complete connectivity flow (read-only)."""
    
    def test_complete_connectivity_check(self):
        """Verify all services are reachable from test environment."""
        print("\n🚀 Starting connectivity validation...")
        
        # Step 1: Check analytics service health
        print("1️⃣ Checking analytics service...")
        response = requests.get(f"{ANALYTICS_URL}/health", timeout=5)
        assert response.status_code == 200
        print("   ✅ Analytics service is healthy")
        
        # Step 2: Check Kafka connectivity
        print("2️⃣ Checking Kafka connectivity...")
        from kafka import KafkaAdminClient
        
        admin_client = KafkaAdminClient(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            request_timeout_ms=5000
        )
        topics = admin_client.list_topics()
        admin_client.close()
        assert len(topics) > 0
        print(f"   ✅ Connected to Kafka ({len(topics)} topics)")
        
        # Step 3: Check InfluxDB connectivity
        print("3️⃣ Checking InfluxDB connectivity...")
        from influxdb_client import InfluxDBClient
        
        client = InfluxDBClient(
            url=INFLUX_URL,
            token=INFLUX_TOKEN,
            org=INFLUX_ORG,
            timeout=5000
        )
        
        health = client.health()
        assert health.status == "pass"
        client.close()
        print("   ✅ Connected to InfluxDB")
        
        print("\n✅ All connectivity checks passed!")

