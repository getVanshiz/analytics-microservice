# Setup Instructions (Milestone 1)

## Prerequisites

- Rancher Desktop with Kubernetes enabled
- Terraform >= 1.5
- kubectl
- Helm
- nerdctl (containerd)

---

## Local Stack Deployment

```bash
cd terraform
terraform init
terraform apply

```
--- 
## Terraform provisions:
- Namespaces
- Kafka cluster and topics
- InfluxDB
- Analytics Service
- Prometheus & Grafana
- Elasticsearch, Kibana, Filebeat
- Jaeger & OpenTelemetry Collector

## Verification

```Bash
kubectl get pods -n team4
kubectl get kafkatopics -n team4
curl http://localhost:8080/health
curl http://localhost:8080/metrics
```

Expected:
```python
Pods in Running state
/health → 200 OK
```

---

