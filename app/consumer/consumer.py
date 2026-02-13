import json
import time
import os
import logging
from datetime import datetime, timezone, timedelta

from kafka import KafkaConsumer

from opentelemetry import trace, propagate

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

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "team4-kafka-kafka-bootstrap.team4.svc:9092")

INPUT_TOPICS = [
    t.strip()
    for t in os.getenv("INPUT_TOPICS", "user-events,order-events,notification-events").split(",")
    if t.strip()
]

GROUP_ID = os.getenv("CONSUMER_GROUP", "analytics-consumer-group")

ENABLE_ANALYTICS = (os.getenv("ENABLE_ANALYTICS_TOPIC", "false").lower() == "true")

IST = timezone(timedelta(hours=5, minutes=30))


class KafkaHeadersGetter:
    """
    Allows OTel propagator to extract trace context from kafka-python headers.
    message.headers => List[Tuple[str, bytes]]
    OpenTelemetry expects `get()` to return a LIST of string values.
    """
    def get(self, carrier, key):
        if not carrier:
            return []
        values = []
        for k, v in carrier:
            if k == key and v is not None:
                if isinstance(v, bytes):
                    values.append(v.decode("utf-8"))
                else:
                    values.append(str(v))
        return values

    def keys(self, carrier):
        return [k for k, _ in (carrier or [])]


def validate_schema(topic, value):
    """
    Validate based on schemas you shared.
    Returns list of missing fields.
    """
    if topic == "user-events":
        required = ["user_id", "email", "status", "created_at", "updated_at"]
    elif topic == "order-events":
        required = ["id", "user_id", "item", "quantity", "status", "created_at", "updated_at"]
    elif topic == "notification-events":
        required = ["event_name", "event_version", "event_id", "occurred_at", "producer", "data"]
    else:
        required = []

    return [k for k in required if k not in value]


def normalize_event(topic, value):
    """
    Normalize to common fields used by logs/Influx.
    """
    if topic == "user-events":
        return {
            "event_name": "user_event",
            "producer": "user-service",
            "source_team": "team-1",
        }

    if topic == "order-events":
        status = (value.get("status") or "UNKNOWN").lower()
        return {
            "event_name": f"order_{status}",
            "producer": "order-service",
            "source_team": "team-2",
        }

    if topic == "notification-events":
        return {
            "event_name": value.get("event_name") or "notification_event",
            "producer": value.get("producer") or "notification-service",
            "source_team": "team-3",
        }

    return {"event_name": "unknown", "producer": "unknown", "source_team": "unknown"}


def parse_event_time_ms(topic, value):
    """
    Convert event timestamp to epoch ms.
    - user/order: created_at or updated_at in ISO-like string
    - notification: occurred_at like "YYYY-MM-DD HH:MM:SS IST"
    """
    now_ms = int(time.time() * 1000)

    if topic in ("user-events", "order-events"):
        ts = value.get("created_at") or value.get("updated_at")
        if not ts:
            return now_ms
        try:
            # Your sample ends with "...+05:30Z" -> remove trailing Z for fromisoformat
            clean = ts[:-1] if ts.endswith("Z") else ts
            dt = datetime.fromisoformat(clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=IST)
            return int(dt.timestamp() * 1000)
        except Exception:
            return now_ms

    if topic == "notification-events":
        ts = value.get("occurred_at")
        if not ts:
            return now_ms
        try:
            # "YYYY-MM-DD HH:MM:SS IST"
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S IST")
            dt = dt.replace(tzinfo=IST)
            return int(dt.timestamp() * 1000)
        except Exception:
            return now_ms

    return now_ms


def start_consumer():
    """
    Kafka consumer for Analytics Service.
    Consumes events from all upstream services (schema-specific)
    and emits metrics/logs + tracing spans.
    """

    tracer = trace.get_tracer("analytics-consumer")
    getter = KafkaHeadersGetter()

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

        except Exception:
            log.error(
                "kafka connection failed, retrying",
                exc_info=True,
                extra={"extra_fields": {"bootstrap": BOOTSTRAP}},
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

                    topic = message.topic
                    value = message.value or {}

                    # Extract parent context from Kafka headers (traceparent)
                    parent_ctx = propagate.extract(message.headers, getter=getter)

                    try:
                        # IMPORTANT: Use extracted parent context as the parent of this span.
                        # No need for attach/detach if you pass context here.
                        with tracer.start_as_current_span(
                            "kafka.consume",
                            context=parent_ctx,
                            attributes={
                                "messaging.system": "kafka",
                                "messaging.destination": topic,
                                "messaging.destination_kind": "topic",
                                "messaging.operation": "process",
                                "kafka.partition": message.partition,
                                "kafka.offset": message.offset,
                            },
                        ) as span:

                            missing = validate_schema(topic, value)
                            if missing:
                                analytics_event_validation_failures_total.inc()
                                log.warning(
                                    "event validation failed",
                                    extra={
                                        "extra": {
                                            "kafka": {"topic": topic},
                                            "validation": {"missing_fields": missing},
                                        }
                                    },
                                )
                                raise ValueError(f"Invalid schema for {topic}, missing={missing}")

                            norm = normalize_event(topic, value)
                            span.set_attribute("event.name", norm["event_name"])
                            span.set_attribute("event.producer", norm["producer"])

                            produced_ts_ms = parse_event_time_ms(topic, value)
                            consumed_ts_ms = int(time.time() * 1000)
                            latency_ms = max(0, consumed_ts_ms - produced_ts_ms)

                            # Metrics
                            analytics_events_consumed_total.labels(topic=topic).inc()
                            analytics_event_processing_latency_ms.labels(topic=topic).observe(
                                (time.time() - start_time) * 1000
                            )

                            # Persist to Influx
                            with tracer.start_as_current_span("influx.write"):
                                write_event_ingest(
                                    topic=topic,
                                    event_type=norm["event_name"],
                                    source_team=norm["source_team"],
                                    latency_ms=latency_ms,
                                    lag=0,  # via exporter 
                                    ts_ms=consumed_ts_ms,
                                )

                            if ENABLE_ANALYTICS:
                                publish_analytics(
                                    topic=topic,
                                    lag=0,
                                    latency=latency_ms,
                                    trace_id=format(span.get_span_context().trace_id, "032x"),
                                )
                                analytics_events_published_total.inc()

                            log.info(
                                "event processed",
                                extra={
                                    "extra": {
                                        "kafka": {
                                            "topic": topic,
                                            "partition": message.partition,
                                            "offset": message.offset,
                                        },
                                        "event": {"name": norm["event_name"], "producer": norm["producer"]},
                                        "event_metrics": {"latency_ms": latency_ms},
                                    }
                                },
                            )

                    except Exception:
                        analytics_processing_errors_total.inc()
                        log.error(
                            "event processing error",
                            exc_info=True,
                            extra={"extra": {"kafka": {"topic": topic}}},
                        )

                    finally:
                        analytics_events_in_flight.dec()

        except Exception:
            log.error("consumer loop error", exc_info=True)
            time.sleep(1)