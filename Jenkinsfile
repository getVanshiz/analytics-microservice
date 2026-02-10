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
  - name: curl
    image: curlimages/curl:latest
    command: [cat]
    tty: true
"""
    }
  }
  
  environment {
    NAMESPACE = "team4"
    SERVICE_NAME = "analytics-service"
    GITHUB_REPO = "vanshiz-os/analytics-microservice"
  }
  
  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }
    
    stage('Check CI Status') {  // ✅ New stage
      steps {
        container('curl') {
          script {
            // Get current commit SHA
            def sha = sh(
              script: "git rev-parse HEAD",
              returnStdout: true
            ).trim()
            
            echo "📋 Checking GitHub Actions CI status for commit: ${sha}"
            
            // Check CI status via GitHub API
            def response = sh(
              script: """
                curl -s \
                  -H "Accept: application/vnd.github.v3+json" \
                  https://api.github.com/repos/${GITHUB_REPO}/commits/${sha}/status
              """,
              returnStdout: true
            )
            
            echo "GitHub API Response: ${response}"
            
            // Parse JSON response
            def jsonResponse = readJSON text: response
            def state = jsonResponse.state
            
            echo "✅ GitHub Actions CI status: ${state}"
            
            // Check if CI passed
            if (state == "success") {
              echo "✅ CI passed! Proceeding with deployment..."
            } else if (state == "pending") {
              error("⏳ CI is still running. Wait for CI to complete before deploying.")
            } else if (state == "failure") {
              error("❌ CI failed! Fix tests before deploying.")
            } else {
              echo "⚠️  No CI status found. Proceeding anyway (assuming first build)..."
            }
          }
        }
      }
    }
    
    stage('Configure IaC Provider') {
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
    
    // ... rest of your stages remain same
    
    stage('Terraform Init') {
      steps {
        container('terraform') {
          dir('terraform') {
            sh '''
              terraform init -upgrade
              
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
              if [ -f terraform.tfstate ]; then
                echo "✅ State file updated"
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
            echo "📋 Checking service deployment..."
            kubectl get pods -n ${NAMESPACE} -l app.kubernetes.io/name=${SERVICE_NAME}
            
            echo "✅ Waiting for rollout..."
            kubectl rollout status deploy/${SERVICE_NAME}-${SERVICE_NAME} \
              -n ${NAMESPACE} --timeout=3m
          '''
        }
      }
    }
  }
  
  post {
    success {
      echo "✅ Deployment successful!"
      container('kubectl') {
        sh '''
          kubectl get deploy/${SERVICE_NAME}-${SERVICE_NAME} -n ${NAMESPACE} -o wide
        '''
      }
    }
    failure {
      echo "❌ Deployment failed!"
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