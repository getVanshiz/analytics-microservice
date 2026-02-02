variable "release_name"  { type = string }
variable "namespace"     { type = string }
variable "chart_version" {
  type    = string
  # pin a recent v2 chart; adjust to the tested version you have in your env
  default = "4.4.2"
}