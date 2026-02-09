import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Thresholds for test pass/fail
export const options = {
  stages: [
    { duration: '10s', target: 10 },   // Ramp up to 10 VUs
    { duration: '30s', target: 100 },  // Ramp up to 100 VUs
    { duration: '30s', target: 100 },  // Stay at 100 req/s
    { duration: '10s', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.1'],
  },
};

// Custom metrics
const eventProcessingTime = new Trend('event_processing_time');
const eventThroughput = new Counter('event_throughput');
const eventErrors = new Counter('event_errors');

const API_BASE_URL = 'http://localhost:8000';

export function setup() {
  const res = http.get(`${API_BASE_URL}/health`);
  check(res, {
    'setup: API is reachable': (r) => r.status === 200,
  });
  
  return { startTime: new Date() };
}

export default function (data) {
  group('User Events', () => {
    testUserEvent();
  });
  
  group('Order Events', () => {
    testOrderEvent();
  });
  
  group('Notification Events', () => {
    testNotificationEvent();
  });
  
  sleep(0.1);
}

function testUserEvent() {
  const userEvent = {
    user_id: Math.floor(Math.random() * 10000),
    email: `user${Math.random()}@example.com`,
    status: ['ACTIVE', 'INACTIVE', 'PENDING'][Math.floor(Math.random() * 3)],
    created_at: new Date().toISOString(),
  };
  
  const startTime = new Date();
  
  const res = http.post(
    `${API_BASE_URL}/events/user`,
    JSON.stringify(userEvent),
    { headers: { 'Content-Type': 'application/json' }, timeout: '30s' }
  );
  
  const processingTime = new Date() - startTime;
  eventProcessingTime.add(processingTime);
  
  const success = check(res, {
    'user event: status 200': (r) => r.status === 200 || r.status === 202,
    'user event: response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  if (success) {
    eventThroughput.add(1);
  } else {
    eventErrors.add(1);
  }
}

function testOrderEvent() {
  const orderEvent = {
    order_id: `ORD${Math.floor(Math.random() * 100000)}`,
    status: ['PENDING', 'SHIPPED', 'DELIVERED'][Math.floor(Math.random() * 3)],
    customer_id: Math.floor(Math.random() * 5000),
    amount: (Math.random() * 1000).toFixed(2),
  };
  
  const startTime = new Date();
  
  const res = http.post(
    `${API_BASE_URL}/events/order`,
    JSON.stringify(orderEvent),
    { headers: { 'Content-Type': 'application/json' }, timeout: '30s' }
  );
  
  const processingTime = new Date() - startTime;
  eventProcessingTime.add(processingTime);
  
  const success = check(res, {
    'order event: status 200': (r) => r.status === 200 || r.status === 202,
  });
  
  if (success) {
    eventThroughput.add(1);
  } else {
    eventErrors.add(1);
  }
}

function testNotificationEvent() {
  const notificationEvent = {
    notification_id: `NOTIF${Math.floor(Math.random() * 100000)}`,
    user_id: Math.floor(Math.random() * 10000),
    type: ['email', 'sms', 'push'][Math.floor(Math.random() * 3)],
    status: ['pending', 'sent'][Math.floor(Math.random() * 2)],
  };
  
  const startTime = new Date();
  
  const res = http.post(
    `${API_BASE_URL}/events/notification`,
    JSON.stringify(notificationEvent),
    { headers: { 'Content-Type': 'application/json' }, timeout: '30s' }
  );
  
  const processingTime = new Date() - startTime;
  eventProcessingTime.add(processingTime);
  
  const success = check(res, {
    'notification event: status 200': (r) => r.status === 200 || r.status === 202,
  });
  
  if (success) {
    eventThroughput.add(1);
  } else {
    eventErrors.add(1);
  }
}

export function handleSummary(data) {
  const summary = {
    'execution': {
      'total_requests': data.metrics.http_reqs.value,
      'successful_requests': data.metrics.http_reqs.value - (eventErrors.value || 0),
      'failed_requests': eventErrors.value || 0,
      'error_rate': (
        ((eventErrors.value || 0) / (data.metrics.http_reqs.value || 1)) * 100
      ).toFixed(2) + '%',
    },
    'performance': {
      'avg_response_time_ms': Math.round(data.metrics.http_req_duration.values.avg),
      'p95_response_time_ms': Math.round(data.metrics.http_req_duration.values['p(95)']),
      'p99_response_time_ms': Math.round(data.metrics.http_req_duration.values['p(99)']),
    },
    'throughput': {
      'total_events_processed': eventThroughput.value || 0,
      'events_per_second': (
        ((eventThroughput.value || 0) / (data.state.testRunDurationMs / 1000)) || 0
      ).toFixed(2),
    },
  };

  console.log('\n========== LOAD TEST SUMMARY ==========');
  console.log(JSON.stringify(summary, null, 2));

  return { 'stdout': JSON.stringify(summary, null, 2) };
}
