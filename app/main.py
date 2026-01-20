
from flask import Flask, jsonify
import time, os, threading
from prometheus_flask_exporter import PrometheusMetrics

from consumer.consumer import start_consumer 

app = Flask(__name__)
start_time = time.time()

metrics = PrometheusMetrics(app, path="/metrics")
metrics.info("app_info", "Application info", version=os.getenv("APP_VERSION", "0.1.0"), service="analytics-service")

@app.route("/health")
def health():
    uptime = time.time() - start_time
    return jsonify({
        "status": "ok",
        "service": "analytics-service",
        "uptime_seconds": round(uptime, 2),
        "version": os.getenv("APP_VERSION", "0.1.0")
    }), 200

def start_kafka_consumer():
    print("[analytics-service] Starting Kafka consumer thread...", flush=True)
    try:
        start_consumer()
    except Exception as e:
        import traceback
        print("[analytics-service] Consumer crashed:", e, flush=True)
        traceback.print_exc()

if __name__ == "__main__":
    consumer_thread = threading.Thread(target=start_kafka_consumer)
    consumer_thread.daemon = True
    consumer_thread.start()
    print("[analytics-service] Flask server starting on 0.0.0.0:8080", flush=True)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
