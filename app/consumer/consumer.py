
from kafka import KafkaConsumer, TopicPartition
import json, time, os, logging
from prometheus_client import Counter, Gauge

from consumer.metrics import (
    kafka_consumer_lag,
    kafka_message_latency_ms,
    kafka_messages_consumed_total
)

from consumer.analytics_producer import publish_analytics
from consumer.influx_writer import write_event_ingest   

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("analytics-consumer")


BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "team4-kafka-kafka-bootstrap.team4.svc:9092")

ENABLE_ANALYTICS = os.getenv("ENABLE_ANALYTICS_TOPIC", "false").lower() == "true"

INPUT_TOPICS = [
    t.strip()
    for t in os.getenv("INPUT_TOPICS", "user-events,order-events,notification-events").split(",")
    if t.strip()
]

GROUP_ID = os.getenv("CONSUMER_GROUP", "observability-group")

analytics_events_published_total = Counter(
    "analytics_events_published_total",
    "Total analytics events published",
)


def start_consumer():
    """Start Kafka consumer with retry logic and event processing."""
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
            log.info(f"Consuming from topics: {INPUT_TOPICS} @ {BOOTSTRAP}")
            break
        except Exception as e:
            log.error(f"Kafka connection failed: {e}; retrying in 2s")
            time.sleep(2)

    while True:
        try:
            records = consumer.poll(timeout_ms=1000)

            if not records:
                continue

            for tp, msgs in records.items():
                for message in msgs:

                    topic = message.topic
                    val = message.value or {}

                    produced_at = int(val.get("produced_at", int(time.time() * 1000)))
                    consumed_at = int(time.time() * 1000)
                    latency = max(0, consumed_at - produced_at)

                    kafka_message_latency_ms.labels(topic=topic).set(latency)
                    kafka_messages_consumed_total.labels(topic=topic).inc()

                    end_offset = consumer.end_offsets([tp]).get(tp, message.offset)
                    lag = max(0, end_offset - message.offset - 1)
                    kafka_consumer_lag.labels(topic=topic).set(lag)

                    event_type = val.get("event_type", "unknown")
                    source_team = val.get("source_team", "unknown")

                    try:
                        write_event_ingest(
                            topic=topic,
                            event_type=event_type,
                            source_team=source_team,
                            latency_ms=latency,
                            lag=lag,
                            ts_ms=consumed_at
                        )
                    except Exception as influx_err:
                        log.warning(f"Influx write failed: {influx_err}")

                    if ENABLE_ANALYTICS:
                        publish_analytics(topic, lag, latency)
                        analytics_events_published_total.inc()

                    log.info(
                        f"[{topic}] type={event_type} latency={latency}ms "
                        f"lag={lag} offset={message.offset}"
                    )

        except Exception as e:
            log.exception(f"Error processing message: {e}, retrying...")
            time.sleep(0.2)

