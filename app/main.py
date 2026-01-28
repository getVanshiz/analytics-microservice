from flask import Flask, jsonify
import time
import os
import threading
import logging

from prometheus_flask_exporter import PrometheusMetrics
from consumer.consumer import start_consumer
from logging_config import setup_logging


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
    logging.info(
        "Starting Kafka consumer thread",
        extra={"extra": {"component": "kafka-consumer"}}
    )
    try:
        start_consumer()
    except Exception:
        logging.exception("Kafka consumer crashed")


if __name__ == "__main__":
    setup_logging()

    logging.info(
        "Analytics service starting",
        extra={"extra": {"port": 8080}}
    )

    consumer_thread = threading.Thread(
        target=start_kafka_consumer,
        daemon=True
    )
    consumer_thread.start()

    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080"))
    )