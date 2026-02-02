from prometheus_client import Counter, Histogram, Gauge

# 1. Events consumed (business KPI)
analytics_events_consumed_total = Counter(
    "analytics_events_consumed_total",
    "Total events consumed by analytics service",
    ["topic"]
)

# 2. Events published
analytics_events_published_total = Counter(
    "analytics_events_published_total",
    "Total analytics events published"
)

# 3. Event processing latency
analytics_event_processing_latency_ms = Histogram(
    "analytics_event_processing_latency_ms",
    "Time taken to process an event (ms)",
    ["topic"],
    buckets=(10, 50, 100, 200, 500, 1000, 2000)
)

# 4. InfluxDB write success/failure
analytics_influx_writes_total = Counter(
    "analytics_influx_writes_total",
    "Total InfluxDB writes",
    ["status"]  # success | failure
)

# 5. Consumer processing errors
analytics_processing_errors_total = Counter(
    "analytics_processing_errors_total",
    "Total errors while processing analytics events"
)

# 6. Event validation failures (bad schema / missing fields)
analytics_event_validation_failures_total = Counter(
    "analytics_event_validation_failures_total",
    "Total invalid events received by analytics service"
)

# 7. In-flight events (load indicator)
analytics_events_in_flight = Gauge(
    "analytics_events_in_flight",
    "Number of events currently being processed"
)