
scalar(rate(analytics_events_published_total[5m]))
/
scalar(sum(rate(kafka_messages_consumed_total[5m])))

## Panel 1 — Kafka Consumer Lag (per topic)
PromQL:
kafka_consumer_lag

## Panel 2 — Kafka Message Latency (per topic)
PromQL:
kafka_message_latency_ms

## Panel 3 — Kafka Messages Consumed Rate
PromQL:
rate(kafka_messages_consumed_total[1m])

## Panel 4 — Analytics Events Published Rate
PromQL:
rate(analytics_events_published_total[1m])


# 🎯 Section B — HTTP API Metrics
## Panel 5 — Request Rate
rate(flask_http_request_total[1m])

## Panel 6 — Request Duration (p95)
histogram_quantile(0.95, 
  sum(rate(flask_http_request_duration_seconds_bucket[5m])) 
  by (le, method, path)
)

## Panel 7 — Error Rate
sum(rate(flask_http_request_total{status!="200"}[5m]))


# 🎯 Section C — System Metrics
## Panel 8 — CPU Usage
rate(process_cpu_seconds_total[1m])
`
## Panel 9 — Memory Usage
process_resident_memory_bytes

## Panel 10 — GC Collections
rate(python_gc_collections_total[5m])