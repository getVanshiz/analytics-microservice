from flask import Flask, jsonify
import time
import os
import threading
import logging

from prometheus_flask_exporter import PrometheusMetrics
from consumer.consumer import start_consumer

app = Flask(__name__)
start_time = time.time()

# ---------- Prometheus ----------
metrics = PrometheusMetrics(app, path="/metrics")
metrics.info(
    "app_info",
    "Application info",
    version=os.getenv("APP_VERSION", "0.1.0"),
    service="analytics-service"
)

# ---------- Health endpoint ----------
@app.route("/health")
def health():
    uptime = time.time() - start_time
    return jsonify({
        "status": "ok",
        "service": "analytics-service",
        "uptime_seconds": round(uptime, 2),
        "version": os.getenv("APP_VERSION", "0.1.0")
    }), 200

# ---------- Kafka consumer thread ----------
def start_kafka_consumer():
    logging.info("[analytics-service] Starting Kafka consumer thread")
    try:
        start_consumer()
    except Exception as e:
        logging.exception("[analytics-service] Kafka consumer crashed")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    consumer_thread = threading.Thread(
        target=start_kafka_consumer,
        daemon=True
    )
    consumer_thread.start()

    logging.info("[analytics-service] Flask server starting on 0.0.0.0:8080")
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080"))
    )