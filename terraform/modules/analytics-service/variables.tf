
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
