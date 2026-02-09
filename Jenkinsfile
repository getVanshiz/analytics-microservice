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
    command:
    - cat
    tty: true
  - name: kubectl
    image: alpine/k8s:1.28.3
    command:
    - cat
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
        sh 'ls -la'
        sh 'ls -la terraform/'
      }
    }
    
    stage('Terraform Init') {
      steps {
        container('terraform') {
          dir('terraform') {
            sh 'terraform init'
          }
        }
      }
    }
    
    stage('Import Existing Resources') {
      steps {
        container('terraform') {
          dir('terraform') {
            sh '''
              echo "Importing existing resources..."
              terraform import -input=false kubernetes_namespace_v1.strimzi strimzi 2>/dev/null || echo "strimzi namespace already imported or doesn't exist"
              terraform import -input=false module.namespace.kubernetes_namespace_v1.ns team4 2>/dev/null || echo "team4 namespace already imported or doesn't exist"
            '''
          }
        }
      }
    }
    
    stage('Terraform Apply') {
      steps {
        container('terraform') {
          dir('terraform') {
            sh '''
              terraform apply \
                -target=module.analytics_service.helm_release.app \
                -auto-approve
            '''
          }
        }
      }
    }
    
    stage('Verify Deployment') {
      steps {
        container('kubectl') {
          sh '''
            echo "⏳ Waiting for deployment..."
            sleep 15
            echo "📋 Checking pods..."
            kubectl get pods -n ${NAMESPACE} -l app.kubernetes.io/name=analytics-service
            echo "✅ Verifying rollout..."
            kubectl rollout status deploy/analytics-service-analytics-service -n ${NAMESPACE} --timeout=5m
          '''
        }
      }
    }
  }
  
  post {
    success {
      echo "✅ Deployment successful!"
    }
    failure {
      echo "❌ Deployment failed!"
    }
  }
}