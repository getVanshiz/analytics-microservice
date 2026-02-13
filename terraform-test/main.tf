terraform {
  required_version = ">= 1.0"
  
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }
}

# ---------------------------
# Test Namespace
# ---------------------------

resource "kubernetes_namespace_v1" "test" {
  metadata {
    name = "analytics-test"
    labels = {
      purpose     = "integration-testing"
      team        = "team4"
      environment = "test"
    }
  }
}

# ---------------------------
# Resource Quota
# ---------------------------

resource "kubernetes_resource_quota_v1" "test_quota" {
  metadata {
    name      = "test-quota"
    namespace = kubernetes_namespace_v1.test.metadata[0].name
  }

  spec {
    hard = {
      "requests.cpu"    = "2"
      "requests.memory" = "4Gi"
      "limits.cpu"      = "4"
      "limits.memory"   = "8Gi"
      pods              = "20"
    }
  }
}

# ---------------------------
# Test Kafka (Lightweight)
# ---------------------------

resource "helm_release" "test_kafka" {
  name       = "test-kafka"
  repository = "https://charts.bitnami.com/bitnami"
  chart      = "kafka"
  version    = "26.4.2"
  namespace  = kubernetes_namespace_v1.test.metadata[0].name

  values = [
    yamlencode({
      # Minimal single-node Kafka for testing
      replicaCount = 1
      
      kraft = {
        enabled = true
      }
      
      controller = {
        replicaCount = 1
      }
      
      broker = {
        replicaCount = 1
      }
      
      listeners = {
        client = {
          protocol = "PLAINTEXT"
        }
      }
      
      persistence = {
        enabled = false  # Ephemeral for tests
      }
      
      resources = {
        requests = {
          cpu    = "250m"
          memory = "512Mi"
        }
        limits = {
          cpu    = "500m"
          memory = "1Gi"
        }
      }
    })
  ]

  depends_on = [kubernetes_namespace_v1.test]
}

# ---------------------------
# Test InfluxDB (Lightweight)
# ---------------------------

resource "helm_release" "test_influxdb" {
  name       = "test-influxdb"
  repository = "https://helm.influxdata.com/"
  chart      = "influxdb2"
  version    = "2.1.1"
  namespace  = kubernetes_namespace_v1.test.metadata[0].name

  values = [
    yamlencode({
      # Minimal InfluxDB for testing
      persistence = {
        enabled = false  # Ephemeral for tests
      }
      
      adminUser = {
        user         = "admin"
        password     = "testpass123"
        token        = "test-token"
        organization = "test-org"
        bucket       = "analytics-test"
      }
      
      service = {
        type = "ClusterIP"
      }
      
      resources = {
        requests = {
          cpu    = "250m"
          memory = "512Mi"
        }
        limits = {
          cpu    = "500m"
          memory = "1Gi"
        }
      }
    })
  ]

  depends_on = [kubernetes_namespace_v1.test]
}

# ---------------------------
# Analytics Service Test Deployment
# ---------------------------

resource "kubernetes_config_map_v1" "analytics_test_config" {
  metadata {
    name      = "analytics-test-config"
    namespace = kubernetes_namespace_v1.test.metadata[0].name
  }

  data = {
    KAFKA_BOOTSTRAP             = "${helm_release.test_kafka.name}.${kubernetes_namespace_v1.test.metadata[0].name}.svc.cluster.local:9092"
    INFLUX_URL                  = "http://${helm_release.test_influxdb.name}.${kubernetes_namespace_v1.test.metadata[0].name}.svc.cluster.local"
    INFLUX_ORG                  = "test-org"
    INFLUX_BUCKET               = "analytics-test"
    INFLUX_TOKEN                = "test-token"
    OTEL_SERVICE_NAME           = "analytics-service-test"
    OTEL_EXPORTER_OTLP_ENDPOINT = "http://otel-collector.monitoring.svc.cluster.local:4317"
    OTEL_EXPORTER_OTLP_INSECURE = "true"
    APP_VERSION                 = var.image_tag
    PORT                        = "8080"
    INPUT_TOPICS                = "user-events,order-events,notification-events"
    ANALYTICS_TOPIC             = "analytics-events"
    CONSUMER_GROUP              = "test-analytics-group"
    ENABLE_ANALYTICS_TOPIC      = "true"
  }
}

resource "kubernetes_deployment_v1" "analytics_test" {
  metadata {
    name      = "analytics-service-test"
    namespace = kubernetes_namespace_v1.test.metadata[0].name
    labels = {
      app         = "analytics-service"
      environment = "test"
    }
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app         = "analytics-service"
        environment = "test"
      }
    }

    template {
      metadata {
        labels = {
          app         = "analytics-service"
          environment = "test"
        }
      }

      spec {
        container {
          name              = "analytics-service"
          image             = "${var.docker_username}/analytics-service:${var.image_tag}"
          image_pull_policy = "Always"

          port {
            container_port = 8080
            name           = "http"
          }

          env_from {
            config_map_ref {
              name = kubernetes_config_map_v1.analytics_test_config.metadata[0].name
            }
          }

          resources {
            requests = {
              cpu    = "250m"
              memory = "512Mi"
            }
            limits = {
              cpu    = "500m"
              memory = "1Gi"
            }
          }

          liveness_probe {
            http_get {
              path = "/health"
              port = 8080
            }
            initial_delay_seconds = 15
            period_seconds        = 10
          }

          readiness_probe {
            http_get {
              path = "/health"
              port = 8080
            }
            initial_delay_seconds = 10
            period_seconds        = 5
          }
        }
      }
    }
  }

  depends_on = [
    helm_release.test_kafka,
    helm_release.test_influxdb
  ]
}

resource "kubernetes_service_v1" "analytics_test" {
  metadata {
    name      = "analytics-service-test"
    namespace = kubernetes_namespace_v1.test.metadata[0].name
    labels = {
      app         = "analytics-service"
      environment = "test"
    }
  }

  spec {
    type = "ClusterIP"

    port {
      port        = 8080
      target_port = 8080
      protocol    = "TCP"
      name        = "http"
    }

    selector = {
      app         = "analytics-service"
      environment = "test"
    }
  }
}
