#!/bin/sh
# Cleanup test environment
# This script destroys all test infrastructure

set -e

echo "=========================================="
echo "🧹 Cleaning Up Test Infrastructure"
echo "=========================================="

cd terraform-test

if [ ! -f "terraform.tfstate" ]; then
  echo "⚠️  No Terraform state found, nothing to cleanup"
  exit 0
fi

echo "1️⃣ Destroying Terraform resources..."
terraform destroy -auto-approve \
  -var="image_tag=cleanup" \
  -var="docker_username=cleanup"

echo ""
echo "2️⃣ Removing override files..."
rm -f providers_override.tf test.tfplan

echo ""
echo "✅ Test environment cleaned up!"