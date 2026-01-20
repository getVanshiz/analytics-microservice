
# Kubernetes provider
provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = "rancher-desktop"
}

# Helm provider - ARGUMENT form to forward Kubernetes auth
provider "helm" {
  kubernetes = {
    config_path    = "~/.kube/config"
    config_context = "rancher-desktop"
  }
}
