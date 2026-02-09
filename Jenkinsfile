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
        sh 'echo "Checking terraform directory..."'
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
    
    stage('Terraform Plan') {
      steps {
        container('terraform') {
          dir('terraform') {
            sh 'terraform plan -target=module.analytics_service'
          }
        }
      }
    }
    
    stage('Terraform Apply') {
      steps {
        container('terraform') {
          dir('terraform') {
            sh 'terraform apply -target=module.analytics_service -auto-approve'
          }
        }
      }
    }
    
    stage('Verify Deployment') {
      steps {
        container('kubectl') {
          sh '''
            echo "Waiting for deployment to stabilize..."
            sleep 15
            echo "Checking pods in namespace ${NAMESPACE}..."
            kubectl get pods -n ${NAMESPACE} -l app.kubernetes.io/name=analytics-service
            echo "Checking rollout status..."
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