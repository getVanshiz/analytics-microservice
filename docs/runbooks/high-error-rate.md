# Runbook: High Error Rate – Analytics Service

## Severity
SEV-2 (Partial system degradation, analytics accuracy impacted)

---

## Purpose

This runbook provides step-by-step guidance to diagnose and mitigate high error rates in the Analytics Service, which consumes Kafka events and generates observability data.

---

## Trigger Conditions

Initiate this runbook if **any** of the following conditions hold for more than 5 minutes:

- `analytics_processing_errors_total` increases continuously
- HTTP 5xx responses > 1% of total requests
- `analytics_influx_writes_total{status="failure"}` increases
- Event consumption rate drops unexpectedly

---

## Impact Assessment

Potential impacts include:
- Loss or delay of analytics data
- Inaccurate dashboards
- Reduced ability to debug upstream services
- Kafka backlog growth

---

## Immediate Triage (0–5 minutes)

### Step 1: Confirm the Issue
- Open Grafana
- Verify error metrics are increasing
- Check Prometheus target health

If error rate is transient (<2 minutes), **monitor only**.

---

### Step 2: Check Pod Health
```bash
kubectl get pods -n team4

```
- If pods are restarting → switch to Pod CrashLoop Runbook
- If pods are running → continue

### Step 3: Inspect Error Logs
Kibana Query:
```Kibana query:
service.name:"analytics-service" AND log.level:"ERROR" AND @timestamp >= now-15m
```
Group errors by message to identify dominant failure pattern.

## Diagnosis & Resolution Paths

### Case A: Kafka Connectivity Errors
Indicators
Logs contain KafkaTimeoutError, Failed to fetch metadata
`analytics_events_consumed_total` flatlines

Actions
```Bash
kubectl get pods -n team4 | grep kafka
kubectl logs <kafka-broker-pod> -n team4
```
Resolution

- Restart Analytics Service

```Bash
kubectl rollout restart deploy/analytics-service-analytics-service -n team4
```

If Kafka unstable, restart Kafka broker

### Case B: Schema Validation Errors
- Indicators
  - Errors mention missing or invalid fields
  - Errors limited to one Kafka topic

Actions


- Identify affected topic
- Validate producer schema
- Inform upstream team

Mitigation

- Allow service to continue processing valid events
- Do NOT stop consumer unless error volume threatens stability

### Case C: InfluxDB Write Failures
Indicators

- Write failures metric increases
- Logs show authentication or timeout errors

Actions

```Bash
kubectl logs deploy/influxdb2 -n team4
kubectl get secrets -n team4 | grep influx
```
If authentication error,

```Bash
kubectl delete secret influxdb-auth -n team4

kubectl create secret generic influxdb-auth -n team4 --from-literal=token='TOKEN'

kubectl -n team4 rollout restart deploy/analytics-service-analytics-service
```

Resolution
- Restart InfluxDB pod
- Revalidate token and bucket configuration

Escalation & Mitigation
- If no clear root cause within 15 minutes:
- Restart Analytics Service
- Temporarily reduce consumer concurrency if configurable

Verification

- Issue is resolved when:
  - Error metrics stabilize
  - No new ERROR logs for 10 minutes
  - Events appear normally in dashboards

Post-Incident Actions
- Document root cause
- Add or tune alerts
- Improve validation or retry logic if applicable