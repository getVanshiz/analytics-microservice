import json
import logging
import sys
from datetime import datetime

from opentelemetry import trace


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": "analytics-service",
            "message": record.getMessage(),
            "logger": record.name,
        }

        if hasattr(record, "trace_id"):
            log["trace_id"] = record.trace_id

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.is_valid:
            log["otel_trace_id"] = format(ctx.trace_id, "032x")
            log["otel_span_id"] = format(ctx.span_id, "016x")

        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log.update(record.extra)

        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log.setdefault("fields", {})
            log["fields"].update(record.extra_fields)

        return json.dumps(log)


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]