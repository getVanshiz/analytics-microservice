from prometheus_client import Counter, Histogram, Gauge

# =========================
# Pipeline / Processing KPIs (Team 4 Core)
# =========================

# 1. Events consumed (by topic)
analytics_events_consumed_total = Counter(
    "analytics_events_consumed_total",
    "Total events consumed by analytics service",
    ["topic"]
)

# 2. Events published (optional analytics topic)
analytics_events_published_total = Counter(
    "analytics_events_published_total",
    "Total analytics events published"
)

# 3. Event local processing latency (handler time, not end-to-end)
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

# 8. End-to-end freshness (producer -> analytics consumer)
analytics_event_end_to_end_latency_ms = Histogram(
    "analytics_event_end_to_end_latency_ms",
    "End-to-end event latency (ms) from event production to analytics consumption",
    ["topic"],
    buckets=(10, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 30000, 60000)
)

# =========================
# Business KPIs (Cross-Team)
# =========================

# ---- Orders ----
# Count of orders by status (created/confirmed/shipped/cancelled/unknown)
analytics_orders_total = Counter(
    "analytics_orders_total",
    "Count of orders observed by Analytics, partitioned by order status",
    ["status"]  # created|confirmed|shipped|cancelled|unknown
)

# Order-stage -> notification latency (e.g., confirmed -> notif, shipped -> notif)
analytics_order_to_notification_latency_ms = Histogram(
    "analytics_order_to_notification_latency_ms",
    "Latency from order stage to notification (ms)",
    ["stage", "channel", "template"],  # stage: confirmed|shipped|created|unknown
    buckets=(50, 100, 200, 500, 1000, 2000, 5000, 10000, 30000)
)

# ---- Notifications ----
# Notification outcome by channel/template/stage (stage if known from order context)
analytics_notifications_total = Counter(
    "analytics_notifications_total",
    "Notifications observed by Analytics",
    ["outcome", "channel", "template", "stage"]  # outcome: sent|failed
)

# ---- Users ----
# User lifecycle counters
analytics_user_created_total = Counter(
    "analytics_user_created_total",
    "User created events observed"
)
analytics_user_updated_total = Counter(
    "analytics_user_updated_total",
    "User updated events observed"
)
analytics_user_deleted_total = Counter(
    "analytics_user_deleted_total",
    "User deleted events observed"
)

# Gauge of users by status (maintained from user-events: ACTIVE/INACTIVE/SUSPENDED)
analytics_users_by_status = Gauge(
    "analytics_users_by_status",
    "Current number of users by status (ACTIVE/INACTIVE/SUSPENDED)",
    ["status"]
)

# Approx unique users that placed orders in a rolling window (maintained in-memory)
analytics_ordering_users_approx_total = Gauge(
    "analytics_ordering_users_approx_total",
    "Approx unique users who placed orders in the configured window"
)

# ---- Customer Journey ----
# User -> first order latency
analytics_user_to_first_order_latency_ms = Histogram(
    "analytics_user_to_first_order_latency_ms",
    "Latency from user creation to user's first order (ms)",
    buckets=(1000, 5000, 15000, 30000, 60000, 120000, 300000, 600000)
)

# First order -> first notification latency
analytics_first_order_to_first_notification_latency_ms = Histogram(
    "analytics_first_order_to_first_notification_latency_ms",
    "Latency from first order to first notification (ms)",
    buckets=(100, 500, 1000, 2000, 5000, 10000, 30000)
)

# Optional: direct user -> first notification
analytics_user_to_first_notification_latency_ms = Histogram(
    "analytics_user_to_first_notification_latency_ms",
    "Latency from user creation to first notification (ms)",
    buckets=(1000, 5000, 15000, 30000, 60000, 120000, 300000, 600000)
)

analytics_topic_last_seen_seconds = Gauge(
    "analytics_topic_last_seen_seconds",
    "Unix timestamp when this topic was last seen",
    ["topic"]
)