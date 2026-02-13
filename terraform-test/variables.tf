variable "docker_username" {
  description = "Docker Hub username for pulling images"
  type        = string
  default     = "vanshi29"
}

variable "image_tag" {
  description = "Docker image tag to deploy for testing"
  type        = string
}
 

