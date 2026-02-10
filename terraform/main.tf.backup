
locals {
  namespace     = "team4"
  kafka_cluster = "team4-kafka"
}

# ---------------------------
# Namespaces
# ---------------------------

resource "kubernetes_namespace_v1" "strimzi" {
  metadata { name = "strimzi" }
}

module "namespace" {
  source = "./modules/namespace"
  name   = local.namespace
}

module "ns_monitoring" {
  source = "./modules/namespace"
  name   = "monitoring"
}

module "ns_observability" {
  source = "./modules/namespace"
  name   = "observability"
}

# ---------------------------
# Strimzi Operator
# ---------------------------

module "strimzi_operator" {
  source        = "./modules/strimzi-operator"
  namespace     = kubernetes_namespace_v1.strimzi.metadata[0].name
  chart_version = "0.49.1"

  values = {
    watchNamespaces = [local.namespace]
  }

  depends_on = [kubernetes_namespace_v1.strimzi]
}

# ---------------------------
# WAIT: Strimzi CRDs
# ---------------------------

resource "null_resource" "wait_for_strimzi_crds" {
  provisioner "local-exec" {
    command = <<EOT
      echo "Waiting for Strimzi Kafka CRDs..."
      kubectl wait --for=condition=Established crd/kafkas.kafka.strimzi.io --timeout=300s
    EOT
  }

  depends_on = [module.strimzi_operator]
}

# ---------------------------
# Kafka Cluster
# ---------------------------

module "kafka" {
  source    = "./modules/kafka"
  namespace = module.namespace.name
  cluster   = local.kafka_cluster

  depends_on = [null_resource.wait_for_strimzi_crds]
}

# ---------------------------
# Kafka Topics
# ---------------------------

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

# ---------------------------
# InfluxDB
# ---------------------------

module "influxdb2" {
  source    = "./modules/influxdb2"
  namespace = module.namespace.name
  name      = "influxdb2"

  values = {
    persistence = { enabled = false }

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

# ---------------------------
# InfluxDB Token Secret (NO MANUAL STEP)
# ---------------------------

resource "kubernetes_secret" "influxdb_auth" {
  metadata {
    name      = "influxdb-auth"
    namespace = module.namespace.name
  }

  data = {
    token = base64encode("team4-dev-admin-token")
  }

  type = "Opaque"

  depends_on = [module.influxdb2]
}

# ---------------------------
# Monitoring Stack
# ---------------------------

module "monitoring" {
  source        = "./modules/monitoring"
  namespace     = module.ns_monitoring.name
  name          = "kube-prometheus-stack"
  chart_version = "62.7.0"

  values = {
    nodeExporter = { enabled = false }

    grafana = {
      adminPassword = "admin123"
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

# ---------------------------
# WAIT: ServiceMonitor CRDs
# ---------------------------

resource "null_resource" "wait_for_monitoring_crds" {
  provisioner "local-exec" {
    command = <<EOT
      echo "Waiting for ServiceMonitor CRDs..."
      kubectl wait --for=condition=Established crd/servicemonitors.monitoring.coreos.com --timeout=300s
    EOT
  }

  depends_on = [module.monitoring]
}

# ---------------------------
# Analytics Service
# ---------------------------

module "analytics_service" {
  source     = "./modules/analytics-service"
  namespace  = module.namespace.name
  name       = "analytics-service"
  chart_path = "${path.module}/../helm-chart/analytics-service"

  values = {
    image = {
      repository = "analytics-service"
      tag        = "v24"
      pullPolicy = "Never"
    }

    kafka = {
      bootstrapServers = module.kafka.bootstrap_dns
    }

    influxdb = {
      url    = "http://${module.influxdb2.release_name}.${module.influxdb2.namespace}.svc.cluster.local"
      org    = "team4"
      bucket = "analytics"
      token  = "team4-dev-admin-token"
    }
  }

  depends_on = [
    module.kafka,
    module.influxdb2
  ]
}

# ---------------------------
# ServiceMonitors
# ---------------------------

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
      endpoints = [{
        port     = "http"
        path     = "/metrics"
        interval = "30s"
      }]
      namespaceSelector = {
        matchNames = [module.namespace.name]
      }
    }
  }

  depends_on = [
    null_resource.wait_for_monitoring_crds,
    module.analytics_service
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
      endpoints = [{
        port     = "http"
        path     = "/metrics"
        interval = "30s"
      }]
      namespaceSelector = {
        matchNames = [module.namespace.name]
      }
    }
  }

  depends_on = [
    null_resource.wait_for_monitoring_crds,
    module.influxdb2
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
      endpoints = [{
        port     = "prometheus"
        path     = "/metrics"
        interval = "30s"
      }]
      namespaceSelector = {
        matchNames = [module.namespace.name]
      }
    }
  }

  depends_on = [
    null_resource.wait_for_monitoring_crds,
    module.kafka
  ]
}

# ---------------------------
# Logging / Observability
# ---------------------------

module "elasticsearch" {
  source       = "./modules/logging/elasticsearch"
  release_name = "elasticsearch"
  namespace    = module.ns_observability.name
}

module "kibana" {
  source       = "./modules/logging/kibana"
  release_name = "kibana"
  namespace    = module.ns_observability.name

  depends_on = [module.elasticsearch]
}

module "filebeat" {
  source       = "./modules/logging/filebeat"
  release_name = "filebeat"
  namespace    = module.ns_observability.name

  depends_on = [module.elasticsearch]
}

module "kibana_objects" {
  source    = "./modules/logging/kibana-objects"
  name      = "kibana-objects"
  namespace = module.ns_observability.name

  depends_on = [module.kibana]
}

module "jaeger" {
  source       = "./modules/logging/jaeger"
  release_name = "jaeger"
  namespace    = module.ns_monitoring.name

  depends_on = [
    module.ns_monitoring
  ]
}

module "opentelemetry" {
  source       = "./modules/logging/opentelemetry"
  release_name = "otel-collector"
  namespace    = module.ns_monitoring.name

  depends_on = [
    module.jaeger
  ]
}
