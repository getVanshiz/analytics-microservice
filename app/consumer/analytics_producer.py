import json
import os
import time
import logging
from kafka import KafkaProducer

from opentelemetry import propagate, trace

log = logging.getLogger("analytics-producer")

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "team4-kafka-kafka-bootstrap.team4.svc:9092")
ANALYTICS_TOPIC = os.getenv("ANALYTICS_TOPIC", "analytics-events")


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


def publish_analytics(topic, lag, latency, trace_id):
    """
    Publishes analytics events and propagates current OTel context via Kafka headers.
    `trace_id` is kept as your business field (optional).
    """
    event = {
        "event_id": f"analytics-{int(time.time()*1000)}",
        "trace_id": trace_id,
        "event_type": "analytics_updated",
        "observed_topic": topic,
        "consumer_lag": lag,
        "latency_ms": latency,
        "produced_at": int(time.time() * 1000),
        "source_team": "team-4"
    }

    tracer = trace.get_tracer("analytics-producer")

    try:
        with tracer.start_as_current_span(
            "kafka.produce",
            attributes={
                "messaging.system": "kafka",
                "messaging.destination": ANALYTICS_TOPIC,
                "messaging.destination_kind": "topic",
                "messaging.operation": "publish",
                "observed_topic": topic,
            },
        ):
            carrier = {}
            propagate.inject(carrier)
            headers = [(k, str(v).encode("utf-8")) for k, v in carrier.items()]

            p = _get_producer()

            # Option A: fire-and-forget
            # p.send(ANALYTICS_TOPIC, event, headers=headers)

            # Option B: wait for ack (better for debugging)
            p.send(ANALYTICS_TOPIC, event, headers=headers).get(timeout=10)

    except Exception:
        log.error(
            "Failed to publish analytics event",
            exc_info=True,
            extra={"extra": {"topic": ANALYTICS_TOPIC}}
        )
        time.sleep(1)
        try:
            globals()["_producer"] = _new_producer()
        except Exception:
            pass