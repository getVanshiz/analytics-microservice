import logging
import json
from datetime import datetime
from opentelemetry.trace import get_current_span

SERVICE_NAME = "analytics-service"

class JsonFormatter(logging.Formatter):
    def format(self, record):
        span = get_current_span()
        trace_id = None

        if span:
            ctx = span.get_span_context()
            if ctx.is_valid:
                trace_id = format(ctx.trace_id, "032x")

        log = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "message": record.getMessage(),
            "trace_id": trace_id,
        }

        # optional domain fields
        if hasattr(record, "domain"):
            log.update(record.domain)

        return json.dumps(log)

def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]
    logging.getLogger("kafka").setLevel(logging.WARNING)