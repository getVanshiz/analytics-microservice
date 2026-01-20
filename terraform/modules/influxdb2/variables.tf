
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
