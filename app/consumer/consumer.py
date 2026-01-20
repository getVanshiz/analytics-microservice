
from kafka import KafkaConsumer, TopicPartition
import json
import time
from consumer.metrics import (
    kafka_consumer_lag,
    kafka_message_latency_ms,
    kafka_messages_consumed_total
)
from consumer.analytics_producer import publish_analytics

import os
ENABLE_ANALYTICS = os.getenv("ENABLE_ANALYTICS_TOPIC", "false").lower() == "true"

# later in loop:

def start_consumer():
    consumer = KafkaConsumer(
        "order-events",
        bootstrap_servers="team4-kafka-kafka-bootstrap.team4.svc:9092",
        group_id="observability-group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8"))
    )

    for message in consumer:
        topic = message.topic

        produced_at = message.value["produced_at"]
        consumed_at = int(time.time() * 1000)

        latency = consumed_at - produced_at

        kafka_message_latency_ms.labels(topic=topic).set(latency)
        kafka_messages_consumed_total.labels(topic=topic).inc()

        tp = TopicPartition(topic, message.partition)
        end_offset = consumer.end_offsets([tp])[tp]
        lag = end_offset - message.offset - 1

        kafka_consumer_lag.labels(topic=topic).set(lag)

        if ENABLE_ANALYTICS:
            publish_analytics(topic, lag, latency)

        print(f"[{topic}] latency={latency}ms lag={lag}")





