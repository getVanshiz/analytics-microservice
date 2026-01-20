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


variable "values" {
  type        = any
  default     = {}
  description = "Custom Helm values for Strimzi"
}
