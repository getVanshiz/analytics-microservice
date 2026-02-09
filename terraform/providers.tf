
# Kubernetes provider
provider "kubernetes" {
  config_path    = fileexists("~/.kube/config") ? "~/.kube/config" : ""
  config_context = fileexists("~/.kube/config") ? "rancher-desktop" : ""

}

# Helm provider - ARGUMENT form to forward Kubernetes auth
provider "helm" {
  kubernetes = {
    config_path    = fileexists("~/.kube/config") ? "~/.kube/config" : ""
    config_context = fileexists("~/.kube/config") ? "rancher-desktop" : ""
  }
}
