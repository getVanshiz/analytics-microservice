output "test_namespace" {
  description = "Test namespace name"
  value       = kubernetes_namespace_v1.test.metadata[0].name
}

output "analytics_service_url" {
  description = "Analytics service URL for testing"
  value       = "http://${kubernetes_service_v1.analytics_test.metadata[0].name}.${kubernetes_namespace_v1.test.metadata[0].name}.svc.cluster.local:8080"
}

output "kafka_bootstrap" {
  description = "Kafka bootstrap servers (existing from team4)"
  value       = "team4-kafka-kafka-bootstrap.team4.svc.cluster.local:9092"
}

output "influxdb_url" {
  description = "InfluxDB URL (existing from team4)"
  value       = "http://influxdb2.team4.svc.cluster.local"
}