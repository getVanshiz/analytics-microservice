# Testing & CI/CD Guide

Complete guide for running tests locally and deploying via GitHub Actions with self-hosted runners on Rancher Desktop.

## Table of Contents
1. [Running Tests Locally](#running-tests-locally)
2. [GitHub Actions Pipeline](#github-actions-pipeline)
3. [Load Testing](#load-testing)
4. [Troubleshooting](#troubleshooting)

---

## Running Tests Locally

### Prerequisites

```bash
# Navigate to project root
cd /Users/sakshi.singh/my-analytics-service

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
cd app
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock
cd ..
```

### Unit Tests

```bash
# Run all unit tests with coverage
pytest tests/unit/ -v --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_core_logic.py -v

# Run specific test class
pytest tests/unit/test_core_logic.py::TestEventTimeParsing -v

# Run specific test case
pytest tests/unit/test_core_logic.py::TestEventTimeParsing::test_iso_8601_timestamp -v

# Run with coverage report
pytest tests/unit/ --cov=app --cov-report=term-missing
```

**Coverage Report:**
- Generated in `htmlcov/` directory
- Open in browser: `open htmlcov/index.html`

### Integration Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific integration test file
pytest tests/integration/test_event_pipeline.py -v

# Run with detailed output
pytest tests/integration/test_event_pipeline.py::TestEventIngestionPipeline -v -s
```

**Note:** Integration tests use mocked Kafka/InfluxDB. Real services optional.

### Code Quality Checks

```bash
# Linting
flake8 app/ tests/ --max-line-length=100

# Code formatting check
black app/ tests/ --check

# Import sorting check
isort app/ tests/ --check

# Auto-fix formatting
black app/ tests/
isort app/ tests/
```

---

## GitHub Actions Pipeline

### Pipeline Workflows

The analytics service uses 3 GitHub Actions workflows (self-hosted runners on Rancher Desktop):

#### 1. **CI Workflow** (`.github/workflows/ci.yml`)
Runs on every `push` and `pull_request`

**Jobs:**
- Unit tests with coverage
- Integration tests
- Code quality checks (flake8, black, isort)

**Status:** Visible in GitHub → Actions tab

#### 2. **CD Workflow** (`.github/workflows/cd.yml`)
Runs on `main` branch and version tags

**Jobs:**
- Docker build and push
- Helm deployment to K8s
- Rollout verification
- Auto-rollback on failure

**Environments:**
- Staging: Deploys on main push
- Production: Deploys on version tags (manual trigger)

#### 3. **Load Test Workflow** (`.github/workflows/load-test.yml`)
Manual dispatch or scheduled

**Jobs:**
- Generates load (100 req/s)
- Collects metrics from Prometheus
- Generates performance report

### Setting Up Self-Hosted Runner

The runner is already configured for Rancher Desktop. To verify:

```bash
# Check runner status
cd /Users/sakshi.singh/my-analytics-service
cat .github/workflows/ci.yml | grep "runs-on"
# Expected: runs-on: [self-hosted, local, rancher, nerdctl]

# Verify runner is active
# GitHub → Project Settings → Actions → Runners
# Should show: "1 online"
```

### Triggering Workflows

#### Trigger CI

```bash
# Push to branch (automatic)
git push origin feature/my-feature

# View status
# GitHub → Actions → CI → Latest run
```

#### Trigger CD (Staging)

```bash
# Merge to main
git checkout main
git merge feature/my-feature
git push origin main

# View status
# GitHub → Actions → CD → "Staging deployment"
```

#### Trigger CD (Production)

```bash
# Create version tag
git tag -a v1.2.3 -m "Release 1.2.3"
git push origin v1.2.3

# Go to GitHub → Actions → CD → Latest run
# Click "Deploy to Production" → Confirm
```

#### Trigger Load Test

```bash
# Manual dispatch
# GitHub → Actions → load-test → "Run workflow" → Enter VUs/duration
```

### Workflow Files

**CI:** `.github/workflows/ci.yml`
```yaml
name: CI
on: [push, pull_request]
jobs:
  tests:
    runs-on: [self-hosted, local, rancher, nerdctl]
    # Tests run here
```

**CD:** `.github/workflows/cd.yml`
```yaml
name: CD
on: [push, release]
jobs:
  build:
    runs-on: [self-hosted, local, rancher, nerdctl]
    # Build and deploy here
```

**Load Test:** `.github/workflows/load-test.yml`
```yaml
name: load-test
on: [workflow_dispatch, schedule]
jobs:
  load_test:
    runs-on: [self-hosted, local, rancher, nerdctl]
    # k6 load test here
```

---

## Load Testing

### Local Load Test

```bash
# Install k6
brew install k6  # macOS
# or
apt-get install k6  # Linux

# Port-forward to analytics service
kubectl port-forward -n team4 svc/analytics-service 8000:8000 &

# Run load test
k6 run load-test/metrics_load_test.js

# Custom parameters
k6 run load-test/metrics_load_test.js \
  --vus=50 \
  --duration=120s
```

### Test Scenarios

The load test runs 3 concurrent scenarios:

1. **User Events** - POST to `/events/user`
   - Random user_id, email, status
   - ~33% of traffic

2. **Order Events** - POST to `/events/order`
   - Random order_id, status, amount
   - ~33% of traffic

3. **Notification Events** - POST to `/events/notification`
   - Random notification_id, type, status
   - ~33% of traffic

### Metrics Collected

- **Response Time (p95, p99)**
  - Threshold: p95 < 500ms, p99 < 1000ms

- **Error Rate**
  - Threshold: < 10%

- **Throughput**
  - Events per second during peak load

- **Processing Latency** (from app logs)
  - Average, p95, p99

- **Prometheus Metrics** (scraped live)
  - Consumer processing latency
  - Events processed (5-min increase)

### Load Test Output

```json
{
  "execution": {
    "total_requests": 18000,
    "successful_requests": 17820,
    "failed_requests": 180,
    "error_rate": "1.0%"
  },
  "performance": {
    "avg_response_time_ms": 245,
    "p95_response_time_ms": 480,
    "p99_response_time_ms": 950,
    "avg_processing_time_ms": 12
  },
  "throughput": {
    "total_events_processed": 17820,
    "events_per_second": "99.0"
  },
  "prometheus_insights": {
    "consumer_latency": { "value": "12.5" },
    "event_throughput": { "events_in_5m": "29500" }
  }
}
```

### Analyzing Results

1. **Check metrics vs thresholds**
   - Error rate should be < 10%
   - p95 latency should be < 500ms
   - If failed: review app logs

2. **Review Prometheus dashboard**
   - Open: `http://localhost:3000/` (Grafana)
   - Check: Analytics Service Dashboard
   - Monitor: CPU, memory, error rates during load test

3. **Check consumer lag**
   - Kafka lag should be ≤ 5 seconds
   - If higher: consumer is falling behind

---

## Troubleshooting

### Unit Tests Failing

```bash
# Run with verbose output
pytest tests/unit/test_core_logic.py -vv -s

# Run specific test
pytest tests/unit/test_core_logic.py::TestEventTimeParsing::test_iso_8601_timestamp -vv
```

**Common Issues:**
- Missing dependencies: `pip install -r app/requirements.txt`
- Import errors: Ensure `PYTHONPATH` includes project root: `export PYTHONPATH=$PWD`

### Integration Tests Timing Out

```bash
# Increase timeout
pytest tests/integration/test_event_pipeline.py --timeout=30

# Run with more verbose output
pytest tests/integration/test_event_pipeline.py -vv -s
```

### GitHub Actions Workflow Fails

**Check logs:**
1. Go to **GitHub → Actions → Failed workflow**
2. Click job name to expand
3. Scroll to bottom for error messages

**Common fixes:**
- Docker build fails: Check `docker/Dockerfile` syntax
- Tests fail: Verify `PYTHONPATH` in CI/CD env
- Deploy fails: Check kubectl access and namespace

```bash
# Debug runner environment
nerdctl ps  # Should show running containers
kubectl get nodes  # Should show k3s node
kubectl get ns  # Should show team4 namespace
```

### Load Test Issues

**"Service not reachable"**
```bash
# Verify port-forward is running
kubectl port-forward -n team4 svc/analytics-service 8000:8000

# Check service is ready
curl http://localhost:8000/health
```

**"Prometheus metrics unavailable"**
```bash
# Verify Prometheus is running
kubectl get pod -n monitoring -l app=prometheus

# Port-forward Prometheus
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090
```

**"High error rate during test"**
1. Check consumer logs: `kubectl logs -n team4 deploy/analytics-service`
2. Check Kafka lag: Visit Prometheus → Query `increase(kafka_consumer_lag[5m])`
3. Scale deployment: `kubectl scale deploy analytics-service -n team4 --replicas=3`

---

## Next Steps

1. ✅ Run unit tests locally to verify setup
2. ✅ Run integration tests with mocked services
3. ✅ Push code to GitHub to trigger CI workflow
4. ✅ Monitor first CI run
5. ✅ Run load test and analyze results
6. ✅ Monitor CD deployment

For questions, check service logs:
```bash
# Analytics service logs
kubectl logs -n team4 deploy/analytics-service -f

# Kafka consumer logs
kubectl logs -n team4 deploy/analytics-service -c consumer -f

# Consumer group lag
kubectl exec -it pod/kafka-0 -n kafka -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group analytics-consumer --describe
```
