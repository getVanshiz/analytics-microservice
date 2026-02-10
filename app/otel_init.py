import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter


def _parse_resource_attrs(raw: str):
    attrs = {}
    for pair in (raw or "").split(","):
        pair = pair.strip()
        if pair and "=" in pair:
            k, v = pair.split("=", 1)
            attrs[k.strip()] = v.strip()
    return attrs


def setup_tracing(default_service_name: str):
    """
    Initializes global OTel tracer provider once.
    """
    service_name = os.getenv("OTEL_SERVICE_NAME", default_service_name)


    endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "otel-collector-opentelemetry-collector.monitoring.svc.cluster.local:4317",
    )
    insecure = os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true"

    resource_attrs = _parse_resource_attrs(os.getenv("OTEL_RESOURCE_ATTRIBUTES", ""))
    resource = Resource.create({"service.name": service_name, **resource_attrs})

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=insecure)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    return trace.get_tracer(service_name)