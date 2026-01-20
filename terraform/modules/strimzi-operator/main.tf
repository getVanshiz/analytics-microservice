resource "helm_release" "strimzi" {
  name             = var.name
  repository       = "oci://quay.io/strimzi-helm"
  chart            = "strimzi-kafka-operator"
  version          = var.chart_version
  namespace        = var.namespace
  create_namespace = false

  values = [
    yamlencode(var.values)
  ]
}


output "name"      { value = helm_release.strimzi.name }
output "namespace" { value = var.namespace }
