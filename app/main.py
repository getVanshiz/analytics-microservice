from flask import Flask, jsonify, request   # + request for extra attributes
import time, os, threading, logging
from prometheus_flask_exporter import PrometheusMetrics

from app.consumer.consumer import start_consumer

# Milestone-4 additions
from app.logging_config import setup_logging
from app.tracing import setup_tracing

# ✨ NEW: Flask instrumentation
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry import trace

app = Flask(__name__)
start_time = time.time()

# Init logging & tracing (your functions)
setup_logging()
setup_tracing()
logger = logging.getLogger("analytics-service")

# ✨ Instrument Flask so each request becomes a server span
FlaskInstrumentor().instrument_app(app)

metrics = PrometheusMetrics(app, path="/metrics")
metrics.info(
    "app_info",
    "Application info",
    version=os.getenv("APP_VERSION", "0.1.0"),
    service="analytics-service"
)

@app.before_request
def _before_request():
    # (Optional) enrich the current span with request attributes
    span = trace.get_current_span()
    if span and span.is_recording():
        span.set_attribute("http.route", request.path)
        span.set_attribute("http.method", request.method)

@app.after_request
def _after_request(response):
    # (Optional) add status/duration to span
    span = trace.get_current_span()
    if span and span.is_recording():
        span.set_attribute("http.status_code", response.status_code)
        span.set_attribute("app.request_duration_ms", int((time.time() - start_time) * 1000))
    return response

@app.route("/health")
def health():
    uptime = time.time() - start_time
    logger.info("health check called")  # structured JSON via your logging_config
    return jsonify({
        "status": "ok",
        "service": "analytics-service",
        "uptime_seconds": round(uptime, 2),
        "version": os.getenv("APP_VERSION", "0.1.0")
    }), 200

def start_kafka_consumer():
    logger.info("Starting Kafka consumer thread")
    try:
        start_consumer()
    except Exception:
        logger.exception("Kafka consumer crashed")

if __name__ == "__main__":
    consumer_thread = threading.Thread(target=start_kafka_consumer, daemon=True)
    consumer_thread.start()

    logger.info("Flask server starting on 0.0.0.0:8080")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
