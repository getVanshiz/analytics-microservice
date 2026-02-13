output "test_namespace" {
  description = "Test namespace name"
  value       = kubernetes_namespace_v1.test.metadata[0].name
}

output "analytics_service_url" {
  description = "Analytics service URL for testing"
  value       = "http://${kubernetes_service_v1.analytics_test.metadata[0].name}.${kubernetes_namespace_v1.test.metadata[0].name}.svc.cluster.local:8080"
}

output "kafka_bootstrap" {
  description = "Kafka bootstrap servers for tests"
  value       = "${helm_release.test_kafka.name}.${kubernetes_namespace_v1.test.metadata[0].name}.svc.cluster.local:9092"
}

output "influxdb_url" {
  description = "InfluxDB URL for tests"
  value       = "http://${helm_release.test_influxdb.name}.${kubernetes_namespace_v1.test.metadata[0].name}.svc.cluster.local"
}