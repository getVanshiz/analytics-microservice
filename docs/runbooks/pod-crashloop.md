# Runbook: Pod CrashLoop / Service Not Starting – Analytics Service

## Severity
SEV-1 (Service unavailable)

---

## Purpose

This runbook provides steps to recover the Analytics Service when pods fail to start or repeatedly crash.

---

## Trigger Conditions

- Pod in `CrashLoopBackOff`
- `/health` endpoint unreachable
- No metrics scraped by Prometheus

---

## Immediate Actions (0–3 minutes)

### Step 1: Inspect Pod Status
```bash
kubectl get pods -n team4
kubectl describe pod <analytics-pod> -n team4
```

Check:
- Exit codes
- Restart count
- Recent events
### Step 2: Inspect Previous Logs

```Bash
kubectl logs <analytics-pod> -n team4 --previous
```

- Identify whether failure occurs:
    - Immediately on startup
    - After initialization
    - After external dependency call
    - Diagnosis & Resolution Paths
### Case A: Configuration / Environment Issues

Indicators
- Startup exceptions
- Missing configuration errors

Actions

```Bash
kubectl describe deploy analytics-service-analytics-service -n team4
```
Verify presence of:
- Kafka bootstrap servers
- InfluxDB URL, token, bucket
- OTEL exporter endpoint

Resolution
- Fix configuration
- Redeploy service
### Case B: Secret / Credential Issues

Indicators
- Authentication failures
- Permission denied errors

Actions

```Bash
kubectl get secrets -n team4
kubectl describe secret influxdb-auth -n team4
```
Resolution
- Recreate secret
- Restart deployment

### Case C: Bad Image or Code Regression
Indicators
- Crash started after deployment
- Previous version was stable

Actions

```Bash
kubectl rollout history deploy/analytics-service-analytics-service -n team4

kubectl rollout undo deploy/analytics-service-analytics-service -n team4
```
---
Verification
- Recovery is successful when:
- Pod reaches Running
- Restart count stops increasing
- /health returns 200
- Metrics visible in Prometheus

Post-Incident Actions
- Add startup validation checks
- Improve readiness and liveness probes
- Document regression cause