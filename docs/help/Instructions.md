If the service doesn't start with this try set wise,

- make namespaces first
```bash
terraform apply \
  -target=module.namespace \
  -target=module.ns_monitoring \
  -target=module.ns_observability \
  -target=kubernetes_namespace_v1.strimzi
```

- Start strimzi Operator

```bash
terraform apply \
  -target=module.strimzi_operator
```
- Verify Installation

```bash
kubectl get crd | grep kafka.strimzi.io
```

- Apply Kafka CRDs

```bash
terraform apply -target=module.kafka

kubectl get kafka -n team4
kubectl get kafkanodepool -n team4
```

- Create Topics
```bash
terraform apply \
  -target=module.kafka_topic_user_events \
  -target=module.kafka_topic_order_events \
  -target=module.kafka_topic_notification_events \
  -target=module.kafka_topic_analytics_events
```


- Create Monitoring CRDs

```bash
terraform apply -target=module.monitoring
kubectl get crd | grep monitoring.coreos.com
```
- Create Influx DB module
```bash
terraform apply -target=module.influxdb2
```

Goto localhost:8086 get an all access API token, Then paste in following command

```bash
kubectl create secret generic influxdb-auth -n team4 --from-literal=token=‘TOKEN’
```

- Apply Analytics module
```bash
terraform apply -target=module.analytics_service 
```

- Apply ServiceMonitors for metrics scraping
```bash
terraform apply \
  -target=kubernetes_manifest.analytics_service_monitor \
  -target=kubernetes_manifest.influxdb_sm \
  -target=kubernetes_manifest.kafka_exporter_sm
```

- Apply Opentelemetry and Jaeger

```bash
terraform apply \
  -target=module.jaeger \
  -target=module.opentelemetry
```

- Apply EFK Stack module
```bash
terraform apply \
  -target=module.elasticsearch \
  -target=module.kibana \
  -target=module.filebeat
  - target=module.kibana_objects
 ``` 
finally,
```bash
  terraform apply
```