
resource "helm_release" "app" {
  name             = var.name
  chart            = var.chart_path
  namespace        = var.namespace
  create_namespace = false
  values           = [yamlencode(var.values)]
}

output "release_name" { value = helm_release.app.name }
output "namespace"    { value = var.namespace }
