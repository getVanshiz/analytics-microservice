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
nerdctl --namespace k8s.io build -t analytics-service:v19 -f docker/Dockerfile .
cd terraform
change version in main.tf
terraform apply -auto-approve

kubectl -n team4 get secrets | grep analytics-service 
kubectl -n team4 delete secret sh.helm.release.v1.analytics-service.v11


------

# kafka
## Producer
kubectl apply -f manifests/all-topic-producer.yaml
kubectl logs deploy/all-topics-producer -n team4 -f

# scale them down
kubectl get deploy -n team4
kubectl scale deploy/all-topics-producer -n team4 --replicas=0


# Consumer
kubectl logs deploy/analytics-service-analytics-service -n team4 -f



- kubectl delete secret influxdb-auth -n team4
- kubectl create secret generic influxdb-auth -n team4 \
  --from-literal=token='dYdM_rEyjoGAMyIMNH8g2hqzMkl0b40Dg3_5SOz6z7MzRrBoXrdAh792NHJgvPhYsQW5tMWZgWmublLc-i83TQ=='
- kubectl -n team4 rollout restart deploy/analytics-service-analytics-service
- terraform apply --auto-approve


# Remove release (statefulset will go)
helm uninstall elasticsearch -n observability

# Delete ES data PVC (wipes data; fixes stale index/permission)
kubectl -n observability delete pvc -l app=elasticsearch-master
# or explicitly:
# kubectl -n observability delete pvc elasticsearch-master-elasticsearch-master-0

# Re-apply with Terraform so Helm recreates cleanly
terraform apply -auto-approve

# Watch pods
kubectl -n observability get pods -w


----


# Current container logs (last 200 lines)
kubectl -n observability logs elasticsearch-master-0 -c elasticsearch --tail=200

# Previous crash logs (why it exited with code 1 earlier)
kubectl -n observability logs elasticsearch-master-0 -c elasticsearch --previous --tail=200


# Elastic search
kubectl get secret -n observability elasticsearch-master-credentials \
  -o jsonpath='{.data.password}' | base64 --decode

curl -k -u elastic:<Password> https://localhost:9200/