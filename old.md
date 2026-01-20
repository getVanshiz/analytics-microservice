I have 5 main folder
app/
main.py

from flask import Flask, jsonify
import time, os
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
start_time = time.time()

# Expose /metrics automatically
metrics = PrometheusMetrics(app, path="/metrics")
metrics.info("app_info", "Application info", version=os.getenv("APP_VERSION", "0.1.0"))

@app.route("/health")
def health():
    uptime = time.time() - start_time
    return jsonify({
        "status": "ok",
        "service": "analytics-service",
        "uptime_seconds": round(uptime, 2),
        "version": os.getenv("APP_VERSION", "0.1.0")
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))


requirements.txt
flask
prometheus-flask-exporter
gunicorn


docker folder

# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    &amp;&amp; apt-get install -y --no-install-recommends ca-certificates \
    &amp;&amp; rm -rf /var/lib/apt/lists/*

# Install deps from app/requirements.txt
COPY app/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    &amp;&amp; pip install -r /app/requirements.txt

# Copy only what you need (main.py)
COPY app/main.py /app/main.py

EXPOSE 8080

RUN useradd -r -u 10001 appuser &amp;&amp; chown -R appuser:appuser /app
USER 10001

CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "2", "main:app"]



helm-chart/analytics-service
templates/_helper.tpl


{{- define "analytics-service.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "analytics-service.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "analytics-service.labels" -}}
app.kubernetes.io/name: {{ include "analytics-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "analytics-service.selectorLabels" -}}
app.kubernetes.io/name: {{ include "analytics-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "analytics-service.fullname" . }}
  labels:
    {{- include "analytics-service.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "analytics-service.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "analytics-service.selectorLabels" . | nindent 8 }}
    spec:
      containers:
        - name: {{ include "analytics-service.name" . }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - containerPort: {{ .Values.service.port }}
          readinessProbe:
            httpGet:
              path: /health
              port: {{ .Values.service.port }}
            initialDelaySeconds: 2
          livenessProbe:
            httpGet:
              path: /health
              port: {{ .Values.service.port }}
            initialDelaySeconds: 5


service.yaml

apiVersion: v1
kind: Service
metadata:
  name: {{ include "analytics-service.fullname" . }}
  labels:
    {{- include "analytics-service.labels" . | nindent 4 }}
spec:
  type: ClusterIP
  selector:
    {{- include "analytics-service.selectorLabels" . | nindent 4 }}
  ports:
    - name: http
      port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.port }}


service-monitor.yaml

{{- if and .Values.serviceMonitor.enabled (.Capabilities.APIVersions.Has "monitoring.coreos.com/v1") }}
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ include "analytics-service.fullname" . }}-sm
  labels:
    {{- include "analytics-service.labels" . | nindent 4 }}
    {{- toYaml .Values.serviceMonitor.labels | nindent 4 }}
spec:
  selector:
    matchLabels:
      {{- include "analytics-service.selectorLabels" . | nindent 6 }}
  endpoints:
    - port: {{ .Values.service.name | default "http" }}
      path: {{ .Values.serviceMonitor.scrapePath | default "/metrics" }}
      interval: {{ .Values.serviceMonitor.interval | default "30s" }}
  namespaceSelector:
    matchNames:
      - {{ .Release.Namespace }}
{{- end }}

manifests/ (these I remember I applied manually)
influxdb-servicemonitor

apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: influxdb2-sm
  namespace: team4
  labels:
    release: kube-prometheus-stack
spec:
  selector:
    matchLabels:
      app.kubernetes.io/instance: influxdb2
      app.kubernetes.io/name: influxdb2
  namespaceSelector:
    matchNames:
      - team4
  endpoints:
    - port: http
      interval: 30s
      path: /metrics


kafka-exporter-servicemonitor.yaml


apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: kafka-exporter
  namespace: team4
  labels:
    release: kube-prometheus-stack
spec:
  selector:
    matchLabels:
      app: prometheus-kafka-exporter
  namespaceSelector:
    matchNames:
      - team4
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics


now the main folder terraform/

manifests/
kafka-cluster.yaml

apiVersion: kafka.strimzi.io/v1
kind: Kafka
metadata:
  name: ${cluster}
  namespace: ${namespace}
spec:
  kafka:
    version: 4.1.1
    metadataVersion: 4.1-IV1
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
    config:
      # Single-node safe factors
      offsets.topic.replication.factor: 1
      transaction.state.log.replication.factor: 1
      transaction.state.log.min.isr: 1
      default.replication.factor: 1
      min.insync.replicas: 1
  entityOperator:
    topicOperator: {}
    userOperator: {}

kafka-nodepool.yaml

apiVersion: kafka.strimzi.io/v1
kind: KafkaNodePool
metadata:
  name: dual-role
  namespace: ${namespace}
  labels:
    strimzi.io/cluster: ${cluster}
spec:
  replicas: 1
  roles: [controller, broker]
  storage:
    type: ephemeral


kafka-topic.yaml


apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: ${name}
  namespace: ${namespace}
  labels:
    strimzi.io/cluster: ${cluster}
spec:
  partitions: 1
  replicas: 1
  config:
    retention.ms: 7200000



manifest folder ends
main.tf

locals {
  namespace     = "team4"
  kafka_cluster = "team4-kafka"
}

# Namespace
module "namespace" {
  source = "./modules/namespace"
  name   = local.namespace
}

# Strimzi operator (Helm) - NOTE: use chart_version, not "version"
module "strimzi_operator" {
  source        = "./modules/strimzi-operator"
  namespace     = module.namespace.name
  chart_version = "0.49.1"
  depends_on = [module.namespace]
}

# Kafka CRs (KRaft, single-broker)
module "kafka" {
  source    = "./modules/kafka"
  namespace = module.namespace.name
  cluster   = local.kafka_cluster

  depends_on = [module.strimzi_operator]
}

# Kafka topic (example)
module "kafka_topic_analytics" {
  source    = "./modules/kafka-topic"
  namespace = module.namespace.name
  cluster   = local.kafka_cluster
  name      = "analytics-events"

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
      organization = "team4-org"
      bucket       = "team4-bucket"
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
      tag        = "latest"
      pullPolicy = "IfNotPresent"
    }
    replicaCount = 1
    service      = { port = 8080 }

    kafka = {
      bootstrapServers = module.kafka.bootstrap_dns
    }
    influxdb = {
      url      = "http://${module.influxdb2.release_name}.${module.influxdb2.namespace}.svc.cluster.local"
      org      = "team4-org"
      bucket   = "team4-bucket"
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
    # 🚫 Disable node exporter to avoid hostPort 9100 conflict on single-node clusters
    nodeExporter = {
      enabled = false
    }

    grafana = {
      service       = { type = "ClusterIP" }
      adminPassword = "admin123"
      additionalDataSources = [
        {
          name   = "InfluxDB"
          type   = "influxdb"
          access = "proxy"
          url    = "http://${module.influxdb2.release_name}.${module.influxdb2.namespace}.svc.cluster.local"
          user   = "admin"
          secureJsonData = { password = "admin123", token = "team4-dev-admin-token" }
          jsonData = {
            version        = "Flux"
            organization   = "team4-org"
            defaultBucket  = "team4-bucket"
            tlsSkipVerify  = true
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



resource "kubernetes_manifest" "kafka_exporter_sm" {
  manifest = {
    apiVersion = "monitoring.coreos.com/v1"
    kind       = "ServiceMonitor"
    metadata = {
      name      = "kafka-exporter-sm"
      namespace = module.namespace.name
      labels = {
        "release" = module.monitoring.name
      }
    }
    spec = {
      selector = {
        matchLabels = {
          "strimzi.io/cluster" = local.kafka_cluster
          # The exporter service typically also has: "app.kubernetes.io/name" = "kafka-exporter"
        }
      }
      endpoints = [
        {
          port     = "tcp-metrics"  # &lt;- common default with Strimzi Kafka Exporter
          interval = "30s"
        }
      ]
      namespaceSelector = {
        matchNames = [module.namespace.name]
      }
    }
  }
  depends_on = [module.kafka, module.monitoring]
}



providers.tf

# Kubernetes provider
provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = "rancher-desktop"
}

# Helm provider - ARGUMENT form to forward Kubernetes auth
provider "helm" {
  kubernetes = {
    config_path    = "~/.kube/config"
    config_context = "rancher-desktop"
  }
}


variables.tf

variable "kubeconfig_path" {
  description = "Path to local kubeconfig (Rancher Desktop)"
  type        = string
  default     = "~/.kube/config"
}

variable "namespace" {
  description = "Kubernetes namespace for analytics"
  type        = string
  default     = "analytics"
}

variable "image_repository" {
  description = "Container image repo for analytics service"
  type        = string
  default     = "analytics-service"
}

variable "image_tag" {
  description = "Container image tag"
  type        = string
  default     = "latest"
}

variable "service_port" {
  description = "Service port for the analytics API"
  type        = number
  default     = 5000
}


versions.tf


terraform {
  required_version = "&gt;= 1.5.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "&gt;= 2.25.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "&gt;= 2.10.1"
    }
  }
}


modules/
7 folders inside it

strimzi-operator
main.tf

resource "helm_release" "strimzi" {
  name             = var.name
  repository       = "oci://quay.io/strimzi-helm"
  chart            = "strimzi-kafka-operator"
  version          = var.chart_version
  namespace        = var.namespace
  create_namespace = false
}

output "name"      { value = helm_release.strimzi.name }
output "namespace" { value = var.namespace }


variable.tf

variable "namespace" { type = string }

variable "name" {
  type    = string
  default = "strimzi-operator"
}

# IMPORTANT: use chart_version, not "version"
variable "chart_version" {
  type        = string
  default     = "0.49.1"
  description = "Helm chart version for strimzi-kafka-operator"
}


namespace/
main.tf

resource "kubernetes_namespace_v1" "ns" {
  metadata { name = var.name }
}

output "name" {
  value = kubernetes_namespace_v1.ns.metadata[0].name
}


variables.tf

variable "name" {
  description = "Kubernetes namespace name"
  type        = string
}


monitoring/
main.tf

resource "helm_release" "monitoring" {
  name             = var.name
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  version          = var.chart_version
  namespace        = var.namespace
  create_namespace = false

  values = [yamlencode(var.values)]
}

output "namespace" { value = var.namespace }

output "grafana_service_dns" {
  value = "${var.name}-grafana.${var.namespace}.svc.cluster.local"
}

output "prometheus_service_dns" {
  value = "${var.name}-prometheus.${var.namespace}.svc.cluster.local"
}
outputs.tf
output "name" {
  description = "The configured release name for the monitoring stack"
  value       = var.name
}
variables.tf
variable "namespace" { type = string }

variable "name" {
  type    = string
  default = "kube-prometheus-stack"
}

variable "chart_version" {
  type        = string
  default     = "62.7.0" # pin a recent version; adjust as needed
  description = "Helm chart version for kube-prometheus-stack"
}

variable "values" {
  type        = any
  default     = {}
  description = "Values map for kube-prometheus-stack"
}
kafka-topicmain.tf
resource "kubernetes_manifest" "topic" {
  manifest = {
    apiVersion = "kafka.strimzi.io/v1beta2"
    kind       = "KafkaTopic"
    metadata = {
      name      = var.name
      namespace = var.namespace
      labels = {
        "strimzi.io/cluster" = var.cluster
      }
    }
    spec = {
      partitions = var.partitions
      replicas   = var.replicas
      config     = {}
    }
  }
}

output "name" { value = var.name }
variables.tf
variable "namespace" { type = string }
variable "cluster"   { type = string }
variable "name"      { type = string }
variable "partitions" {
  type    = number
  default = 1
}
variable "replicas" {
  type    = number
  default = 1
}
kafka/templateskafka-cluster.yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: ${cluster}
  namespace: ${namespace}
spec:
  kafka:
    # Strimzi will default to a compatible Kafka if not pinned;
    # you can pin explicitly:
    # version: 4.1.1
    replicas: 1
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
    storage:
      type: ephemeral
    config:
      # Single-node safe factors
      offsets.topic.replication.factor: 1
      transaction.state.log.replication.factor: 1
      transaction.state.log.min.isr: 1
      default.replication.factor: 1
      min.insync.replicas: 1
      # (Optional) Tune log.retention, etc., for dev:
      # log.retention.hours: 24
  # No `zookeeper` in KRaft mode
  entityOperator:
    topicOperator: {}
    userOperator: {}
  
  kafkaExporter:
    topicRegex: ".*"
    groupRegex: ".*"

kafka-nodepool.yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: ${cluster}-np-dual
  namespace: ${namespace}
  labels:
    strimzi.io/cluster: ${cluster}
spec:
  replicas: 1
  roles:
    - controller
    - broker
  storage:
    type: ephemeral
kafka/main.tf
# Node pool / dual role (uses template file)
resource "kubernetes_manifest" "kafka_nodepool_dualrole" {
  manifest = yamldecode(
    templatefile("${path.module}/templates/kafka-nodepool.yaml", {
      namespace = var.namespace
      cluster   = var.cluster
    })
  )
}

# Kafka cluster (depends on nodepool)
resource "kubernetes_manifest" "kafka_cluster" {
  manifest = yamldecode(
    templatefile("${path.module}/templates/kafka-cluster.yaml", {
      namespace = var.namespace
      cluster   = var.cluster
    })
  )
  depends_on = [kubernetes_manifest.kafka_nodepool_dualrole]
}

output "cluster"   { value = var.cluster }
output "namespace" { value = var.namespace }
# Strimzi exposes a bootstrap service with a conventional name:
output "bootstrap_dns" { value = "${var.cluster}-kafka-bootstrap.${var.namespace}.svc.cluster.local:9092" }

variables.tf
variable "namespace" {
  description = "Namespace where the Kafka CRs will be created"
  type        = string
}

variable "cluster" {
  description = "Strimzi Kafka cluster name"
  type        = string
}
influxdb2/
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
variables.tf
variable "namespace" { type = string }

variable "name" { 
    type = string 
    default = "influxdb2" 
}

# Allow passing values as a map for flexibility
variable "values" {
  type        = any
  description = "Values map for the InfluxDB2 Helm chart"
}
analytics-service/main.tf
resource "helm_release" "app" {
  name             = var.name
  chart            = var.chart_path
  namespace        = var.namespace
  create_namespace = false
  values           = [yamlencode(var.values)]
}

output "release_name" { value = helm_release.app.name }
output "namespace"    { value = var.namespace }
variables.tf
variable "namespace" { type = string }
variable "name"      { 
    type = string
    default = "analytics-service" 
}

variable "chart_path" {
  type        = string
  description = "Local path to the chart (relative to root)"
}
variable "values" {
  type        = any
  description = "Values map for the analytics service Helm chart"
}

