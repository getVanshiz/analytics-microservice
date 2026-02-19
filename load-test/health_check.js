// load-test/health_check.js
import http from "k6/http";
import { check } from "k6";

export const options = {
  scenarios: {
    steady_rps: {
      executor: "constant-arrival-rate",
      rate: 100,            // 100 requests per second
      timeUnit: "1s",
      duration: "60s",
      preAllocatedVUs: 50,
      maxVUs: 200,
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<50", "p(99)<100"],
  },
};

export default function () {
  const res = http.get("http://localhost:8080/health");
  check(res, { "status is 200": (r) => r.status === 200 });
}