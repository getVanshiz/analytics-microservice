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
    
    stage('Configure Terraform for K8s') {
      steps {
        container('terraform') {
          dir('terraform') {
            sh '''
              # In-cluster auth setup (Jenkins pod ke andar se K8s access)
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
    
    stage('Import Analytics Service') {
      steps {
        container('terraform') {
          dir('terraform') {
            sh '''
              # Existing Helm release ko import karo state mein
              terraform import \
                module.analytics_service.helm_release.app \
                ${NAMESPACE}/analytics-service || echo "Already imported"
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
              # Sirf analytics service ka plan dekho
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
            
            echo "🏥 Health check..."
            sleep 5
            kubectl get svc analytics-service-analytics-service -n ${NAMESPACE}
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

