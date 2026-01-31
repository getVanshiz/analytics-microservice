
resource "helm_release" "jaeger" {
  name             = var.release_name
  namespace        = var.namespace
  repository       = "https://jaegertracing.github.io/helm-charts"
  chart            = "jaeger"
  version          = var.chart_version

  create_namespace = false
  values           = [file("${path.module}/values.yaml")]

  atomic           = true
  cleanup_on_fail  = true
  replace          = true
  force_update     = true
  wait             = true
  timeout          = 600
}
