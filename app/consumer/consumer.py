import json
import time
import os
import logging
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

logging.basicConfig(level=logging.INFO)
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
    """
    Kafka consumer for Analytics Service.
    Consumes events from all upstream services and emits
    application-level metrics for observability.
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
            log.info(f"Consuming from topics: {INPUT_TOPICS}")
            break
        except Exception as e:
            log.error(f"Kafka connection failed: {e}. Retrying in 2s...")
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

                    try:
                        topic = message.topic
                        value = message.value or {}

                        # -------- Event validation --------
                        if (
                            "event_type" not in value
                            or "source_team" not in value
                        ):
                            analytics_event_validation_failures_total.inc()
                            raise ValueError("Invalid event schema")

                        produced_at = int(
                            value.get(
                                "produced_at",
                                int(time.time() * 1000)
                            )
                        )
                        consumed_at = int(time.time() * 1000)
                        latency_ms = max(0, consumed_at - produced_at)

                        # -------- Business metrics --------
                        analytics_events_consumed_total.labels(
                            topic=topic
                        ).inc()

                        analytics_event_processing_latency_ms.labels(
                            topic=topic
                        ).observe((time.time() - start_time) * 1000)

                        # -------- Persist to InfluxDB --------
                        write_event_ingest(
                            topic=topic,
                            event_type=value.get("event_type"),
                            source_team=value.get("source_team"),
                            latency_ms=latency_ms,
                            lag=0,  # Kafka lag handled by Kafka Exporter
                            ts_ms=consumed_at,
                        )

                        # -------- Optional analytics publish --------
                        if ENABLE_ANALYTICS:
                            publish_analytics(
                                topic=topic,
                                lag=0,
                                latency=latency_ms,
                            )
                            analytics_events_published_total.inc()

                        log.info(
                            f"[{topic}] type={value.get('event_type')} "
                            f"latency={latency_ms}ms"
                        )

                    except Exception as e:
                        analytics_processing_errors_total.inc()
                        log.exception(f"Error processing message: {e}")

                    finally:
                        analytics_events_in_flight.dec()

        except Exception as e:
            log.exception(f"Consumer loop error: {e}")
            time.sleep(1)