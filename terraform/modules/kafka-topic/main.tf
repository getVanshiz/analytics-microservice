
resource "kubernetes_manifest" "topic" {
  manifest = {
    apiVersion = "kafka.strimzi.io/v1beta2"
    kind       = "KafkaTopic"
    metadata = {
      name      = var.name
      namespace = var.namespace
      labels = {
        "strimzi.io/cluster" = var.cluster
      }
    }
    
    
    spec = {
      partitions = var.partitions
      replicas   = var.replicas
      config     = {}
      topicName  = var.topicName != null ? var.topicName : var.name
    }

  }
}

output "name" { value = var.name }
