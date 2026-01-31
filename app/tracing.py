# app/tracing.py
from opentelemetry import trace, propagate
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
# ✅ Correct import path for Python OTLP exporter (traces)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
import os

SERVICE_NAME = "analytics-service"

def setup_tracing():
    resource = Resource.create({"service.name": SERVICE_NAME})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    # ✅ Prefer the standard TRACES endpoint if provided by Helm,
    #    then fallback to generic OTLP endpoint, finally to a correct in-cluster default.
    endpoint = (
        os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        or "http://otel-collector-opentelemetry-collector.monitoring.svc.cluster.local:4317"
    )

    # In-cluster OTLP gRPC typically uses plaintext; your Helm values set protocol=grpc.
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))

def inject_trace(headers: dict):
    propagate.inject(headers)  # W3C traceparent into headers

def extract_trace(headers: dict):
    return propagate.extract(headers)
