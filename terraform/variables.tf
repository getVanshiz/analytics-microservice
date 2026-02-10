
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

variable "service_port" {
  description = "Service port for the analytics API"
  type        = number
  default     = 5000
}

variable "use_docker_hub" {
  description = "Use Docker Hub images instead of local"
  type        = bool
  default     = true
}

variable "docker_username" {
  description = "Docker Hub username/namespace"
  type        = string
  default     = "vanshi29"  # <— your Docker Hub username
}

variable "image_tag" {
  description = "Image tag to deploy (e.g., short SHA from CI)"
  type        = string
  default     = "latest"    # override during apply
}

variable "rollout_nonce" {
  description = "Forcing a rollout even if values are the same"
  type        = string
  default     = ""
}