#!/bin/sh
# Run integration tests against test environment
# This script executes pytest integration tests with proper configuration

set -e

echo "=========================================="
echo "🧪 Running Integration Tests"
echo "=========================================="

# Extract Terraform outputs for test configuration
cd terraform-test

if [ ! -f "terraform.tfstate" ]; then
  echo "❌ ERROR: Test environment not deployed (no terraform.tfstate found)"
  exit 1
fi

# Get service endpoints from Terraform outputs
export ANALYTICS_URL=$(terraform output -raw analytics_service_url 2>/dev/null || echo "http://analytics-service-test.analytics-test.svc.cluster.local:8080")
export KAFKA_BOOTSTRAP=$(terraform output -raw kafka_bootstrap 2>/dev/null || echo "team4-kafka-kafka-bootstrap.team4.svc.cluster.local:9092")
export INFLUX_URL=$(terraform output -raw influxdb_url 2>/dev/null || echo "http://influxdb2.team4.svc.cluster.local")
export INFLUX_TOKEN="team4-dev-admin-token"
export INFLUX_ORG="team4"
export INFLUX_BUCKET="analytics"  # Use production bucket (read-only)

cd ..

echo "🔧 Test Configuration:"
echo "  Analytics URL: $ANALYTICS_URL"
echo "  Kafka Bootstrap: $KAFKA_BOOTSTRAP"
echo "  InfluxDB URL: $INFLUX_URL"
echo ""

# Install test dependencies if not already installed
echo "1️⃣ Installing test dependencies..."
pip install -q -r requirements-test.txt
pip install -q -r app/requirements.txt

echo ""
echo "2️⃣ Running integration tests..."
pytest tests/integration/test_real_integration.py \
  -v \
  --tb=short \
  --color=yes \
  --junitxml=test-results.xml \
  --html=test-report.html \
  --self-contained-html

TEST_EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo "✅ Integration tests PASSED!"
else
  echo "❌ Integration tests FAILED!"
  echo "Check test-results.xml and test-report.html for details"
fi
echo "=========================================="

exit $TEST_EXIT_CODE
