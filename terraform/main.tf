
locals {
  namespace     = "team4"
  kafka_cluster = "team4-kafka"
}


# Create dedicated namespace for Strimzi operator
resource "kubernetes_namespace_v1" "strimzi" {
  metadata {
    name = "strimzi"
  }
}


# Namespace
module "namespace" {
  source = "./modules/namespace"
  name   = local.namespace
}




module "strimzi_operator" {
  source        = "./modules/strimzi-operator"
  namespace     = kubernetes_namespace_v1.strimzi.metadata[0].name
  chart_version = "0.49.1"

  values = {
    watchNamespaces = ["team4"]
  }

  depends_on = [kubernetes_namespace_v1.strimzi]
}





# Kafka CRs (KRaft, single-broker)
module "kafka" {
  source    = "./modules/kafka"
  namespace = module.namespace.name
  cluster   = local.kafka_cluster
  depends_on = [module.strimzi_operator]
}

# Kafka CRs (KRaft, single-broker)

module "kafka_topic_user_events" {
  source    = "./modules/kafka-topic"
  namespace = module.namespace.name
  cluster   = local.kafka_cluster
  name      = "user-events"            # <-- FIXED
  topicName = "user-events"            # <-- real Kafka topic name
  depends_on = [module.kafka]
}

module "kafka_topic_order_events" {
  source    = "./modules/kafka-topic"
  namespace = module.namespace.name
  cluster   = local.kafka_cluster
  name      = "order-events"
  topicName = "order-events"
  depends_on = [module.kafka]
}

module "kafka_topic_notification_events" {
  source    = "./modules/kafka-topic"
  namespace = module.namespace.name
  cluster   = local.kafka_cluster
  name      = "notification-events"
  topicName = "notification-events"
  depends_on = [module.kafka]
}


module "kafka_topic_analytics_events" {
  source    = "./modules/kafka-topic"
  namespace = module.namespace.name
  cluster   = local.kafka_cluster
  name      = "analytics-events"
  topicName = "analytics-events"
  depends_on = [module.kafka]
}


# InfluxDB v2 (Helm)
module "influxdb2" {
  source    = "./modules/influxdb2"
  namespace = module.namespace.name
  name      = "influxdb2"

  values = {
    persistence = { enabled = false } # ephemeral for dev
    adminUser = {
      user         = "admin"
      password     = "admin123"
      token        = "team4-dev-admin-token"
      organization = "team4"
      bucket       = "analytics"
    }
    service = { type = "ClusterIP" }
  }

  depends_on = [module.namespace]
}

# Analytics service (local Helm chart)
module "analytics_service" {
  source     = "./modules/analytics-service"
  namespace  = module.namespace.name
  name       = "analytics-service"
  chart_path = "${path.module}/../helm-chart/analytics-service"

  
  values = {
    image = {
      repository = "analytics-service"
      tag        = "v22"        # ✅ NEW TAG
      pullPolicy = "Never"
    }
    replicaCount = 1
    service      = { port = 8080 }

    kafka = {
      bootstrapServers = module.kafka.bootstrap_dns
    }
    influxdb = {
      url      = "http://${module.influxdb2.release_name}.${module.influxdb2.namespace}.svc.cluster.local"
      org      = "team4"
      bucket   = "analytics"
      token    = "team4-dev-admin-token"
      username = "admin"
      password = "admin123"
    }
  }

  depends_on = [
    module.influxdb2,
    module.kafka
  ]
}



module "elasticsearch" {
  source       = "./modules/logging/elasticsearch"
  release_name = "elasticsearch"
  namespace    = "monitoring"
  depends_on   = [module.ns_monitoring]
}

module "kibana" {
  source       = "./modules/logging/kibana"
  release_name = "kibana"
  namespace    = "monitoring"
  depends_on   = [module.elasticsearch, module.ns_monitoring]
}

module "filebeat" {
  source       = "./modules/logging/filebeat"
  release_name = "filebeat"
  namespace    = "monitoring"
  depends_on   = [module.elasticsearch, module.ns_monitoring]
}

module "jaeger" {
  source       = "./modules/logging/jaeger"
  release_name = "jaeger"
  namespace    = "monitoring"
  depends_on   = [module.ns_monitoring]
}

module "otel" {
  source       = "./modules/logging/opentelemetry"
  release_name = "otel-collector"
  namespace    = "monitoring"
  depends_on   = [module.jaeger, module.ns_monitoring]
}


# ---------------------------
# (Optional) Monitoring stack
# ---------------------------
module "ns_monitoring" {
  source = "./modules/namespace"
  name   = "monitoring"
}



module "monitoring" {
  source        = "./modules/monitoring"
  namespace     = module.ns_monitoring.name
  name          = "kube-prometheus-stack"
  chart_version = "62.7.0"

  values = {
    nodeExporter = { enabled = false }

    grafana = {
      service       = { type = "ClusterIP" }
      adminPassword = "admin123"

      additionalDataSources = [
        {
          name   = "InfluxDB-Team4"
          type   = "influxdb"
          access = "proxy"
          url    = "http://${module.influxdb2.release_name}.${module.influxdb2.namespace}.svc.cluster.local"
          jsonData = {
            version        = "Flux"     # Flux query language
            organization   = "team4"    # <-- CHANGED
            defaultBucket  = "analytics" # <-- CHANGED
            httpHeaderName1 = "Authorization"
            tlsSkipVerify  = true
          }
          secureJsonData = {
            httpHeaderValue1 = "Token team4-dev-admin-token"  # <-- Prefer using a Secret (see below)
          }
        }
      ]
    }

    prometheus = {
      prometheusSpec = {
        retention      = "5d"
        scrapeInterval = "30s"
      }
    }

    alertmanager = { enabled = true }
  }

  depends_on = [module.ns_monitoring]
}


# Example ServiceMonitor for analytics-service (if monitoring enabled)
resource "kubernetes_manifest" "analytics_service_monitor" {
  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "ServiceMonitor"
    metadata = {
      name      = "analytics-service-sm"
      namespace = module.namespace.name
      labels = {
        release = "kube-prometheus-stack"
      }
    }
    spec = {
      selector = {
        matchLabels = {
          "app.kubernetes.io/name" = "analytics-service"
        }
      }
      endpoints = [
        {
          port     = "http"   # ensure Service has a named port "http"
          path     = "/metrics"
          interval = "30s"
        }
      ]
      namespaceSelector = {
        matchNames = [module.namespace.name]
      }
    }
  }
  depends_on = [module.analytics_service]
}


resource "kubernetes_manifest" "influxdb_sm" {
  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "ServiceMonitor"
    metadata = {
      name      = "influxdb2-sm"
      namespace = module.namespace.name
      labels = {
        release = "kube-prometheus-stack"
      }
    }
    spec = {
      selector = {
        matchLabels = {
          "app.kubernetes.io/name"      = "influxdb2"
          "app.kubernetes.io/instance"  = "influxdb2"
        }
      }
      endpoints = [
        {
          port     = "http"
          path     = "/metrics"
          interval = "30s"
        }
      ]
      namespaceSelector = {
        matchNames = [module.namespace.name]
      }
    }
  }

  depends_on = [
    module.influxdb2,
    module.monitoring
  ]
}




resource "kubernetes_manifest" "kafka_exporter_sm" {
  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "ServiceMonitor"
    metadata = {
      name      = "kafka-exporter-sm"
      namespace = module.namespace.name
      labels = {
        release = "kube-prometheus-stack"
      }
    }
    spec = {
      selector = {
        matchLabels = {
          "strimzi.io/cluster" = local.kafka_cluster
          "app.kubernetes.io/name" = "kafka-exporter"
        }
      }
      endpoints = [
        {
          port     = "prometheus" # STRIMZI DEFAULT PORT
          interval = "30s"
          path     = "/metrics"
        }
      ]
      namespaceSelector = {
        matchNames = [module.namespace.name]
      }
    }
  }

  depends_on = [
    module.kafka,
    module.monitoring
  ]
}
