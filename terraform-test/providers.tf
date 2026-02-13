provider "kubernetes" {
  # Configuration will be provided via environment or override file
}

provider "helm" {
  kubernetes {
    # Configuration will be provided via environment or override file
  }
}