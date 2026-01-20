create image

terraform apply -target=module.strimzi_operator

# If your namespace isn't there yet, create it first
terraform apply -target=module.ns_monitoring    

# Then install the stack (CRDs come with the chart)
terraform apply -target=module.monitoring


# check
kubectl get pods,svc,deploy -n monitoring
kubectl get pods,svc,deploy -n team4  


kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090

kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80

kubectl port-forward -n monitoring svc/kube-prometheus-stack-alertmanager 9093:9093

kubectl port-forward -n team4 svc/influxdb2 8086:80

kubectl port-forward -n team4 svc/analytics-service-analytics-service 8080:8080

kubectl get kafkatopics -n team4