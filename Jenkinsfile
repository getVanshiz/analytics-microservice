pipeline {
  agent {
    kubernetes {
      yaml """
apiVersion: v1
kind: Pod
spec:
  serviceAccountName: jenkins
  containers:
  - name: terraform
    image: hashicorp/terraform:1.5
    command: [cat]
    tty: true
  - name: kubectl
    image: alpine/k8s:1.28.3
    command: [cat]
    tty: true
"""
    }
  }
  
  environment {
    NAMESPACE = "team4"
  }
  
  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }
    
    stage('Configure Terraform') {
      steps {
        container('terraform') {
          dir('terraform') {
            sh '''
              cat > providers_override.tf <<'EOF'
provider "kubernetes" {
  host                   = "https://kubernetes.default.svc"
  token                  = file("/var/run/secrets/kubernetes.io/serviceaccount/token")
  cluster_ca_certificate = file("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
}

provider "helm" {
  kubernetes {
    host                   = "https://kubernetes.default.svc"
    token                  = file("/var/run/secrets/kubernetes.io/serviceaccount/token")
    cluster_ca_certificate = file("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
  }
}
EOF
            '''
          }
        }
      }
    }
    
    stage('Terraform Init') {
      steps {
        container('terraform') {
          dir('terraform') {
            sh 'terraform init -upgrade'
          }
        }
      }
    }
    
    stage('Import ALL Existing Resources') {
      steps {
        container('terraform') {
          dir('terraform') {
            sh '''
              # Import namespaces
              terraform import kubernetes_namespace_v1.strimzi strimzi || echo "Already imported"
              terraform import module.namespace.kubernetes_namespace_v1.ns team4 || echo "Already imported"
              
              # Import Strimzi operator
              terraform import module.strimzi_operator.helm_release.strimzi strimzi/strimzi-operator || echo "Already imported"
              
              # Import Kafka resources (skip if fails)
              terraform import module.kafka.kubernetes_manifest.kafka_nodepool_dualrole \
                "apiVersion=kafka.strimzi.io/v1beta2,kind=KafkaNodePool,namespace=team4,name=team4-kafka-np-dual" || echo "Skip"
              
              terraform import module.kafka.kubernetes_manifest.kafka_cluster \
                "apiVersion=kafka.strimzi.io/v1beta2,kind=Kafka,namespace=team4,name=team4-kafka" || echo "Skip"
              
              # Import InfluxDB
              terraform import module.influxdb2.helm_release.influxdb2 team4/influxdb2 || echo "Already imported"
              
              # Import Analytics Service (MAIN TARGET)
              terraform import module.analytics_service.helm_release.app team4/analytics-service || echo "Already imported"
            '''
          }
        }
      }
    }
    
    stage('Plan Analytics Update') {
      steps {
        container('terraform') {
          dir('terraform') {
            sh '''
              terraform plan \
                -target=module.analytics_service.helm_release.app \
                -out=analytics.tfplan
            '''
          }
        }
      }
    }
    
    stage('Apply Analytics Update') {
      steps {
        container('terraform') {
          dir('terraform') {
            sh 'terraform apply analytics.tfplan'
          }
        }
      }
    }
    
    stage('Verify Deployment') {
      steps {
        container('kubectl') {
          sh '''
            echo "📋 Checking analytics service..."
            kubectl get pods -n ${NAMESPACE} -l app.kubernetes.io/name=analytics-service
            
            echo "✅ Waiting for rollout..."
            kubectl rollout status deploy/analytics-service-analytics-service \
              -n ${NAMESPACE} --timeout=3m
          '''
        }
      }
    }
  }
  
  post {
    success {
      echo "✅ Analytics service updated successfully!"
    }
    failure {
      echo "❌ Update failed!"
      container('kubectl') {
        sh '''
          echo "Debug info:"
          kubectl describe deploy/analytics-service-analytics-service -n ${NAMESPACE} || true
          kubectl logs -n ${NAMESPACE} -l app.kubernetes.io/name=analytics-service --tail=20 || true
        '''
      }
    }
    always {
      container('terraform') {
        dir('terraform') {
          sh 'rm -f providers_override.tf analytics.tfplan || true'
        }
      }
    }
  }
}
