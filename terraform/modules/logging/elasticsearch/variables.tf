variable "release_name"  { type = string }
variable "namespace"     { type = string }
variable "chart_version" {
  type    = string
  default = "8.5.1"
} # pin per Elastic’s Helm chart
# adjust if needed