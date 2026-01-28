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
        }

        # trace_id support
        if hasattr(record, "trace_id"):
            log["trace_id"] = record.trace_id

        # structured extra fields
        if hasattr(record, "extra"):
            log.update(record.extra)

        return json.dumps(log)


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]