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
    SERVICE_NAME = "analytics-service"  // ✅ Centralized
  }
  
  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }
    
    stage('Configure IaC Provider') {  // ✅ Generic
      steps {
        container('terraform') {
          dir('terraform') {
            sh '''
              # In-cluster provider config
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
            sh '''
              terraform init -upgrade
              
              # Verify state file exists
              if [ ! -f terraform.tfstate ]; then
                echo "❌ ERROR: terraform.tfstate not found in Git!"
                echo "Please run manual import first (see docs)"
                exit 1
              fi
              
              echo "✅ State file found, listing resources:"
              terraform state list
            '''
          }
        }
      }
    }
    
    stage('Refresh State') {
      steps {
        container('terraform') {
          dir('terraform') {
            sh '''
              # Refresh state from cluster (non-destructive)
              terraform refresh \
                -target=module.${SERVICE_NAME}.helm_release.app
            '''
          }
        }
      }
    }
    
    stage('Plan Deployment') {  
      steps {
        container('terraform') {
          dir('terraform') {
            sh '''
              terraform plan \
                -target=module.${SERVICE_NAME}.helm_release.app \
                -out=service.tfplan
            '''
          }
        }
      }
    }
    
    stage('Apply Changes') {  
      steps {
        container('terraform') {
          dir('terraform') {
            sh 'terraform apply -auto-approve service.tfplan'
          }
        }
      }
    }
    
    stage('Commit Updated State') {
      steps {
        container('terraform') {
          dir('terraform') {
            sh '''
              # Optional: Push updated state back to Git
              # (Only if you want to track state changes)
              if [ -f terraform.tfstate ]; then
                echo " State file updated"
                # Uncomment below to auto-commit state
                # git config user.email "jenkins@ci.local"
                # git config user.name "Jenkins CI"
                # git add terraform.tfstate
                # git commit -m "Update terraform state [skip ci]" || true
                # git push origin main
              fi
            '''
          }
        }
      }
    }
    
    stage('Verify Deployment') {
      steps {
        container('kubectl') {
          sh '''
            echo " Checking service deployment..."
            kubectl get pods -n ${NAMESPACE} -l app.kubernetes.io/name=${SERVICE_NAME}
            
            echo " Waiting for rollout..."
            kubectl rollout status deploy/${SERVICE_NAME}-${SERVICE_NAME} \
              -n ${NAMESPACE} --timeout=3m
          '''
        }
      }
    }
  }
  
  post {
    success {
      echo "Deployment successful!"  
      container('kubectl') {
        sh '''
          kubectl get deploy/${SERVICE_NAME}-${SERVICE_NAME} -n ${NAMESPACE} -o wide
        '''
      }
    }
    failure {
      echo " Deployment failed!" 
      container('kubectl') {
        sh '''
          echo "Debug info:"
          kubectl describe deploy/${SERVICE_NAME}-${SERVICE_NAME} -n ${NAMESPACE} || true
          kubectl logs -n ${NAMESPACE} -l app.kubernetes.io/name=${SERVICE_NAME} --tail=50 || true
        '''
      }
    }
    always {
      container('terraform') {
        dir('terraform') {
          sh 'rm -f providers_override.tf service.tfplan || true'  
        }
      }
    }
  }
}
