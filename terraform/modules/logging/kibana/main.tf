resource "helm_release" "kibana" {
  name       = var.release_name
  namespace  = var.namespace
  repository = "https://helm.elastic.co"
  chart      = "kibana"
  version    = "8.5.1"               # <-- pin

  create_namespace = false
  values = [file("${path.module}/values.yaml")]

  atomic          = true
  cleanup_on_fail = true
  replace         = true
  force_update    = true
  wait            = true
  timeout         = 600

}