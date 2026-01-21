
import os, time
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS

_INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb2.team4.svc:80")
_INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
_INFLUX_ORG = os.getenv("INFLUX_ORG", "team4")
_INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "analytics")

_client = None
_write_api = None

def _get_write_api():
    global _client, _write_api
    if _write_api is None:
        _client = InfluxDBClient(url=_INFLUX_URL, token=_INFLUX_TOKEN, org=_INFLUX_ORG, timeout=5000)
        _write_api = _client.write_api(write_options=SYNCHRONOUS)  # reliable; dev-size load
    return _write_api

def write_event_ingest(topic: str, event_type: str, source_team: str, latency_ms: int, lag: int, ts_ms: int):
    p = Point("event_ingest") \
        .tag("topic", topic) \
        .tag("event_type", event_type) \
        .tag("source_team", source_team) \
        .field("latency_ms", int(latency_ms)) \
        .field("consumer_lag", int(lag)) \
        .time(int(ts_ms) * 1_000_000)  # ms -> ns
    try:
        _get_write_api().write(bucket=_INFLUX_BUCKET, record=p)
    except Exception as e:
        # swallow, log, and continue; do not crash consumer
        import logging; logging.getLogger("analytics-consumer").warning(f"Influx write failed: {e}")
