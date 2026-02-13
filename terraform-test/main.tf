terraform {
  required_version = ">= 1.0"
  
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
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
      "requests.cpu"    = "1"
      "requests.memory" = "2Gi"
      "limits.cpu"      = "2"
      "limits.memory"   = "4Gi"
      pods              = "10"
    }
  }
}

# ---------------------------
# Analytics Service Test Deployment
# Uses existing Kafka and InfluxDB from team4 namespace
# ---------------------------

resource "kubernetes_config_map_v1" "analytics_test_config" {
  metadata {
    name      = "analytics-test-config"
    namespace = kubernetes_namespace_v1.test.metadata[0].name
  }

  data = {
    # Kafka - reuse existing from team4
    KAFKA_BOOTSTRAP = "team4-kafka-kafka-bootstrap.team4.svc.cluster.local:9092"
    
    # InfluxDB - reuse existing from team4 with test bucket
    INFLUX_URL    = "http://influxdb2.team4.svc.cluster.local"
    INFLUX_ORG    = "team4"
    INFLUX_BUCKET = "analytics-test"  # Separate test bucket
    INFLUX_TOKEN  = "team4-dev-admin-token"
    
    # OpenTelemetry
    OTEL_SERVICE_NAME           = "analytics-service-test"
    OTEL_EXPORTER_OTLP_ENDPOINT = "http://otel-collector.monitoring.svc.cluster.local:4317"
    OTEL_EXPORTER_OTLP_INSECURE = "true"
    
    # App Config
    APP_VERSION             = var.image_tag
    PORT                    = "8080"
    INPUT_TOPICS            = "test-user-events,test-order-events,test-notification-events"
    ANALYTICS_TOPIC         = "test-analytics-events"
    CONSUMER_GROUP          = "test-analytics-group"
    ENABLE_ANALYTICS_TOPIC  = "true"
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
            initial_delay_seconds = 10
            period_seconds        = 10
          }

          readiness_probe {
            http_get {
              path = "/health"
              port = 8080
            }
            initial_delay_seconds = 5
            period_seconds        = 5
          }
        }
      }
    }
  }
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


