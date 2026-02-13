"""
Real integration tests for analytics service.
These tests run against actual services (not mocked) in the test namespace.
Tests: API -> Kafka -> Event Processing -> InfluxDB/Metrics

Test Environment: Isolated namespace with standalone Kafka, InfluxDB, and Analytics service
"""
import pytest
import requests
import json
import time
from kafka import KafkaProducer, KafkaConsumer
from influxdb_client import InfluxDBClient
import os


# Test Configuration - reads from environment (set by run-integration-tests.sh)
ANALYTICS_URL = os.getenv("ANALYTICS_URL", "http://analytics-service-test.analytics-test.svc.cluster.local:8080")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "test-kafka.analytics-test.svc.cluster.local:9092")
INFLUX_URL = os.getenv("INFLUX_URL", "http://test-influxdb.analytics-test.svc.cluster.local")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "test-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "test-org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "analytics-test")


@pytest.fixture(scope="session")
def kafka_producer():
    """Create Kafka producer for integration tests."""
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        acks='all',
        retries=3
    )
    yield producer
    producer.close()


@pytest.fixture(scope="session")
def influx_client():
    """Create InfluxDB client for verification."""
    client = InfluxDBClient(
        url=INFLUX_URL,
        token=INFLUX_TOKEN,
        org=INFLUX_ORG
    )
    yield client
    client.close()


@pytest.fixture(scope="session")
def analytics_consumer():
    """Create Kafka consumer for analytics-events topic."""
    consumer = KafkaConsumer(
        'analytics-events',
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset='latest',
        enable_auto_commit=True,
        group_id='integration-test-consumer',
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        consumer_timeout_ms=10000
    )
    yield consumer
    consumer.close()


class TestAPIHealthCheck:
    """Test API endpoints."""
    
    def test_health_endpoint(self):
        """Test /health endpoint returns 200."""
        response = requests.get(f"{ANALYTICS_URL}/health", timeout=5)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "analytics-service"
        assert "uptime_seconds" in data
    
    def test_metrics_endpoint(self):
        """Test /metrics endpoint is accessible."""
        response = requests.get(f"{ANALYTICS_URL}/metrics", timeout=5)
        assert response.status_code == 200
        assert "analytics_" in response.text  # Should contain custom metrics


class TestKafkaIntegration:
    """Test Kafka event publishing and consumption."""
    
    def test_publish_user_event(self, kafka_producer):
        """Test publishing a user event to Kafka."""
        event = {
            "user_id": 12345,
            "email": "integration-test@example.com",
            "status": "ACTIVE",
            "created_at": "2024-01-01T10:00:00+05:30Z",
            "updated_at": "2024-01-01T10:00:00+05:30Z",
        }
        
        # Publish event
        future = kafka_producer.send('user-events', value=event)
        metadata = future.get(timeout=10)
        
        # Verify publish succeeded
        assert metadata.topic == 'user-events'
        assert metadata.partition >= 0
        assert metadata.offset >= 0
    
    def test_publish_order_event(self, kafka_producer):
        """Test publishing an order event to Kafka."""
        event = {
            "id": "test-order-123",
            "order_id": 99999,
            "user_id": 12345,
            "item": "Integration Test Product",
            "quantity": 1,
            "status": "SHIPPED",
            "total": 999.99,
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:00:00Z"
        }
        
        future = kafka_producer.send('order-events', value=event)
        metadata = future.get(timeout=10)
        
        assert metadata.topic == 'order-events'
        assert metadata.offset >= 0
    
    def test_publish_notification_event(self, kafka_producer):
        """Test publishing a notification event to Kafka."""
        event = {
            "event_id": "test-notif-789",
            "event_version": "1.0",
            "event_name": "notification_sent",
            "producer": "notification-service",
            "user_id": 12345,
            "type": "EMAIL",
            "data": {"message": "Integration test notification"},
            "occurred_at": "2024-01-01 10:00:00 IST"
        }
        
        future = kafka_producer.send('notification-events', value=event)
        metadata = future.get(timeout=10)
        
        assert metadata.topic == 'notification-events'
        assert metadata.offset >= 0


class TestAnalyticsEventProduction:
    """Test that analytics service publishes analytics events."""
    
    def test_analytics_event_produced(self, kafka_producer, analytics_consumer):
        """Test end-to-end: publish event -> verify analytics event produced."""
        # Publish a user event
        test_user_id = int(time.time())  # Unique ID
        event = {
            "user_id": test_user_id,
            "email": f"test-{test_user_id}@example.com",
            "status": "ACTIVE",
            "created_at": "2024-01-01T10:00:00+05:30Z",
            "updated_at": "2024-01-01T10:00:00+05:30Z",
        }
        
        kafka_producer.send('user-events', value=event)
        kafka_producer.flush()
        
        # Wait for analytics service to process and publish
        time.sleep(5)
        
        # Consume analytics events
        analytics_events = []
        for message in analytics_consumer:
            analytics_events.append(message.value)
            if len(analytics_events) >= 5:  # Get a few events
                break
        
        # Verify at least one analytics event was published
        assert len(analytics_events) > 0
        
        # Verify structure of analytics events
        for event in analytics_events:
            assert "topic" in event
            assert "lag" in event
            assert "latency" in event


class TestInfluxDBIntegration:
    """Test InfluxDB metric writes."""
    
    def test_metrics_written_to_influxdb(self, kafka_producer, influx_client):
        """Test that metrics are written to InfluxDB after event processing."""
        # Publish test event
        test_user_id = int(time.time())
        event = {
            "user_id": test_user_id,
            "email": f"influx-test-{test_user_id}@example.com",
            "status": "ACTIVE",
            "created_at": "2024-01-01T10:00:00+05:30Z",
            "updated_at": "2024-01-01T10:00:00+05:30Z",
        }
        
        kafka_producer.send('user-events', value=event)
        kafka_producer.flush()
        
        # Wait for processing
        time.sleep(8)
        
        # Query InfluxDB for metrics
        query_api = influx_client.query_api()
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -5m)
          |> filter(fn: (r) => r["_measurement"] == "event_ingest")
          |> filter(fn: (r) => r["topic"] == "user-events")
          |> limit(n: 10)
        '''
        
        tables = query_api.query(query, org=INFLUX_ORG)
        
        # Verify data points exist
        records = []
        for table in tables:
            for record in table.records:
                records.append(record)
        
        assert len(records) > 0, "No metrics found in InfluxDB"
        
        # Verify metric fields
        for record in records[:1]:  # Check first record
            assert record.get_measurement() == "event_ingest"
            assert "topic" in record.values
            assert "event_type" in record.values or "source_team" in record.values


class TestEndToEndFlow:
    """Test complete end-to-end flow: API -> Kafka -> Processing -> Metrics."""
    
    def test_complete_user_event_flow(self, kafka_producer, influx_client, analytics_consumer):
        """Test complete flow for user event processing."""
        print("\n🚀 Starting end-to-end integration test...")
        
        # Step 1: Verify service health
        print("1️⃣ Checking service health...")
        response = requests.get(f"{ANALYTICS_URL}/health", timeout=5)
        assert response.status_code == 200
        print("   ✅ Service is healthy")
        
        # Step 2: Publish event to Kafka
        print("2️⃣ Publishing user event to Kafka...")
        test_user_id = int(time.time())
        event = {
            "user_id": test_user_id,
            "email": f"e2e-{test_user_id}@example.com",
            "status": "ACTIVE",
            "created_at": "2024-01-01T10:00:00+05:30Z",
            "updated_at": "2024-01-01T10:00:00+05:30Z",
        }
        
        kafka_producer.send('user-events', value=event)
        kafka_producer.flush()
        print(f"   ✅ Published event for user {test_user_id}")
        
        # Step 3: Wait for processing
        print("3️⃣ Waiting for event processing (10 seconds)...")
        time.sleep(10)
        
        # Step 4: Verify analytics event produced
        print("4️⃣ Checking analytics events...")
        analytics_events = []
        for message in analytics_consumer:
            analytics_events.append(message.value)
            if len(analytics_events) >= 3:
                break
        
        assert len(analytics_events) > 0, "No analytics events produced"
        print(f"   ✅ Found {len(analytics_events)} analytics events")
        
        # Step 5: Verify InfluxDB metrics
        print("5️⃣ Verifying InfluxDB metrics...")
        query_api = influx_client.query_api()
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -10m)
          |> filter(fn: (r) => r["_measurement"] == "event_ingest")
          |> limit(n: 20)
        '''
        
        tables = query_api.query(query, org=INFLUX_ORG)
        records = []
        for table in tables:
            for record in table.records:
                records.append(record)
        
        assert len(records) > 0, "No metrics in InfluxDB"
        print(f"   ✅ Found {len(records)} metric records in InfluxDB")
        
        print("\n✅ End-to-end integration test PASSED!")

