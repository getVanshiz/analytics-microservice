resource "kubernetes_manifest" "kibana_seeder_job" {
  manifest = {
    apiVersion = "batch/v1"
    kind       = "Job"
    metadata = {
      name      = "${var.name}-seed"
      namespace = var.namespace
      labels = {
        app = "${var.name}-seed"
      }
    }
    spec = {
      backoffLimit = 3
      template = {
        metadata = {
          name = "${var.name}-seed"
          labels = { app = "${var.name}-seed" }
        }
        spec = {
          restartPolicy = "OnFailure"
          containers = [
            {
              name  = "seed"
              image = "curlimages/curl:8.6.0"
              command = [
                "sh", "-c",
                <<-EOT
                set -euo pipefail

                K="$KIBANA_URL"

                echo "Waiting for Kibana at $K ..."
                for i in $(seq 1 60); do
                  if curl -sf "$K/api/status" | grep -q '"level":"available"'; then
                    echo "Kibana is available."
                    break
                  fi
                  echo "Kibana not ready yet, retry $i/60..."
                  sleep 5
                done

                echo "Create index pattern logs-* (idempotent)"
                curl -sf -X POST "$K/api/saved_objects/index-pattern/logs-*" \
                  -H 'kbn-xsrf: true' -H 'Content-Type: application/json' \
                  -d '{"attributes": {"title": "logs-*", "timeFieldName": "@timestamp"}}' || true

                echo "Saved search: ERROR last 1h"
                curl -sf -X POST "$K/api/saved_objects/search/error_last_1h" \
                  -H 'kbn-xsrf: true' -H 'Content-Type: application/json' \
                  -d '{"attributes":{"title":"ERROR last 1h","columns":["timestamp","level","service","message","trace_id"],"kibanaSavedObjectMeta":{"searchSourceJSON":"{\\"query\\":{\\"language\\":\\"kuery\\",\\"query\\":\\"level : \\\\\\"ERROR\\\\\\" and @timestamp >= now()-1h\\"},\\"filter\\":[]}"}}' || true

                echo "Saved search: Slow requests"
                curl -sf -X POST "$K/api/saved_objects/search/slow_requests" \
                  -H 'kbn-xsrf: true' -H 'Content-Type: application/json' \
                  -d '{"attributes":{"title":"Slow requests (latency_ms > 500)","columns":["timestamp","service","endpoint","latency_ms","trace_id","message"],"kibanaSavedObjectMeta":{"searchSourceJSON":"{\\"query\\":{\\"language\\":\\"kuery\\",\\"query\\":\\"latency_ms > 500\\"},\\"filter\\":[]}"}}' || true

                echo "Saved search: Logs by trace_id"
                curl -sf -X POST "$K/api/saved_objects/search/trace_lookup" \
                  -H 'kbn-xsrf: true' -H 'Content-Type: application/json' \
                  -d '{"attributes":{"title":"Logs by trace_id","columns":["timestamp","service","message","trace_id","user_id","order_id"],"kibanaSavedObjectMeta":{"searchSourceJSON":"{\\"query\\":{\\"language\\":\\"kuery\\",\\"query\\":\\"\\"},\\"filter\\":[]}"}}' || true

                echo "Seeding complete."
                EOT
              ]
              env = [
                {
                  name  = "KIBANA_URL"
                  value = "https://kibana-kibana.${var.namespace}.svc.cluster.local:5601"
                }
              ]
            }
          ]
        }
      }
    }
  }

  # 👇 This is the important part
  computed_fields = [
    "metadata.labels",
    "spec.template.metadata.labels",
  ]

  # (Optional) If you use SSA or see conflict errors:
  # field_manager {
  #   force_conflicts = true
  # }

  # (Optional) Wait for the Job to complete successfully
  # wait {
  #   fields  = { "status.succeeded" = "1" }
  #   timeout = "10m"
  # }
}
