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

  # --- add these ---
  cleanup_on_fail = true
  replace         = true     # allow re-using the same release name if it exists in history
  force_update    = true     # push template changes even without version bump
  wait            = true
  timeout         = 600

  depends_on = [kubernetes_cluster_role.strimzi_secrets_manager]
}

# Grant Strimzi operator permission to manage secrets across all namespaces
resource "kubernetes_cluster_role" "strimzi_secrets_manager" {
  metadata {
    name = "strimzi-secrets-manager"
  }

  rule {
    api_groups = [""]
    resources  = ["secrets", "configmaps", "services", "serviceaccounts", "pods"]
    verbs      = ["create", "delete", "deletecollection", "get", "list", "patch", "update", "watch"]
  }

  rule {
    api_groups = ["apps"]
    resources  = ["deployments", "deployments/scale", "replicasets", "replicasets/scale", "statefulsets", "statefulsets/scale"]
    verbs      = ["create", "delete", "deletecollection", "get", "list", "patch", "update", "watch"]
  }
}

resource "kubernetes_cluster_role_binding" "strimzi_secrets_manager" {
  metadata {
    name = "strimzi-secrets-manager"
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.strimzi_secrets_manager.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = "strimzi-cluster-operator"
    namespace = var.namespace
  }
}
