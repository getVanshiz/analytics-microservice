# Database Schema — InfluxDB

## Purpose

InfluxDB stores derived analytics metrics for observability and trend analysis.

---

## Measurement: `event_ingest`

### Tags (Indexed)

| Tag | Description |
|----|-------------|
| topic | Kafka topic name |
| event_type | Normalized event name |
| source_team | Producing team |

---

### Fields

| Field | Type | Description |
|------|------|-------------|
| latency_ms | int | Event end-to-end latency |
| consumer_lag | int | Kafka consumer lag |

---

### Timestamp

- Event ingestion time (epoch milliseconds)

---

## Rationale

This schema enables:
- Time-series analysis
- Per-topic throughput
- Latency percentiles
- Cross-team analytics