import json
import time
import os
import logging
from datetime import datetime, timezone, timedelta

from kafka import KafkaConsumer
from opentelemetry import trace, propagate

# Local modules
from consumer.analytics_producer import publish_analytics
from consumer.influx_writer import write_event_ingest
from consumer.metrics import (
    # Core pipeline
    analytics_events_consumed_total,
    analytics_events_published_total,
    analytics_event_processing_latency_ms,
    analytics_processing_errors_total,
    analytics_event_validation_failures_total,
    analytics_events_in_flight,
    analytics_event_end_to_end_latency_ms,
    analytics_influx_writes_total,
    # Business
    analytics_orders_total,
    analytics_notifications_total,
    analytics_order_to_notification_latency_ms,
    analytics_user_created_total,
    analytics_user_updated_total,
    analytics_user_deleted_total,
    analytics_users_by_status,
    analytics_ordering_users_approx_total,
    analytics_user_to_first_order_latency_ms,
    analytics_first_order_to_first_notification_latency_ms,
    analytics_user_to_first_notification_latency_ms,
    # Stream liveness (NEW)
    analytics_topic_last_seen_seconds,
)
from consumer.cache import TTLDict, TTLSet

log = logging.getLogger("analytics-consumer")

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "team4-kafka-kafka-bootstrap.team4.svc:9092")
INPUT_TOPICS = [
    t.strip()
    for t in os.getenv("INPUT_TOPICS", "user-events,order-events,notification-events").split(",")
    if t.strip()
]
GROUP_ID = os.getenv("CONSUMER_GROUP", "analytics-consumer-group")
ENABLE_ANALYTICS = (os.getenv("ENABLE_ANALYTICS_TOPIC", "false").lower() == "true")

# Correlation & window settings
ORDER_STATE_TTL_SEC = int(os.getenv("ORDER_STATE_TTL_SEC", "7200"))  # 2h
USER_STATE_TTL_SEC = int(os.getenv("USER_STATE_TTL_SEC", "86400"))   # 24h
ORDERING_USERS_WINDOW_SEC = int(os.getenv("ORDERING_USERS_WINDOW_SEC", "3600"))  # 1h approx unique

IST = timezone(timedelta(hours=5, minutes=30))

# ------------------- TTL State for Correlations -------------------

# user_id -> user_created_ts_ms
_user_created_ts = TTLDict(ttl_seconds=USER_STATE_TTL_SEC, max_size=500_000)

# user_id -> last_known_status (UPPERCASE)
_user_status = TTLDict(ttl_seconds=USER_STATE_TTL_SEC, max_size=500_000)

# user_id observed first order? (long TTL to avoid double counting; or use USER_STATE_TTL_SEC)
_first_order_seen_users = TTLSet(ttl_seconds=7 * 24 * 3600, max_size=1_000_000)

# order_id -> { "user_id", "created_ts_ms", "confirmed_ts_ms", "shipped_ts_ms" }
_order_state = TTLDict(ttl_seconds=ORDER_STATE_TTL_SEC, max_size=1_000_000)

# order_id had first notification already computed?
_first_notification_seen_orders = TTLSet(ttl_seconds=ORDER_STATE_TTL_SEC, max_size=1_000_000)

# approx unique ordering users in the last window
_ordering_users_window = TTLSet(ttl_seconds=ORDERING_USERS_WINDOW_SEC, max_size=1_000_000)

# per-user last known order stage timestamps (fallback when order_id missing)
# user_id -> { "created_ts_ms", "confirmed_ts_ms", "shipped_ts_ms" }
_user_stage_ts = TTLDict(ttl_seconds=ORDER_STATE_TTL_SEC, max_size=1_000_000)


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
    if topic == "user-events":
        return {"event_name": "user_event", "producer": "user-service", "source_team": "team-1"}
    if topic == "order-events":
        status = (value.get("status") or "UNKNOWN").lower()
        return {"event_name": f"order_{status}", "producer": "order-service", "source_team": "team-2"}
    if topic == "notification-events":
        return {
            "event_name": value.get("event_name") or "notification_event",
            "producer": value.get("producer") or "notification-service",
            "source_team": "team-3",
        }
    return {"event_name": "unknown", "producer": "unknown", "source_team": "unknown"}


def parse_event_time_ms(topic, value):
    now_ms = int(time.time() * 1000)
    if topic in ("user-events", "order-events"):
        ts = value.get("created_at") or value.get("updated_at")
        if not ts:
            return now_ms
        try:
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
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S IST")
            dt = dt.replace(tzinfo=IST)
            return int(dt.timestamp() * 1000)
        except Exception:
            return now_ms

    return now_ms


def _to_upper_status(s: str) -> str:
    s = (s or "UNKNOWN").upper()
    if s not in ("ACTIVE", "INACTIVE", "SUSPENDED", "CREATED", "UPDATED", "DELETED", "UNKNOWN"):
        return s
    return s


def _order_status_lower(s: str) -> str:
    s = (s or "unknown").lower()
    if s not in ("created", "confirmed", "shipped", "cancelled", "unknown"):
        return "unknown"
    return s


def _notif_stage_from_template(template: str) -> str:
    t = (template or "").upper()
    if "CONFIRM" in t:
        return "confirmed"
    if "SHIP" in t:
        return "shipped"
    if "CANCEL" in t:
        return "cancelled"
    if "CREATE" in t or "PLACED" in t:
        return "created"
    return "unknown"


# --- Baseline gauges so Grafana never shows blank panels ---
def _init_metric_baselines():
    for s in ("ACTIVE", "INACTIVE", "SUSPENDED"):
        analytics_users_by_status.labels(status=s).set(0)
    analytics_ordering_users_approx_total.set(0)

_init_metric_baselines()


def start_consumer():
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
            log.info("kafka consumer connected", extra={"extra_fields": {"topics": INPUT_TOPICS, "group_id": GROUP_ID}})
            break
        except Exception:
            log.error("kafka connection failed, retrying", exc_info=True, extra={"extra_fields": {"bootstrap": BOOTSTRAP}})
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
                    proc_start = time.time()

                    topic = message.topic
                    value = message.value or {}

                    # NEW: Update stream liveness as soon as a message arrives for this topic
                    analytics_topic_last_seen_seconds.labels(topic=topic).set(time.time())

                    produced_ts_ms = parse_event_time_ms(topic, value)
                    consumed_ts_ms = int(time.time() * 1000)
                    e2e_latency_ms = max(0, consumed_ts_ms - produced_ts_ms)

                    parent_ctx = propagate.extract(message.headers, getter=getter)

                    try:
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
                                    extra={"extra": {"kafka": {"topic": topic}, "validation": {"missing_fields": missing}}},
                                )
                                raise ValueError(f"Invalid schema for {topic}, missing={missing}")

                            norm = normalize_event(topic, value)
                            span.set_attribute("event.name", norm["event_name"])
                            span.set_attribute("event.producer", norm["producer"])

                            analytics_events_consumed_total.labels(topic=topic).inc()
                            analytics_event_processing_latency_ms.labels(topic=topic).observe(
                                (time.time() - proc_start) * 1000
                            )
                            analytics_event_end_to_end_latency_ms.labels(topic=topic).observe(e2e_latency_ms)

                            # Persist to Influx (non-critical)
                            try:
                                with tracer.start_as_current_span("influx.write"):
                                    write_event_ingest(
                                        topic=topic,
                                        event_type=norm["event_name"],
                                        source_team=norm["source_team"],
                                        latency_ms=e2e_latency_ms,
                                        lag=0,
                                        ts_ms=consumed_ts_ms,
                                    )
                                analytics_influx_writes_total.labels(status="success").inc()
                            except Exception:
                                analytics_influx_writes_total.labels(status="failure").inc()
                                log.exception("influx write failed")

                            # --------- Business KPIs ---------
                            if topic == "user-events":
                                _handle_user_event(value, produced_ts_ms)
                            elif topic == "order-events":
                                _handle_order_event(value, produced_ts_ms)
                            elif topic == "notification-events":
                                _handle_notification_event(value, produced_ts_ms)

                            if ENABLE_ANALYTICS:
                                publish_analytics(
                                    topic=topic,
                                    lag=0,
                                    latency=e2e_latency_ms,
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
                                        "event_metrics": {"e2e_latency_ms": e2e_latency_ms},
                                    }
                                },
                            )

                    except Exception:
                        analytics_processing_errors_total.inc()
                        log.error("event processing error", exc_info=True, extra={"extra": {"kafka": {"topic": topic}}})
                    finally:
                        analytics_events_in_flight.dec()

        except Exception:
            log.error("consumer loop error", exc_info=True)
            time.sleep(1)


# ------------------- Business Handlers -------------------

def _handle_user_event(value: dict, event_ts_ms: int) -> None:
    user_id = value.get("user_id")
    if user_id is None:
        return

    if not _user_created_ts.has(user_id):
        _user_created_ts.set(user_id, event_ts_ms)
        analytics_user_created_total.inc()
    else:
        analytics_user_updated_total.inc()

    new_status = _to_upper_status(value.get("status"))
    prev_status = _user_status.get(user_id)
    if prev_status != new_status:
        if prev_status in ("ACTIVE", "INACTIVE", "SUSPENDED"):
            try:
                analytics_users_by_status.labels(status=prev_status).dec()
            except Exception:
                pass
        if new_status in ("ACTIVE", "INACTIVE", "SUSPENDED"):
            analytics_users_by_status.labels(status=new_status).inc()
        _user_status.set(user_id, new_status)

    if new_status == "DELETED":
        analytics_user_deleted_total.inc()
        if prev_status in ("ACTIVE", "INACTIVE", "SUSPENDED"):
            try:
                analytics_users_by_status.labels(status=prev_status).dec()
            except Exception:
                pass
        _user_status.pop(user_id)


def _handle_order_event(value: dict, event_ts_ms: int) -> None:
    order_id = value.get("id")
    user_id = value.get("user_id")
    status = _order_status_lower(value.get("status"))

    analytics_orders_total.labels(status=status).inc()

    if status == "created" and user_id is not None:
        _ordering_users_window.add(user_id)
        analytics_ordering_users_approx_total.set(_ordering_users_window.size())

        user_created_ts = _user_created_ts.get(user_id)
        if user_created_ts is not None and not _first_order_seen_users.contains(user_id):
            delta_ms = max(0, event_ts_ms - user_created_ts)
            analytics_user_to_first_order_latency_ms.observe(delta_ms)
            _first_order_seen_users.add(user_id)

    # Maintain order state timestamps to compute notif latencies later
    if order_id is not None:
        st = _order_state.get(order_id) or {}
        st.setdefault("user_id", user_id)
        if status == "created":
            st["created_ts_ms"] = event_ts_ms
        elif status == "confirmed":
            st["confirmed_ts_ms"] = event_ts_ms
        elif status == "shipped":
            st["shipped_ts_ms"] = event_ts_ms
        _order_state.set(order_id, st, ttl=ORDER_STATE_TTL_SEC)

    # per-user stage timestamps for fallback correlation
    if user_id is not None:
        ust = _user_stage_ts.get(user_id) or {}
        if status == "created":
            ust["created_ts_ms"] = event_ts_ms
        elif status == "confirmed":
            ust["confirmed_ts_ms"] = event_ts_ms
        elif status == "shipped":
            ust["shipped_ts_ms"] = event_ts_ms
        _user_stage_ts.set(user_id, ust, ttl=ORDER_STATE_TTL_SEC)


def _handle_notification_event(value: dict, event_ts_ms: int) -> None:
    data = value.get("data") or {}
    order_id = data.get("order_id")
    user_id = data.get("user_id")

    channel = (data.get("channel") or "unknown").upper()
    template = (data.get("template") or "unknown").upper()
    outcome = "sent" if (value.get("event_name") == "notification_sent" or data.get("status") == "SENT") else "failed"
    stage = _notif_stage_from_template(template)

    analytics_notifications_total.labels(
        outcome=outcome,
        channel=channel,
        template=template,
        stage=stage,
    ).inc()

    # Try exact order_id first
    st = _order_state.get(order_id) if order_id is not None else None

    # Fallback: per-user stage timestamps (if order unknown)
    if st is None and user_id is not None:
        ust = _user_stage_ts.get(user_id)
        if ust:
            st = ust  # same keys: created_ts_ms / confirmed_ts_ms / shipped_ts_ms

    if st:
        # Choose best stage timestamp based on label
        stage_ts = None
        if stage == "confirmed":
            stage_ts = st.get("confirmed_ts_ms") or st.get("created_ts_ms")
        elif stage == "shipped":
            stage_ts = st.get("shipped_ts_ms") or st.get("confirmed_ts_ms") or st.get("created_ts_ms")
        elif stage == "cancelled":
            stage_ts = st.get("created_ts_ms")
        elif stage == "created":
            stage_ts = st.get("created_ts_ms")
        else:
            stage_ts = st.get("shipped_ts_ms") or st.get("confirmed_ts_ms") or st.get("created_ts_ms")

        if stage_ts is not None:
            delta_ms = max(0, event_ts_ms - stage_ts)
            analytics_order_to_notification_latency_ms.labels(stage=stage, channel=channel, template=template).observe(delta_ms)

        # First order -> first notification latency (only if we know the order)
        if order_id is not None and not _first_notification_seen_orders.contains(order_id):
            created_ts = (_order_state.get(order_id) or {}).get("created_ts_ms")
            if created_ts is not None:
                analytics_first_order_to_first_notification_latency_ms.observe(max(0, event_ts_ms - created_ts))
            _first_notification_seen_orders.add(order_id)

    # Optional: user -> first notification (approx; may count multiple notifs)
    if user_id is not None:
        user_created_ts = _user_created_ts.get(user_id)
        if user_created_ts is not None:
            analytics_user_to_first_notification_latency_ms.observe(max(0, event_ts_ms - user_created_ts))