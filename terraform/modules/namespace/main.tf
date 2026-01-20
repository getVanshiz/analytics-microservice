
resource "kubernetes_namespace_v1" "ns" {
  metadata { name = var.name }
}

output "name" {
  value = kubernetes_namespace_v1.ns.metadata[0].name
}
