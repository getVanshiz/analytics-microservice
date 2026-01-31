#!/bin/bash

echo "🔄 Cleaning up old port-forward processes..."
pkill -f "kubectl port-forward" 2>/dev/null || true
sleep 1

echo "🚀 Starting fresh port-forwards..."

########################################
# 🔍 KIBANA (Elasticsearch + Logs UI)
########################################
kubectl port-forward -n monitoring svc/kibana-kibana 5601:5601 \
  >/tmp/pf-kibana.log 2>&1 &
echo "Kibana → http://localhost:5601"

########################################
# 🔎 JAEGER (Traces UI)
########################################
kubectl port-forward -n monitoring svc/jaeger 16686:16686 \
  >/tmp/pf-jaeger.log 2>&1 &
echo "Jaeger → http://localhost:16686"

########################################
# 📈 PROMETHEUS
########################################
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090 \
  >/tmp/pf-prometheus.log 2>&1 &
echo "Prometheus → http://localhost:9090"

########################################
# 📊 GRAFANA
########################################
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:3000 \
  >/tmp/pf-grafana.log 2>&1 &
echo "Grafana → http://localhost:3000  (login: admin / prom-operator)"

########################################
# 🚨 ALERTMANAGER
########################################
kubectl port-forward -n monitoring svc/kube-prometheus-stack-alertmanager 9093:9093 \
  >/tmp/pf-alertmanager.log 2>&1 &
echo "Alertmanager → http://localhost:9093"

########################################
# 📡 OTEL COLLECTOR METRICS (optional)
########################################
kubectl port-forward -n monitoring deploy/otel-collector-opentelemetry-collector 8888:8888 \
  >/tmp/pf-otel-metrics.log 2>&1 &
echo "OTel Collector Metrics → http://localhost:8888/metrics"

########################################
# 📦 INFLUXDB (Team4 namespace)
########################################
kubectl port-forward -n team4 svc/influxdb2 8086:80 \
  >/tmp/pf-influxdb.log 2>&1 &
echo "InfluxDB → http://localhost:8086"

########################################
# 🧪 ANALYTICS SERVICE (Team4)
########################################
kubectl port-forward -n team4 svc/analytics-service-analytics-service 8080:8080 \
  >/tmp/pf-analytics.log 2>&1 &
echo "Analytics Service → http://localhost:8080/health"

echo ""
echo "🎉 All port-forwarding started!"
echo "👉 Check /tmp/pf-*.log if any port fails."