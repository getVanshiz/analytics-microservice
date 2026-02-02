resource "helm_release" "filebeat" {
  name       = var.release_name
  namespace  = var.namespace
  repository = "https://helm.elastic.co"
  chart      = "filebeat"
  version    = "8.5.1"               # <-- pin

  create_namespace = false
  values = [file("${path.module}/values.yaml")]

  wait    = true
  timeout = 600
}
