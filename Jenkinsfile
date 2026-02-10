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

              # Tools (only on first run; Alpine base)
              apk add --no-cache curl jq >/dev/null

              # Resolve commit SHA (Jenkins sets GIT_COMMIT after checkout)
              COMMIT_SHA="${GIT_COMMIT}"
              if [ -z "$COMMIT_SHA" ]; then
                COMMIT_SHA="$(git rev-parse HEAD)"
              fi
              echo "Commit SHA: $COMMIT_SHA"

              REPO="${GITHUB_REPO}"
              API="https://api.github.com"

              # Poll until all check runs complete or timeout
              ATTEMPTS=0
              MAX_ATTEMPTS=60    # ~10 minutes (sleep 10s)
              SLEEP_SECONDS=10

              while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
                ATTEMPTS=$((ATTEMPTS+1))

                RESPONSE="$(curl -s \
                  -H "Accept: application/vnd.github+json" \
                  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
                  "${API}/repos/${REPO}/commits/${COMMIT_SHA}/check-runs")"

                TOTAL="$(echo "$RESPONSE" | jq -r '.total_count')"
                if [ "$TOTAL" = "null" ] || [ -z "$TOTAL" ]; then
                  echo "⚠️  Unexpected response from GitHub Checks API:"
                  echo "$RESPONSE"
                  echo "Retrying in ${SLEEP_SECONDS}s..."
                  sleep $SLEEP_SECONDS
                  continue
                fi

                echo "👉 Found $TOTAL check run(s)"

                if [ "$TOTAL" -eq 0 ]; then
                  # No check runs yet — maybe Actions is delayed; wait a bit.
                  echo "⏳ No check runs yet. Waiting ${SLEEP_SECONDS}s..."
                  sleep $SLEEP_SECONDS
                  continue
                fi

                # Count incomplete and failed runs
                INCOMPLETE="$(echo "$RESPONSE" | jq '[.check_runs[] | select(.status != "completed")] | length')"
                FAILURES="$(echo "$RESPONSE" | jq '[.check_runs[] | select(.status=="completed" and (.conclusion!="success" and .conclusion!="skipped" and .conclusion!="neutral"))] | length')"

                echo ""
                echo "📄 Check runs:"
                echo "$RESPONSE" | jq '.check_runs[] | {name, status, conclusion, started_at, completed_at, html_url}'
                echo ""

                if [ "$INCOMPLETE" -gt 0 ]; then
                  echo "⏳ ${INCOMPLETE} check run(s) still in progress. Waiting ${SLEEP_SECONDS}s..."
                  sleep $SLEEP_SECONDS
                  continue
                fi

                if [ "$FAILURES" -gt 0 ]; then
                  echo "❌ One or more check runs failed (or were cancelled/timed_out)."
                  exit 1
                fi

                echo "✅ All check runs completed successfully (or skipped/neutral)."
                exit 0
              done

              echo "⏰ Timeout waiting for check runs to complete after $((MAX_ATTEMPTS*SLEEP_SECONDS))s."
              exit 1
            '''
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

    stage('Deploy New Image with SHA') {
      steps {
        container('terraform') {
          dir('terraform') {

            sh '''
              echo "=========================================="
              echo "📦 Deploying new image using Git SHA"
              echo "=========================================="
              git config --global --add safe.directory "*"
              # Determine Git SHA (short)
              IMAGE_SHA=$(git rev-parse --short HEAD)
              echo "Using image tag: $IMAGE_SHA"

              export TF_VAR_use_docker_hub=true
              export TF_VAR_docker_username="vanshi29"
              export TF_VAR_image_tag="$IMAGE_SHA"
              export TF_VAR_rollout_nonce="$IMAGE_SHA"

              echo "🔧 Running targeted Terraform apply..."
              terraform apply -auto-approve \
                -target=module.${SERVICE_NAME}.helm_release.app
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