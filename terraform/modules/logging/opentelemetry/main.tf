resource "helm_release" "otel_collector" {
  name        = var.release_name
  namespace   = var.namespace
  repository  = "https://open-telemetry.github.io/opentelemetry-helm-charts"
  chart       = "opentelemetry-collector"
  version     = var.chart_version

  create_namespace = false
  values           = [file("${path.module}/values.yaml")]

  # Safer while stabilizing; switch to atomic=true once green
  wait             = true
  timeout          = 900
  atomic           = false
  cleanup_on_fail  = true
  replace          = true
  force_update     = true
}