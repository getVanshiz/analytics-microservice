# Team-4 Analytics Service

The Analytics Service is part of a multi-team, event-driven microservices system deployed locally on Kubernetes using Terraform and Helm.
Team-4 is responsible for aggregating events from all upstream services and providing system-wide observability through metrics, logs, and distributed tracing.

---

## Responsibilities

- Consume Kafka events from all teams
- Validate and normalize event schemas
- Measure event latency, throughput, and failures
- Store derived analytics data in InfluxDB
- Expose Prometheus metrics
- Emit structured logs to Elasticsearch
- Emit distributed traces via OpenTelemetry to Jaeger

---

## Tech Stack

- Kubernetes (Rancher Desktop)
- Terraform (IaC)
- Helm (Packaging)
- Apache Kafka (Strimzi)
- Prometheus & Grafana (Metrics)
- Elasticsearch, Kibana, Filebeat (Logs)
- OpenTelemetry & Jaeger (Tracing)
- InfluxDB (Time-series analytics)
- Python (Flask)

---

## Endpoints

| Endpoint | Description |
|--------|------------|
| `/health` | Liveness & readiness |
| `/metrics` | Prometheus metrics |

---

## Cluster Overview
<img src="../images/image.png"/>

--- 
## Quick Start

- First create image of analytics-service
```bash
nerdctl --namespace k8s.io build -t analytics-service:latest -f docker/Dockerfile .
```
- Then apply terraform 
```bash
cd terraform
terraform init
terraform apply
```

## Validation Checklist
- All pods in team4, monitoring, observability namespaces are running
- /health returns HTTP 200
- /metrics exposes Prometheus metrics
- Kafka topics exist
- Grafana, Kibana, Jaeger dashboards accessible