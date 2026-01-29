import json
import logging
import sys
from datetime import datetime


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": "analytics-service",
            "message": record.getMessage(),
            "logger": record.name,
        }

        # trace_id support
        if hasattr(record, "trace_id"):
            log["trace_id"] = record.trace_id

        # Support BOTH patterns:
        # - extra={"extra": {...}}  (used in main.py)
        # - extra={"extra_fields": {...}} (used in consumer.py)
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log.update(record.extra)

        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            # Put them under a consistent key to avoid polluting top-level
            log.setdefault("fields", {})
            log["fields"].update(record.extra_fields)

        return json.dumps(log)


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]