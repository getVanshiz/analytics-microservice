import json
import time
import os
import uuid
import logging
import traceback
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


def _log_fields(topic, event_type, source_team, **more):
    return {
        "event": {
            "name": event_type,
        },
        "kafka": {
            "topic": topic,
        },
        "source": {
            "team": source_team,
        },
        **more
    }


def start_consumer():
    """
    Kafka consumer for Analytics Service.
    Consumes events from all upstream services and emits
    application-level metrics and structured logs.
    """

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
                "kafka consumer connected",
                extra={
                    "extra_fields": {
                        "topics": INPUT_TOPICS,
                        "group_id": GROUP_ID,
                    }
                },
            )
            break

        except Exception as e:
            log.error(
                "kafka connection failed, retrying",
                exc_info=True,
                extra={
                    "extra_fields": {
                        "bootstrap": BOOTSTRAP,
                    }
                },
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

                    # -------- Trace ID handling --------
                    trace_id = value.get("trace_id", str(uuid.uuid4()))

                    try:
                        # -------- Log: event received --------
                        log.info(
                            "event received",
                            extra={
                                "trace_id": trace_id,
                                "extra": {
                                    "event": {
                                        "action": "received",
                                        "outcome": "unknown",
                                        "name": value.get("event_type"),
                                    },
                                    "kafka": {"topic": message.topic},
                                    "source": {"team": value.get("source_team")},
                                },
                            },
                        )


                        # -------- Event validation --------
                        if (
                            "event_type" not in value
                            or "source_team" not in value
                        ):
                            analytics_event_validation_failures_total.inc()

                            log.warning(
                                "event validation failed",
                                extra={
                                    "trace_id": trace_id,
                                    "extra": {
                                        "event": {
                                            "action": "validate",
                                            "outcome": "failure",
                                            "name": value.get("event_type"),
                                        },
                                        "kafka": {"topic": message.topic},
                                        "source": {"team": value.get("source_team")},
                                        # Avoid dumping full payload unless needed (can be huge/sensitive)
                                        "validation": {"missing_fields": ["event_type", "source_team"]},
                                    },
                                },
                            )

                            raise ValueError("Invalid event schema")

                        produced_at = int(
                            value.get(
                                "produced_at",
                                int(time.time() * 1000)
                            )
                        )
                        consumed_at = int(time.time() * 1000)
                        latency_ms = max(0, consumed_at - produced_at)

                        # -------- Metrics --------
                        analytics_events_consumed_total.labels(
                            topic=message.topic
                        ).inc()

                        analytics_event_processing_latency_ms.labels(
                            topic=message.topic
                        ).observe((time.time() - start_time) * 1000)

                        # -------- Persist to InfluxDB --------
                        write_event_ingest(
                            topic=message.topic,
                            event_type=value.get("event_type"),
                            source_team=value.get("source_team"),
                            latency_ms=latency_ms,
                            lag=0,  # Kafka lag via exporter
                            ts_ms=consumed_at,
                        )

                        # -------- Optional analytics publish --------
                        if ENABLE_ANALYTICS:
                            publish_analytics(
                                topic=message.topic,
                                lag=0,
                                latency=latency_ms,
                                trace_id=trace_id,
                            )
                            analytics_events_published_total.inc()

                        # -------- Log: success --------
                        log.info(
                            "event processed",
                            extra={
                                "trace_id": trace_id,
                                "extra": {
                                    "event": {
                                        "action": "processed",
                                        "outcome": "success",
                                        "name": value.get("event_type"),
                                    },
                                    "kafka": {"topic": message.topic},
                                    "source": {"team": value.get("source_team")},
                                    "event_metrics": {"latency_ms": latency_ms},
                                },
                            },
                        )

                    except Exception:
                        analytics_processing_errors_total.inc()

                        log.error(
                            "event processing error",
                            exc_info=True,
                            extra={
                                "trace_id": trace_id,
                                "extra": {
                                    "event": {
                                        "action": "processed",
                                        "outcome": "failure",
                                        "name": value.get("event_type"),
                                    },
                                    "kafka": {"topic": message.topic},
                                    "source": {"team": value.get("source_team")},
                                },
                            },
                        )

                    finally:
                        analytics_events_in_flight.dec()

        except Exception:
            log.error(
                "consumer loop error",
                exc_info=True,
            )
            time.sleep(1)