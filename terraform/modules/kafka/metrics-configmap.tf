
resource "kubernetes_manifest" "kafka_metrics_cm" {
  manifest = {
    apiVersion = "v1"
    kind       = "ConfigMap"
    metadata = {
      name      = "${var.cluster}-metrics"
      namespace = var.namespace
    }
    data = {
      "metrics-config.yml" = <<-EOF
        lowercaseOutputName: true
        rules:
          - pattern: "kafka.server<type=BrokerTopicMetrics, name=(.*)><>Count"
            name: kafka_server_brokertopicmetrics_$1_count
        EOF
    }
  }
}
