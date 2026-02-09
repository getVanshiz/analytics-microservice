################################
# Root stack for your platform #
################################

locals {
  namespace     = "team4"
  kafka_cluster = "team4-kafka"
}

# --- Namespaces ---

# Dedicated namespace for Strimzi operator
resource "kubernetes_namespace_v1" "strimzi" {
  metadata { name = "strimzi" }
}

# App / Team namespace
module "namespace" {
  source = "./modules/namespace"
  name   = local.namespace
}

# Monitoring namespace
module "ns_monitoring" {
  source = "./modules/namespace"
  name   = "monitoring"
}

# Observability namespace for ES/Kibana/Filebeat (optional)
module "ns_observability" {
  source = "./modules/namespace"
  name   = "observability"
}

# --- Strimzi operator & Kafka ---

module "strimzi_operator" {
  source        = "./modules/strimzi-operator"
  namespace     = kubernetes_namespace_v1.strimzi.metadata[0].name
  chart_version = "0.49.1"

  values = {
    watchNamespaces = [local.namespace]
  }

  depends_on = [
    kubernetes_namespace_v1.strimzi,  # operator namespace
    module.namespace                  # ensure "team4" exists before install since it's watched
  ]
}

# Kafka (KRaft, single-broker)
module "kafka" {
  source    = "./modules/kafka"
  namespace = module.namespace.name
  cluster   = local.kafka_cluster
  depends_on = [module.strimzi_operator]
}

# Topics
module "kafka_topic_user_events" {
  source    = "./modules/kafka-topic"
  namespace = module.namespace.name
  cluster   = local.kafka_cluster
  name      = "user-events"
  topicName = "user-events"
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

# --- InfluxDB ---

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

# Influx token secret (Terraform-managed)
resource "kubernetes_secret_v1" "influxdb_auth" {
  metadata {
    name      = "influxdb-auth"
    namespace = module.namespace.name
  }
  data = {
    token = "team4-dev-admin-token"
  }
  type = "Opaque"
}

# --- Your analytics service ---
module "analytics_service" {
  source     = "./modules/analytics-service"
  namespace  = module.namespace.name
  name       = "analytics-service"
  chart_path = "${path.module}/../helm-chart/analytics-service"

  values = {
    image = {
      repository = "analytics-service"
      tag        = "v28"
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
    kubernetes_secret_v1.influxdb_auth,
    module.influxdb2,
    module.kafka
  ]
}

# --- Monitoring stack (kube-prometheus-stack) ---

module "monitoring" {
  source        = "./modules/monitoring"
  namespace     = module.ns_monitoring.name
  name          = "kube-prometheus-stack"
  chart_version = "62.7.0"

  # IMPORTANT: enable CRDs and the CRD upgrade job
  values = {
    crds = {
      enabled    = false
      upgradeJob = { enabled = true }
    }

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
            version         = "Flux"
            organization    = "team4"
            defaultBucket   = "analytics"
            httpHeaderName1 = "Authorization"
            tlsSkipVerify   = true
          }
          secureJsonData = {
            httpHeaderValue1 = "Token team4-dev-admin-token"
          }
        }
      ]
    }

    prometheus = {
      prometheusSpec = {
        web = {
          httpConfig = {}
        }
        storageSpec = null 
        retention      = "5d"
        scrapeInterval = "30s"
        
        # Add resource requests and limits to prevent OOM/slowness
        resources = {
          requests = {
            cpu    = "250m"
            memory = "512Mi"
          }
          limits = {
            cpu    = "1000m"
            memory = "1Gi"
          }
        }
        
        # Increase probe timeouts and initial delays since Prometheus is slow to respond
        livenessProbe = {
          httpGet = {
            path = "/-/healthy"
            port = "http-web"
            scheme = "HTTP"
          }
          initialDelaySeconds = 60
          timeoutSeconds = 10
          periodSeconds = 15
          successThreshold = 1
          failureThreshold = 5
        }
        
        readinessProbe = {
          httpGet = {
            path = "/-/ready"
            port = "http-web"
            scheme = "HTTP"
          }
          initialDelaySeconds = 60
          timeoutSeconds = 10
          periodSeconds = 15
          successThreshold = 1
          failureThreshold = 3
        }
        
        startupProbe = {
          httpGet = {
            path = "/-/ready"
            port = "http-web"
            scheme = "HTTP"
          }
          initialDelaySeconds = 0
          timeoutSeconds = 10
          periodSeconds = 15
          successThreshold = 1
          failureThreshold = 60
        }
      }
    }

    alertmanager = { enabled = true }
  }

  depends_on = [module.ns_monitoring]
}

# --- Jaeger & OTel ---
module "jaeger" {
  source       = "./modules/logging/jaeger"
  release_name = "jaeger"
  namespace    = module.ns_monitoring.name
  depends_on   = [module.ns_monitoring]
}

module "opentelemetry" {
  source       = "./modules/logging/opentelemetry"
  release_name = "otel-collector"
  namespace    = module.ns_monitoring.name
  depends_on   = [module.jaeger]
}

# --- ServiceMonitors (created only after CRDs exist) ---

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
    # module.analytics_service,  # Disabled for now
    module.monitoring   # ensure CRDs are present before creating SMs
  ]
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
          "app.kubernetes.io/name"     = "influxdb2"
          "app.kubernetes.io/instance" = "influxdb2"
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
          "strimzi.io/cluster"        = local.kafka_cluster
          "app.kubernetes.io/name"    = "kafka-exporter"
        }
      }
      endpoints = [
        {
          port     = "prometheus"
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
    # module.kafka,  # Disabled for now
    module.monitoring
  ]
}

# --- Elasticsearch, Kibana, Filebeat ---
module "elasticsearch" {
  source       = "./modules/logging/elasticsearch"
  release_name = "elasticsearch"
  namespace    = module.ns_observability.name
  depends_on   = [module.ns_observability]
}

module "kibana" {
  source       = "./modules/logging/kibana"
  release_name = "kibana"
  namespace    = module.ns_observability.name
  depends_on   = [module.elasticsearch]
}

module "filebeat" {
  source       = "./modules/logging/filebeat"
  release_name = "filebeat"
  namespace    = module.ns_observability.name
  depends_on   = [module.elasticsearch]
}

module "kibana_objects" {
  source     = "./modules/logging/kibana-objects"
  name       = "kibana-objects"
  namespace  = module.ns_observability.name
  depends_on = [module.kibana]
}