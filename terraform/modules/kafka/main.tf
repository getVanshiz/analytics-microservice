
# Node pool / dual role (uses template file)
resource "kubernetes_manifest" "kafka_nodepool_dualrole" {
  manifest = yamldecode(
    templatefile("${path.module}/templates/kafka-nodepool.yaml", {
      namespace = var.namespace
      cluster   = var.cluster
    })
  )
}

# Kafka cluster (depends on nodepool)
resource "kubernetes_manifest" "kafka_cluster" {
  manifest = yamldecode(
    templatefile("${path.module}/templates/kafka-cluster.yaml", {
      namespace = var.namespace
      cluster   = var.cluster
    })
  )

  field_manager {
    name            = "terraform"
    force_conflicts = true
  }
  depends_on = [kubernetes_manifest.kafka_nodepool_dualrole]
}





output "cluster"   { value = var.cluster }
output "namespace" { value = var.namespace }
# Strimzi exposes a bootstrap service with a conventional name:
output "bootstrap_dns" { value = "${var.cluster}-kafka-bootstrap.${var.namespace}.svc.cluster.local:9092" }

