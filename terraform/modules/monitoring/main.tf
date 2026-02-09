##############################################
# Module: monitoring (kube-prometheus-stack) #
##############################################

resource "helm_release" "monitoring" {
  name       = var.name
  repository = "oci://ghcr.io/prometheus-community/charts"
  chart      = "kube-prometheus-stack"
  version    = var.chart_version

  namespace        = var.namespace
  create_namespace = false

  # CRDs must be installed; let the chart install/upgrade them via hooks
  skip_crds = false

  # Make installs/upgrades resilient and idempotent
  cleanup_on_fail = true
  replace         = true
  force_update    = true
  wait            = true
  timeout         = 900

  # Expect callers to pass a rich map in var.values; encode to YAML once here
  values = [yamlencode(var.values)]
}

output "namespace" {
  value = var.namespace
}

output "grafana_service_dns" {
  value = "${var.name}-grafana.${var.namespace}.svc.cluster.local"
}

output "prometheus_service_dns" {
  value = "${var.name}-prometheus.${var.namespace}.svc.cluster.local"
}
