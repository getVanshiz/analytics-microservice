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
  - name: git
    image: alpine/git:latest
    command: [cat]
    tty: true
"""
    }
  }
  
  environment {
    NAMESPACE = "team4"
    SERVICE_NAME = "analytics-service"
    GITHUB_REPO = "vanshiz-os/analytics-microservice"
    DOCKER_USERNAME = "vanshi29"
  }
  
  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('CI Validation Gate (GitHub Actions)') {
      steps {
        container('kubectl') {
          withCredentials([string(credentialsId: 'github-api-token', variable: 'GITHUB_TOKEN')]) {
            sh '''
              #!/bin/sh
              set -e
              echo "=========================================="
              echo "📋 GitHub Actions CI Validation (Gate)"
              echo "=========================================="
              
              apk add --no-cache curl jq git >/dev/null 2>&1 || true
              
              COMMIT_SHA="${GIT_COMMIT}"
              if [ -z "$COMMIT_SHA" ]; then
                COMMIT_SHA="$(git rev-parse HEAD)"
              fi
              echo "Commit SHA: $COMMIT_SHA"
              
              REPO="${GITHUB_REPO}"
              API="https://api.github.com"
              
              ATTEMPTS=0
              MAX_ATTEMPTS=60
              SLEEP_SECONDS=10
              
              while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
                ATTEMPTS=$((ATTEMPTS+1))
                
                RESPONSE="$(curl -s \
                  -H "Accept: application/vnd.github+json" \
                  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
                  "${API}/repos/${REPO}/commits/${COMMIT_SHA}/check-runs")"
                
                TOTAL="$(echo "$RESPONSE" | jq -r '.total_count')"
                
                if [ "$TOTAL" = "null" ] || [ -z "$TOTAL" ]; then
                  echo "⚠️  Unexpected response from GitHub Checks API"
                  sleep $SLEEP_SECONDS
                  continue
                fi
                
                echo "👉 Found $TOTAL check run(s)"
                
                if [ "$TOTAL" -eq 0 ]; then
                  echo "⏳ No check runs yet. Waiting ${SLEEP_SECONDS}s..."
                  sleep $SLEEP_SECONDS
                  continue
                fi
                
                INCOMPLETE="$(echo "$RESPONSE" | jq '[.check_runs[] | select(.status != "completed")] | length')"
                FAILURES="$(echo "$RESPONSE" | jq '[.check_runs[] | select(.status=="completed" and (.conclusion!="success" and .conclusion!="skipped" and .conclusion!="neutral"))] | length')"
                
                echo ""
                echo "📄 Check runs:"
                echo "$RESPONSE" | jq '.check_runs[] | {name, status, conclusion}'
                echo ""
                
                if [ "$INCOMPLETE" -gt 0 ]; then
                  echo "⏳ ${INCOMPLETE} check run(s) still in progress. Waiting ${SLEEP_SECONDS}s..."
                  sleep $SLEEP_SECONDS
                  continue
                fi
                
                if [ "$FAILURES" -gt 0 ]; then
                  echo "❌ One or more check runs failed."
                  exit 1
                fi
                
                echo "✅ All check runs completed successfully."
                exit 0
              done
              
              echo "⏰ Timeout waiting for check runs to complete."
              exit 1
            '''
          }
        }
      }
    }

    stage('Get Image SHA') {
      steps {
        container('git') {
          script {
            sh 'git config --global --add safe.directory "*"'
            env.IMAGE_SHA = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
            echo "🏷️  Image SHA: ${env.IMAGE_SHA}"
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
              cat providers_override.tf
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
              
              if [ ! -f terraform.tfstate ]; then
                echo "❌ ERROR: terraform.tfstate not found!"
                exit 1
              fi
              
              echo "✅ State file found, listing resources:"
              terraform state list
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
              echo "=========================================="
              echo "📦 Planning deployment with image SHA: ${IMAGE_SHA}"
              echo "=========================================="
              
              export TF_VAR_use_docker_hub=true
              export TF_VAR_docker_username="${DOCKER_USERNAME}"
              export TF_VAR_image_tag="${IMAGE_SHA}"
              export TF_VAR_rollout_nonce="${IMAGE_SHA}"
              
              echo "Variables:"
              echo "  - docker_username: ${DOCKER_USERNAME}"
              echo "  - image_tag: ${IMAGE_SHA}"
              echo "  - rollout_nonce: ${IMAGE_SHA}"
              
              terraform plan \
                -target=kubernetes_secret.influxdb_auth \
                -target=module.${SERVICE_NAME}.helm_release.app \
                -out=deployment.tfplan
            '''
          }
        }
      }
    }
    
    stage('Apply Deployment') {
      steps {
        container('terraform') {
          dir('terraform') {
            sh '''
              echo "=========================================="
              echo "🚀 Applying deployment..."
              echo "=========================================="
              
              terraform apply -auto-approve deployment.tfplan
              
              echo "✅ Terraform apply completed"
            '''
          }
        }
      }
    }
    
    stage('Verify Deployment') {
      steps {
        container('kubectl') {
          sh '''
            echo "=========================================="
            echo "🔍 Verifying deployment..."
            echo "=========================================="
            
            echo "📋 Pods in namespace ${NAMESPACE}:"
            kubectl get pods -n ${NAMESPACE} -l app.kubernetes.io/name=${SERVICE_NAME}
            
            echo ""
            echo "⏳ Waiting for rollout to complete..."
            kubectl rollout status deployment/${SERVICE_NAME}-${SERVICE_NAME} \
              -n ${NAMESPACE} --timeout=5m
            
            echo ""
            echo "✅ Deployment completed successfully"
            echo ""
            echo "📊 Deployment details:"
            kubectl get deployment/${SERVICE_NAME}-${SERVICE_NAME} -n ${NAMESPACE} -o wide
            
            echo ""
            echo "🏷️  Checking image tag:"
            kubectl get deployment/${SERVICE_NAME}-${SERVICE_NAME} -n ${NAMESPACE} \
              -o jsonpath='{.spec.template.spec.containers[0].image}'
            echo ""
          '''
        }
      }
    }

    stage('Health Check') {
      steps {
        container('kubectl') {
          sh '''
            echo "=========================================="
            echo "🏥 Running health checks..."
            echo "=========================================="
            
            # Wait a bit for pod to be fully ready
            sleep 10
            
            POD_NAME=$(kubectl get pods -n ${NAMESPACE} \
              -l app.kubernetes.io/name=${SERVICE_NAME} \
              -o jsonpath='{.items[0].metadata.name}')
            
            echo "Selected pod: $POD_NAME"
            
            # Check if pod is running
            POD_STATUS=$(kubectl get pod $POD_NAME -n ${NAMESPACE} \
              -o jsonpath='{.status.phase}')
            
            echo "Pod status: $POD_STATUS"
            
            if [ "$POD_STATUS" != "Running" ]; then
              echo "❌ Pod is not running!"
              kubectl describe pod $POD_NAME -n ${NAMESPACE}
              exit 1
            fi
            
            echo "✅ Pod is running"
            
            # Show recent logs
            echo ""
            echo "📝 Recent logs:"
            kubectl logs $POD_NAME -n ${NAMESPACE} --tail=20 || true
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
          echo ""
          echo "=========================================="
          echo "🎉 Deployment Summary"
          echo "=========================================="
          echo "Service: ${SERVICE_NAME}"
          echo "Namespace: ${NAMESPACE}"
          echo "Image SHA: ${IMAGE_SHA}"
          echo ""
          kubectl get deployment/${SERVICE_NAME}-${SERVICE_NAME} -n ${NAMESPACE} -o wide
          echo ""
          kubectl get pods -n ${NAMESPACE} -l app.kubernetes.io/name=${SERVICE_NAME}
        '''
      }
    }
    
    failure {
      echo "❌ Deployment failed!"
      container('kubectl') {
        sh '''
          echo ""
          echo "=========================================="
          echo "🔍 Debug Information"
          echo "=========================================="
          echo "Deployment description:"
          kubectl describe deployment/${SERVICE_NAME}-${SERVICE_NAME} -n ${NAMESPACE} || true
          echo ""
          echo "Pod logs:"
          kubectl logs -n ${NAMESPACE} -l app.kubernetes.io/name=${SERVICE_NAME} --tail=100 || true
          echo ""
          echo "Events:"
          kubectl get events -n ${NAMESPACE} --sort-by='.lastTimestamp' | tail -20 || true
        '''
      }
    }
    
    always {
      container('terraform') {
        dir('terraform') {
          sh 'rm -f providers_override.tf deployment.tfplan || true'
        }
      }
    }
  