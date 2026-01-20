
from kafka import KafkaConsumer, TopicPartition
import json, time, os, logging
from prometheus_client import Counter, Gauge
from consumer.metrics import (
    kafka_consumer_lag,
    kafka_message_latency_ms,
    kafka_messages_consumed_total
)
from consumer.analytics_producer import publish_analytics

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("analytics-consumer")

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "team4-kafka-kafka-bootstrap.team4.svc:9092")
ENABLE_ANALYTICS = os.getenv("ENABLE_ANALYTICS_TOPIC", "false").lower() == "true"
INPUT_TOPICS = [t.strip() for t in os.getenv(
    "INPUT_TOPICS", "user-events,order-events,notification-events").split(",") if t.strip()]
GROUP_ID = os.getenv("CONSUMER_GROUP", "observability-group")

analytics_events_published_total = Counter(
    "analytics_events_published_total",
    "Total analytics events published",
)

def start_consumer():
    # Retry loop to handle broker not available
    while True:
        try:
            consumer = KafkaConsumer(
                bootstrap_servers=BOOTSTRAP,
                group_id=GROUP_ID,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                # Let it block; rely on poll()
                # consumer_timeout_ms not needed here
                max_poll_records=500,
                # You can tune these if needed:
                # session_timeout_ms=10000,
                # max_poll_interval_ms=300000,
            )
            consumer.subscribe(INPUT_TOPICS)
            log.info(f"Consuming from topics: {INPUT_TOPICS} @ {BOOTSTRAP}")
            break
        except Exception as e:
            log.error(f"Kafka connection failed: {e}; retrying in 2s")
            time.sleep(2)

    while True:
        try:
            records = consumer.poll(timeout_ms=1000)  # wait up to 1s
            if not records:
                continue

            for tp, msgs in records.items():
                for message in msgs:
                    topic = message.topic
                    val = message.value or {}
                    produced_at = int(val.get("produced_at", int(time.time() * 1000)))
                    consumed_at = int(time.time() * 1000)
                    latency = max(0, consumed_at - produced_at)

                    # metrics
                    kafka_message_latency_ms.labels(topic=topic).set(latency)
                    kafka_messages_consumed_total.labels(topic=topic).inc()

                    # lag = end_offset - current_offset - 1
                    end_offset = consumer.end_offsets([tp]).get(tp, message.offset)
                    lag = max(0, end_offset - message.offset - 1)
                    kafka_consumer_lag.labels(topic=topic).set(lag)

                    if ENABLE_ANALYTICS:
                        publish_analytics(topic, lag, latency)
                        analytics_events_published_total.inc()

                    log.info(f"[{topic}] latency={latency}ms lag={lag} offset={message.offset}")

        except Exception as e:
            log.exception(f"Error processing message: {e}")
            time.sleep(0.2)
