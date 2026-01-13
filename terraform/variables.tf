
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
