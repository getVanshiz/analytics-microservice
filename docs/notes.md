create image

terraform apply -target=module.strimzi_operator

# If your namespace isn't there yet, create it first
terraform apply -target=module.ns_monitoring    

# Then install the stack (CRDs come with the chart)
terraform apply -target=module.monitoring


# check all services
kubectl get pods,svc,deploy -n monitoring
kubectl get pods,svc,deploy -n team4  



# Port-Forwarding
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
kubectl port-forward -n monitoring svc/kube-prometheus-stack-alertmanager 9093:9093
kubectl port-forward -n team4 svc/influxdb2 8086:80
kubectl port-forward -n team4 svc/analytics-service-analytics-service 8080:8080
kubectl get kafkatopics -n team4




# create or update analytics service
nerdctl --namespace k8s.io build -t analytics-service:v5 -f docker/Dockerfile .
cd terraform
terraform apply -auto-approve
kubectl -n team4 get secrets | grep analytics-service 
kubectl -n team4 delete secret sh.helm.release.v1.analytics-service.v5


------

# kafka
## Producer
kubectl apply -f manifests/all-topics-producer.yaml
kubectl logs deploy/all-topics-producer -n team4 -f

# scale them down
kubectl get deploy -n team4
kubectl scale deploy/all-topics-producer -n team4 --replicas=0
kubectl -n team4 scale deploy order-producer --replicas=0

# Consumer
kubectl logs deploy/analytics-service-analytics-service -n team4 -f
