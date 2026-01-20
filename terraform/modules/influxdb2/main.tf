
resource "helm_release" "influxdb2" {
  name             = var.name
  repository       = "https://helm.influxdata.com"
  chart            = "influxdb2"
  namespace        = var.namespace
  create_namespace = false

  # Let root pass the values map; keep module generic
  values = [yamlencode(var.values)]
}

output "release_name" { value = helm_release.influxdb2.name }
output "namespace"    { value = var.namespace }
# A convenient service DNS (typical name = release)
output "service_dns"  { value = "${helm_release.influxdb2.name}.${var.namespace}.svc.cluster.local" }
