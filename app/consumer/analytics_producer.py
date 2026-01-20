import json
import os
import time
from kafka import KafkaProducer

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "team4-kafka-kafka-bootstrap.team4.svc:9092")
ANALYTICS_TOPIC = os.getenv("ANALYTICS_TOPIC", "analytics-events")

# Retry-able producer creation
def _new_producer():
    return KafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",
        retries=5
    )

_producer = None

def _get_producer():
    global _producer
    if _producer is None:
        _producer = _new_producer()
    return _producer

def publish_analytics(topic, lag, latency):
    event = {
        "event_id": f"analytics-{int(time.time()*1000)}",
        "event_type": "analytics_updated",
        "observed_topic": topic,
        "consumer_lag": lag,
        "latency_ms": latency,
        "produced_at": int(time.time() * 1000),
        "source_team": "team-4"
    }
    try:
        p = _get_producer()
        p.send(ANALYTICS_TOPIC, event)
    except Exception as e:
        # simple backoff/recreate producer on failure
        time.sleep(1.0)
        try:
            globals()["_producer"] = _new_producer()
        except Exception:
            pass
