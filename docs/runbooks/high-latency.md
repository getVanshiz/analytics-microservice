# Runbook: High Latency / Timeouts – Analytics Service

## Severity
SEV-2 (Performance degradation)

---

## Purpose

This runbook addresses increased event processing latency or request timeouts in the Analytics Service.

---

## Trigger Conditions

Execute this runbook when:
- p95 latency > 500 ms for 5 minutes
- Kafka consumer lag increases steadily
- Jaeger traces show long-running spans

---

## Impact

- Delayed analytics visibility
- Kafka backlog accumulation
- Reduced reliability of dashboards

---

## Immediate Triage (0–5 minutes)

### Step 1: Identify Latency Source
Open Grafana:
- Event processing latency (p95)
- Kafka consumer lag
- CPU and memory utilization

Determine whether latency correlates with load or occurs suddenly.

---

### Step 2: Analyze Traces

Open Jaeger:
- Search for recent traces
- Sort by duration
- Identify longest span

Common bottlenecks:
- `kafka.consume`
- `influx.write`
- `Kafka.produce`

---

## Diagnosis & Resolution Paths

### Case A: Kafka Backlog / Under-Scaling

**Indicators**
- Consumer lag increasing
- Event rate > processing rate

**Actions**
```bash
kubectl describe deploy analytics-service-analytics-service -n team4
```
Resolution

- Scale analytics service (if allowed)

```Bash
kubectl scale deploy analytics-service-analytics-service --replicas=2 -n team4
```
---
### Case B: InfluxDB Slow Writes
Indicators

- influx.write dominates trace duration
- Latency increases gradually

Actions

```Bash
kubectl logs deploy/influxdb2 -n team4
```
Resolution

- Restart InfluxDB pod
- Reduce write batch size (if configurable)

--- 
### Case C: Resource Throttling

Indicators
- CPU near limit
- Latency spikes align with load tests

Actions

- Review resource limits in Grafana
- Check Kubernetes events

Resolution
- Increase CPU/memory limits via Helm
- Redeploy service

---

Verification
- Latency issue is resolved when:
- p95 latency < 200 ms
- Kafka lag stabilizes
- Traces show reduced span duration

Post-Incident Actions

- Adjust autoscaling or resource limits
- Add latency-based alerts
- Document scaling decisions


---

