from prometheus_client import Gauge, Counter

kafka_consumer_lag=Gauge(
    "kafka_consumer_lag",
    "Number of messages waiting to be consumed",
    ["topic"]
)
kafka_message_latency_ms=Gauge(
    "kafka_message_latency_ms",
    "Latency between produce and consume time",
    ["topic"]
)

kafka_messages_consumed_total=Counter(
    "kafka_messages_consumed_total",
    "total messages consumed from Kafka",
    ["topic"]
)