
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.25.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.10.1"
    }
  }
}

# Kubernetes provider
provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = "rancher-desktop"
}

# Helm provider - use ARGUMENT (map) form for kubernetes auth
provider "helm" {
  kubernetes = {
    config_path    = "~/.kube/config"
    config_context = "rancher-desktop"
  }
}

# Namespace: use v1 resource
resource "kubernetes_namespace_v1" "team4" {
  metadata { name = "team4" }
}

# --- InfluxDB v2 via official Helm chart ---
resource "helm_release" "influxdb2" {
  name             = "influxdb2"
  repository       = "https://helm.influxdata.com"
  chart            = "influxdb2"
  namespace        = kubernetes_namespace_v1.team4.metadata[0].name
  create_namespace = false

  values = [yamlencode({
    persistence = { enabled = false } # ephemeral for dev
    adminUser = {
      user         = "admin"
      password     = "admin123"
      token        = "team4-dev-admin-token"
      organization = "team4-org"
      bucket       = "team4-bucket"
    }
    service = { type = "ClusterIP" }
  })]
}

# --- Strimzi Cluster Operator via Helm (OCI) ---
resource "helm_release" "strimzi_operator" {
  name             = "strimzi-operator"
  repository       = "oci://quay.io/strimzi-helm"
  chart            = "strimzi-kafka-operator"
  version          = "0.49.1"
  namespace        = kubernetes_namespace_v1.team4.metadata[0].name
  create_namespace = false
}

# --- Single-broker Kafka (KRaft) using Strimzi CRs ---
resource "kubernetes_manifest" "kafka_nodepool_dualrole" {
  manifest = yamldecode(templatefile("${path.module}/manifests/kafka-nodepool.yaml", {
    namespace = kubernetes_namespace_v1.team4.metadata[0].name
    cluster   = "team4-kafka"
  }))
  depends_on = [helm_release.strimzi_operator]
}

resource "kubernetes_manifest" "kafka_cluster" {
  manifest = yamldecode(templatefile("${path.module}/manifests/kafka-cluster.yaml", {
    namespace = kubernetes_namespace_v1.team4.metadata[0].name
    cluster   = "team4-kafka"
  }))
  depends_on = [kubernetes_manifest.kafka_nodepool_dualrole]
}

# Optional: create one topic to validate cluster
resource "kubernetes_manifest" "kafka_topic_analytics" {
  manifest = yamldecode(templatefile("${path.module}/manifests/kafka-topic.yaml", {
    namespace = kubernetes_namespace_v1.team4.metadata[0].name
    cluster   = "team4-kafka"
    name      = "analytics-events"
  }))
  depends_on = [kubernetes_manifest.kafka_cluster]
}

# --- Deploy your Analytics Service (local Helm chart) ---
resource "helm_release" "analytics_service" {
  name             = "analytics-service"
  chart            = "${path.module}/../helm-chart/analytics-service"
  namespace        = kubernetes_namespace_v1.team4.metadata[0].name
  create_namespace = false
  values = [yamlencode({
    image = {
      repository = "analytics-service"
      tag        = "latest"
      pullPolicy = "IfNotPresent"
    }
    replicaCount = 1
    service = { port = 8080 }
  })]
  depends_on = [
    helm_release.influxdb2,
    kubernetes_manifest.kafka_cluster
  ]
}
