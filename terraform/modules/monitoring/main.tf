
resource "helm_release" "monitoring" {
  name             = var.name
  repository       = "oci://ghcr.io/prometheus-community/charts"
  chart            = "kube-prometheus-stack"
  version          = var.chart_version
  namespace        = var.namespace
  create_namespace = false

  values = [yamlencode(var.values)]
}

output "namespace" { value = var.namespace }

output "grafana_service_dns" {
  value = "${var.name}-grafana.${var.namespace}.svc.cluster.local"
}

output "prometheus_service_dns" {
  value = "${var.name}-prometheus.${var.namespace}.svc.cluster.local"
}
