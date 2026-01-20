
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


variable "topicName" {
  type        = string
  description = "Actual Kafka topic name"
  default     = null
}
