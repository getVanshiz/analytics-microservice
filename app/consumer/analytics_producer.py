
import json
from kafka import KafkaProducer
import os

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "team4-kafka-kafka-bootstrap.team4.svc:9092")
ANALYTICS_TOPIC = os.getenv("ANALYTICS_TOPIC", "analytics-events")

producer = KafkaProducer(
    bootstrap_servers=BOOTSTRAP,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def publish_analytics(topic, lag, latency):
    event = {
        "topic": topic,
        "consumer_lag": lag,
        "latency_ms": latency
    }
    producer.send(ANALYTICS_TOPIC, event)
