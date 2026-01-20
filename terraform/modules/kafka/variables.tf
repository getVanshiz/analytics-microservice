
variable "namespace" {
  description = "Namespace where the Kafka CRs will be created"
  type        = string
}

variable "cluster" {
  description = "Strimzi Kafka cluster name"
  type        = string
}
