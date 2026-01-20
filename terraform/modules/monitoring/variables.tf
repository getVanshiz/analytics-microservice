
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

