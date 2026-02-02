#!/bin/bash

echo "Cleaning up old port-forward processes..."
# Kill ANY kubectl port-forward processes (covers kubectl, kubectl1., etc.)
pkill -f "port-forward" 2>/dev/null || true

# Optional: wait 1 second to ensure ports are fully released
sleep 1

echo "Starting fresh port-forwards..."

# Prometheus
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090 >/tmp/pf-prometheus.log 2>&1 &
echo "Prometheus → http://localhost:9090"

# Grafana
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80 >/tmp/pf-grafana.log 2>&1 &
echo "Grafana → http://localhost:3000"

# Alertmanager
kubectl port-forward -n monitoring svc/kube-prometheus-stack-alertmanager 9093:9093 >/tmp/pf-alertmanager.log 2>&1 &
echo "Alertmanager → http://localhost:9093"

# InfluxDB
kubectl port-forward -n team4 svc/influxdb2 8086:80 >/tmp/pf-influxdb.log 2>&1 &
echo "InfluxDB → http://localhost:8086"

# Analytics Flask Service
kubectl port-forward -n team4 svc/analytics-service-analytics-service 8080:8080 >/tmp/pf-analytics.log 2>&1 &
echo "Analytics Service → http://localhost:8080/health"
echo "Analytics Service → http://localhost:8080/metrics"

# Elasticsearch
kubectl port-forward -n observability svc/elasticsearch-master 9200:9200 >/tmp/pf-elasticsearch.log 2>&1 &
echo "Elasticsearch is Up"

# Kibana
kubectl port-forward -n observability svc/kibana-kibana 5601:5601 >/tmp/pf-kibana.log 2>&1 &
echo "Kibana → http://localhost:5601"

echo "All port-forwarding started!"