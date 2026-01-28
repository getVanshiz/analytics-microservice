import json
import time
import os
import logging
import uuid
from kafka import KafkaConsumer

from consumer.analytics_producer import publish_analytics
from consumer.influx_writer import write_event_ingest
from consumer.metrics import (
    analytics_events_consumed_total,
    analytics_events_published_total,
    analytics_event_processing_latency_ms,
    analytics_processing_errors_total,
    analytics_event_validation_failures_total,
    analytics_events_in_flight,
)


log = logging.getLogger("analytics-consumer")

BOOTSTRAP = os.getenv(
    "KAFKA_BOOTSTRAP",
    "team4-kafka-kafka-bootstrap.team4.svc:9092"
)

INPUT_TOPICS = [
    t.strip()
    for t in os.getenv(
        "INPUT_TOPICS",
        "user-events,order-events,notification-events"
    ).split(",")
    if t.strip()
]

GROUP_ID = os.getenv("CONSUMER_GROUP", "analytics-consumer-group")

ENABLE_ANALYTICS = (
    os.getenv("ENABLE_ANALYTICS_TOPIC", "false").lower() == "true"
)


def start_consumer():
    # ---------- Kafka connection with retry ----------
    while True:
        try:
            consumer = KafkaConsumer(
                bootstrap_servers=BOOTSTRAP,
                group_id=GROUP_ID,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                max_poll_records=500,
            )
            consumer.subscribe(INPUT_TOPICS)

            log.info(
                "Kafka consumer connected",
                extra={"extra": {"topics": INPUT_TOPICS, "group": GROUP_ID}}
            )
            break

        except Exception as e:
            log.error(
                "Kafka connection failed, retrying",
                extra={"extra": {"bootstrap": BOOTSTRAP}}
            )
            time.sleep(2)

    # ---------- Main consume loop ----------
    while True:
        try:
            records = consumer.poll(timeout_ms=1000)
            if not records:
                continue

            for _, messages in records.items():
                for message in messages:
                    analytics_events_in_flight.inc()
                    start_time = time.time()

                    value = message.value or {}
                    topic = message.topic
                    trace_id = value.get("trace_id", str(uuid.uuid4()))

                    try:
                        # -------- Validation --------
                        if "event_type" not in value or "source_team" not in value:
                            analytics_event_validation_failures_total.inc()
                            log.error(
                                "Invalid event schema",
                                extra={
                                    "trace_id": trace_id,
                                    "extra": {"topic": topic, "event": value}
                                }
                            )
                            continue

                        produced_at = int(
                            value.get("produced_at", int(time.time() * 1000))
                        )
                        consumed_at = int(time.time() * 1000)
                        latency_ms = max(0, consumed_at - produced_at)

                        analytics_events_consumed_total.labels(topic=topic).inc()

                        analytics_event_processing_latency_ms.labels(
                            topic=topic
                        ).observe((time.time() - start_time) * 1000)

                        write_event_ingest(
                            topic=topic,
                            event_type=value.get("event_type"),
                            source_team=value.get("source_team"),
                            latency_ms=latency_ms,
                            lag=0,
                            ts_ms=consumed_at,
                        )

                        if ENABLE_ANALYTICS:
                            publish_analytics(
                                topic=topic,
                                lag=0,
                                latency=latency_ms,
                                trace_id=trace_id,
                            )
                            analytics_events_published_total.inc()

                        log.info(
                            "Event processed",
                            extra={
                                "trace_id": trace_id,
                                "extra": {
                                    "topic": topic,
                                    "event_type": value.get("event_type"),
                                    "latency_ms": latency_ms
                                }
                            }
                        )

                    except Exception:
                        analytics_processing_errors_total.inc()
                        log.exception(
                            "Error processing message",
                            extra={"trace_id": trace_id}
                        )

                    finally:
                        analytics_events_in_flight.dec()

        except Exception:
            log.exception("Consumer loop error")
            time.sleep(1)