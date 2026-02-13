#!/bin/sh
# Deploy test environment using Terraform
# This script deploys isolated Kafka, InfluxDB, and analytics service

set -e

echo "=========================================="
echo "🚀 Deploying Test Infrastructure"
echo "=========================================="

# Get image tag from environment or argument
IMAGE_TAG="${1:-${IMAGE_SHA}}"
DOCKER_USERNAME="${DOCKER_USERNAME:-vanshi29}"

if [ -z "$IMAGE_TAG" ]; then
  echo "❌ ERROR: IMAGE_TAG not provided"
  echo "Usage: $0 <image_tag>"
  exit 1
fi

echo "📦 Image: ${DOCKER_USERNAME}/analytics-service:${IMAGE_TAG}"
echo ""

cd terraform-test

# Configure providers for in-cluster execution
cat > providers_override.tf <<'EOF'
provider "kubernetes" {
  host                   = "https://kubernetes.default.svc"
  token                  = file("/var/run/secrets/kubernetes.io/serviceaccount/token")
  cluster_ca_certificate = file("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
}
provider "helm" {
  kubernetes {
    host                   = "https://kubernetes.default.svc"
    token                  = file("/var/run/secrets/kubernetes.io/serviceaccount/token")
    cluster_ca_certificate = file("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
  }
}
EOF

echo "1️⃣ Initializing Terraform..."
terraform init -upgrade

echo ""
echo "2️⃣ Planning deployment..."
terraform plan \
  -var="docker_username=${DOCKER_USERNAME}" \
  -var="image_tag=${IMAGE_TAG}" \
  -out=test.tfplan

echo ""
echo "3️⃣ Applying deployment..."
terraform apply -auto-approve test.tfplan

echo ""
echo "4️⃣ Deployment complete! Outputs:"
terraform output

echo ""
echo "✅ Test environment deployed successfully!"
echo ""
echo "⏳ Note: Pods may take 10-15 seconds to be ready..."